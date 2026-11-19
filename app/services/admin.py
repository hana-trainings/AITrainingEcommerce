"""Staff and owner tools (Epic E7). Admin pages are plain: no gamification.

Every page using these functions must call guard_page(*ADMIN_ROLES) first, and
the database RLS policies are the real protection (NFR-SEC-05). Course, role
and order-cancel changes are written to audit_log automatically by database
triggers (NFR-SEC-18); use RPC write_audit_log only for extra details such as
the reason for a seat adjustment.

The functions below ALSO re-check the role (read fresh from the database) before
changing anything, so a hidden button is never the only protection and the user
gets a clear message instead of a silent "nothing happened".
"""

import re
import uuid
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from functools import wraps
from typing import Any

from app.models.domain import (
    ADMIN_ROLES,
    COURSE_LEVELS,
    OWNER_ONLY,
    ActionResult,
    Category,
    Course,
    CourseInput,
    DashboardMetrics,
    LearningPath,
    Order,
    OrderStatus,
    Role,
    UserRow,
)
from app.services import auth, catalog, gamification
from app.services.supabase_client import get_client
from app.utils.log import get_logger
from app.utils.text import escape_markdown

logger = get_logger(__name__)


def _refreshes_catalog(action: Callable[..., ActionResult]) -> Callable[..., ActionResult]:
    """Clear the cached public catalog after a successful admin change.

    Why: the storefront caches published courses for 60 seconds (NFR-PERF-03).
    Without this, a course staff just published or edited would look unchanged.
    """

    @wraps(action)
    def run_and_refresh(*args: Any, **kwargs: Any) -> ActionResult:
        result = action(*args, **kwargs)
        if result.ok:
            catalog.clear_cache()
        return result

    return run_and_refresh


COURSE_IMAGE_BUCKET = "course-images"
# Query parameter that tells the course editor which course to edit (?course_id=12).
EDIT_COURSE_PARAM = "course_id"
ALLOWED_IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB, US-703 AC3

# Limits copied from the database CHECK rules (migration 0003), so the form can
# explain problems before the database rejects them (NFR-SEC-13).
TITLE_MAX = 120
SLUG_MAX = 80
SUMMARY_MAX = 200
DESCRIPTION_MAX = 5000
INSTRUCTOR_MAX = 80
DURATION_MAX = 500
PRICE_MAX = 9999
SEATS_MIN, SEATS_MAX = 1, 10000
LIST_ITEMS_MAX = 20  # outcomes, prerequisites, tags
LIST_ITEM_MAX_CHARS = 200
TAG_MAX_CHARS = 40
MODULES_MAX = 100
MODULE_DESCRIPTION_MAX = 1000
PATH_POSITION_MAX = 50
SEAT_REASON_MAX = 200
CATEGORY_NAME_MAX = 60
ICON_MAX = 40
PATH_NAME_MAX = 80
PATH_DESCRIPTION_MAX = 1000
BADGE_NAME_MAX = 80
PATH_COURSES_MAX = 50

# "Low seats" uses the same rule as the seat meter (US-203 AC2): 5 or fewer, or 10% or less.
LOW_SEATS_ABSOLUTE = 5
LOW_SEATS_SHARE = 0.10
DASHBOARD_DAYS = 30
TOP_COURSES = 5

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

GENERIC_ERROR = "Something went wrong, please try again."
STAFF_ONLY = "Only staff can do this."
OWNER_ONLY_MESSAGE = "Only the owner can do this."
NOT_FOUND = "Course not found."
HAS_ORDERS = (
    "This course has orders, so it can't be deleted. "
    "Unpublish it instead to hide it from the catalog."
)
SLUG_TAKEN = "This slug is already used by another course. Choose a different one."
SEATS_CHANGED = (
    "The seats changed while you were working (someone may have just bought one). "
    "Please check the numbers and try again."
)
OWN_ROLE_MESSAGE = (
    "You can't change your own role. The owner role is managed by the trainer, "
    "and the last owner can't be demoted."
)
ROLE_ERRORS = {
    "LAST_OWNER": "The last owner can't be demoted.",
    "NOT_ALLOWED": "Only the owner can change roles, and only between customer and staff.",
}

# Magic bytes: the first bytes of a real image file. Checking them means a renamed
# text file can't pretend to be a picture (NFR-SEC-16).
_IMAGE_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}
_IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


# ---------------------------------------------------------------- small helpers
def _is_admin() -> bool:
    """Role read fresh from the database (NFR-SEC-10)."""
    return auth.require_role(*ADMIN_ROLES) is not None


def _is_owner() -> bool:
    return auth.require_role(*OWNER_ONLY) is not None


def _error_text(error: Exception) -> str:
    """The database message of a Supabase error (used only to find error CODES)."""
    return str(getattr(error, "message", "") or error)


def _error_code(error: Exception) -> str:
    """Postgres error code, e.g. 23505 = unique value already used, 23503 = still referenced."""
    return str(getattr(error, "code", "") or "")


def slugify(text: str) -> str:
    """Make a URL-friendly slug from a title: "SQL for Analysts!" -> "sql-for-analysts"."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:SLUG_MAX].strip("-")


def _clean_list(values: list[str] | None) -> list[str]:
    """Strip spaces and drop empty lines from a list of text values."""
    return [str(value).strip() for value in (values or []) if str(value).strip()]


# ---------------------------------------------------------------- courses
def list_courses(
    search: str = "", published: bool | None = None, category_id: int | None = None
) -> list[Course]:
    """Return ALL courses (including unpublished) for the admin table, newest update first.

    published=None means both. Story US-702 (U3-01).
    RLS only returns drafts to staff and owner (US-702 AC3).
    """
    client = get_client()
    query = client.table("courses").select("*")
    if search.strip():
        query = query.ilike("title", f"%{search.strip()}%")
    if published is not None:
        query = query.eq("is_published", published)
    if category_id is not None:
        query = query.eq("category_id", category_id)
    courses = query.order("updated_at", desc=True).execute().data or []
    names = _category_names()
    for course in courses:
        course["category_name"] = names.get(course.get("category_id"), "")
    return courses


def _category_names() -> dict[int, str]:
    rows = get_client().table("categories").select("id, name").execute().data or []
    return {row["id"]: row["name"] for row in rows}


def validate_course_input(data: CourseInput) -> dict[str, str]:
    """Return {field: message} for every invalid field (pure function, no DB).

    Rules: title, summary (<= 200 chars), description, category, level, duration
    required; price 0-9,999; seats 1-10,000. Story US-703 AC2 (U3-03).
    """
    errors: dict[str, str] = {}
    _check_text(errors, data, "title", "a title", TITLE_MAX)
    _check_text(errors, data, "summary", "a summary", SUMMARY_MAX)
    _check_text(errors, data, "description", "a description", DESCRIPTION_MAX)

    slug = str(data.get("slug") or "").strip() or slugify(str(data.get("title") or ""))
    if not slug:
        errors.setdefault("slug", "Enter a slug (lowercase letters, numbers and dashes).")
    elif len(slug) > SLUG_MAX or not _SLUG_PATTERN.match(slug):
        errors["slug"] = "Use lowercase letters, numbers and single dashes, e.g. sql-for-analysts."

    if not data.get("category_id"):
        errors["category_id"] = "Choose a category."
    if data.get("level") not in COURSE_LEVELS:
        errors["level"] = "Choose a level."
    _check_number(
        errors,
        data,
        "duration_hours",
        0,
        DURATION_MAX,
        "Enter hours above 0 and up to 500.",
        allow_min=False,
    )
    _check_number(errors, data, "price", 0, PRICE_MAX, "Enter a price from 0 to 9,999.")
    _check_number(
        errors,
        data,
        "seats_total",
        SEATS_MIN,
        SEATS_MAX,
        "Enter total seats from 1 to 10,000.",
        whole=True,
    )

    if len(str(data.get("instructor_name") or "").strip()) > INSTRUCTOR_MAX:
        errors["instructor_name"] = f"Use at most {INSTRUCTOR_MAX} characters."
    for field in ("outcomes", "prerequisites"):
        items = _clean_list(data.get(field))  # type: ignore[arg-type]
        if len(items) > LIST_ITEMS_MAX or any(len(item) > LIST_ITEM_MAX_CHARS for item in items):
            errors[field] = (
                f"Use at most {LIST_ITEMS_MAX} lines of {LIST_ITEM_MAX_CHARS} characters each."
            )
    tags = _clean_list(data.get("tags"))
    if len(tags) > LIST_ITEMS_MAX or any(len(tag) > TAG_MAX_CHARS for tag in tags):
        errors["tags"] = f"Use at most {LIST_ITEMS_MAX} tags of {TAG_MAX_CHARS} characters each."
    _check_modules(errors, data.get("modules") or [])
    _check_path_positions(errors, data.get("path_positions") or [])
    if len(str(data.get("image_url") or "")) > 500:
        errors["image_url"] = "The image link is too long."
    return errors


def _check_text(
    errors: dict[str, str], data: CourseInput, field: str, what: str, limit: int
) -> None:
    value = str(data.get(field) or "").strip()
    if not value:
        errors[field] = f"Enter {what}."
    elif len(value) > limit:
        errors[field] = f"Use at most {limit} characters (now {len(value)})."


def _check_number(
    errors: dict[str, str],
    data: CourseInput,
    field: str,
    low: float,
    high: float,
    message: str,
    *,
    allow_min: bool = True,
    whole: bool = False,
) -> None:
    value = data.get(field)
    if value is None or isinstance(value, bool):
        errors[field] = message
        return
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        errors[field] = message
        return
    too_low = number < low if allow_min else number <= low
    if too_low or number > high or (whole and number != int(number)):
        errors[field] = message


def _check_modules(errors: dict[str, str], modules: list[dict[str, str]]) -> None:
    if len(modules) > MODULES_MAX:
        errors["modules"] = f"Use at most {MODULES_MAX} modules."
        return
    for number, module in enumerate(modules, start=1):
        title = str(module.get("title") or "").strip()
        if not title or len(title) > TITLE_MAX:
            errors["modules"] = f"Module {number}: enter a title of up to {TITLE_MAX} characters."
            return
        if len(str(module.get("description") or "")) > MODULE_DESCRIPTION_MAX:
            errors["modules"] = (
                f"Module {number}: keep the description under {MODULE_DESCRIPTION_MAX} characters."
            )
            return


def _check_path_positions(errors: dict[str, str], positions: list[dict[str, int]]) -> None:
    path_ids = [item.get("path_id") for item in positions]
    if len(set(path_ids)) != len(path_ids):
        errors["path_positions"] = "Add the course to each learning path only once."
        return
    for item in positions:
        position = item.get("position")
        if not isinstance(position, int) or not 1 <= position <= PATH_POSITION_MAX:
            errors["path_positions"] = f"Path positions must be from 1 to {PATH_POSITION_MAX}."
            return


def _course_values(data: CourseInput) -> dict[str, Any]:
    """The course columns to save, cleaned. Seats are handled separately on purpose."""
    instructor = str(data.get("instructor_name") or "").strip()
    return {
        "title": str(data["title"]).strip(),
        "slug": str(data.get("slug") or "").strip() or slugify(str(data["title"])),
        "summary": str(data["summary"]).strip(),
        "description": str(data["description"]).strip(),
        "category_id": int(data["category_id"]),
        "level": data["level"],
        "duration_hours": float(data["duration_hours"]),
        "price": round(float(data["price"]), 2),
        "instructor_name": instructor or None,
        "outcomes": _clean_list(data.get("outcomes")),
        "prerequisites": _clean_list(data.get("prerequisites")),
        "tags": [tag.lower() for tag in _clean_list(data.get("tags"))],
        "image_url": data.get("image_url") or None,
        "is_featured": bool(data.get("is_featured", False)),
    }


def _slug_in_use(slug: str, except_course_id: int | None = None) -> bool:
    rows = get_client().table("courses").select("id").eq("slug", slug).execute().data or []
    return any(row["id"] != except_course_id for row in rows)


# Database error codes from migration 0025, mapped to friendly text.
CHILDREN_ERRORS = {
    "POSITION_TAKEN": (
        "A learning path step is already taken by another course. Choose a free step, "
        "or reorder the path on Categories & paths."
    ),
    "DUPLICATE_PATH": "Add the course to each learning path only once.",
    "DUPLICATE_COURSE": "Add each course only once.",
    "NOT_ALLOWED": STAFF_ONLY,
    "COURSE_NOT_FOUND": NOT_FOUND,
    "PATH_NOT_FOUND": "Learning path not found.",
}


def _children_error_message(error: Exception) -> str:
    """Friendly text for an error raised by the 0025 database functions."""
    text = _error_text(error)
    for code, message in CHILDREN_ERRORS.items():
        if text.startswith(code) or f"{code}:" in text:
            return message
    return GENERIC_ERROR


def _save_course_children(course_id: int, data: CourseInput) -> str:
    """Replace the course's modules and learning-path steps. Returns "" or a friendly problem.

    One database function does it in ONE transaction (migration 0025): if anything
    fails, the old modules and path steps are kept, nothing is half-saved.
    """
    modules = [
        {
            "title": str(module.get("title") or "").strip(),
            "description": str(module.get("description") or "").strip(),
        }
        for module in data.get("modules") or []
    ]
    positions = [
        {"path_id": int(item["path_id"]), "position": int(item["position"])}
        for item in data.get("path_positions") or []
    ]
    try:
        get_client().rpc(
            "admin_replace_course_children",
            {"p_course_id": course_id, "p_modules": modules, "p_path_positions": positions},
        ).execute()
    except Exception as error:
        logger.warning(
            "saving modules/paths failed: course_id=%s %s", course_id, type(error).__name__
        )
        return _children_error_message(error)
    return ""


@_refreshes_catalog
def create_course(data: CourseInput) -> ActionResult:
    """Insert a new course (unpublished by default; the insert must set
    seats_available = seats_total) with its modules and path positions.
    On success data={"course_id": ...}. Story US-703 (U3-03).
    """
    if not _is_admin():
        return ActionResult(ok=False, message=STAFF_ONLY)
    errors = validate_course_input(data)  # checked here too, never only in the form
    if errors:
        return ActionResult(
            ok=False, message="Please fix the highlighted fields.", data={"errors": errors}
        )
    values = _course_values(data)
    if _slug_in_use(values["slug"]):
        return ActionResult(ok=False, message=SLUG_TAKEN, data={"errors": {"slug": SLUG_TAKEN}})
    seats = int(data["seats_total"])
    # A new course has sold nothing yet, so every seat is available (US-703 AC5).
    values.update(
        seats_total=seats,
        seats_available=seats,
        is_published=bool(data.get("is_published", False)),  # draft unless asked (AC4)
    )
    try:
        rows = get_client().table("courses").insert(values).execute().data or []
    except Exception as error:
        if _error_code(error) == "23505":
            return ActionResult(ok=False, message=SLUG_TAKEN, data={"errors": {"slug": SLUG_TAKEN}})
        logger.warning("create_course failed: %s", type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_ERROR)
    if not rows:
        return ActionResult(ok=False, message=STAFF_ONLY)
    course_id = int(rows[0]["id"])
    problem = _save_course_children(course_id, data)
    warning = f"The course was saved, but not its modules or paths: {problem}" if problem else ""
    logger.info("course created: course_id=%s", course_id)
    return ActionResult(
        ok=True,
        message=warning or f'Course "{escape_markdown(values["title"])}" was created.',
        data={"course_id": course_id, "warning": warning},
    )


def get_course_for_edit(course_id: int) -> Course | None:
    """Return any course (published or not) with modules and paths for the edit form.

    Story US-704 (U3-09).
    """
    client = get_client()
    rows = client.table("courses").select("*").eq("id", course_id).limit(1).execute().data or []
    if not rows:
        return None
    course: Course = rows[0]
    course["modules"] = (
        client.table("course_modules")
        .select("*")
        .eq("course_id", course_id)
        .order("position")
        .execute()
        .data
        or []
    )
    links = client.table("learning_path_courses").select("*").execute().data or []
    path_names = {
        row["id"]: row["name"]
        for row in client.table("learning_paths").select("id, name").execute().data or []
    }
    course["paths"] = [
        {
            "path_id": link["path_id"],
            "path_name": path_names.get(link["path_id"], ""),
            "position": link["position"],
            "course_count": sum(1 for other in links if other["path_id"] == link["path_id"]),
        }
        for link in links
        if link["course_id"] == course_id
    ]
    course["category_name"] = _category_names().get(course.get("category_id"), "")
    return course


def get_editor_name(user_id: str | None) -> str:
    """Display name of whoever last updated a course (US-704 AC3), or "" if unknown."""
    if not user_id:
        return ""
    rows = (
        get_client()
        .table("profiles")
        .select("display_name")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return str(rows[0].get("display_name") or "") if rows else ""


@_refreshes_catalog
def update_course(course_id: int, data: CourseInput) -> ActionResult:
    """Save edits (sets updated_by). Past orders keep their price snapshot. Story US-704 (U3-09).

    updated_by and updated_at are stamped by a database trigger, so they can't be faked.
    A change of total seats goes through the same rule as "Adjust seats" (US-706).
    """
    if not _is_admin():
        return ActionResult(ok=False, message=STAFF_ONLY)
    errors = validate_course_input(data)
    if errors:
        return ActionResult(
            ok=False, message="Please fix the highlighted fields.", data={"errors": errors}
        )
    current = _read_seats(course_id)
    if current is None:
        return ActionResult(ok=False, message=NOT_FOUND)
    values = _course_values(data)
    if _slug_in_use(values["slug"], except_course_id=course_id):
        return ActionResult(ok=False, message=SLUG_TAKEN, data={"errors": {"slug": SLUG_TAKEN}})
    if "is_published" in data:
        values["is_published"] = bool(data["is_published"])

    # Check the seat change BEFORE saving anything, so a bad number changes nothing.
    total, available = int(current["seats_total"]), int(current["seats_available"])
    seat_change = int(data["seats_total"]) - total
    seat_problem = check_seat_change(total, available, seat_change) if seat_change else ""
    if seat_problem:
        return ActionResult(
            ok=False, message=seat_problem, data={"errors": {"seats_total": seat_problem}}
        )
    old_image = current.get("image_url")
    try:
        rows = get_client().table("courses").update(values).eq("id", course_id).execute().data
    except Exception as error:
        if _error_code(error) == "23505":
            return ActionResult(ok=False, message=SLUG_TAKEN, data={"errors": {"slug": SLUG_TAKEN}})
        logger.warning("update_course failed: course_id=%s %s", course_id, type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_ERROR)
    if not rows:
        return ActionResult(ok=False, message=STAFF_ONLY)
    problems = []
    children_problem = _save_course_children(course_id, data)
    if children_problem:
        problems.append(f"Modules and paths were not changed: {children_problem}")
    if seat_change:
        # Seats last, only after the course itself saved. Same rule and audit as US-706.
        seats = adjust_seats(course_id, seat_change, "Total seats changed in the course editor")
        if not seats.ok:
            problems.append(f"Total seats were not changed: {seats.message}")
    if old_image and old_image != values.get("image_url"):
        delete_course_image(old_image)  # the old picture is no longer used
    logger.info("course updated: course_id=%s", course_id)
    warning = " ".join(problems)
    message = f"The other changes were saved. {warning}" if warning else "Changes saved."
    return ActionResult(ok=True, message=message, data={"warning": warning})


def _image_type_matches(file_bytes: bytes, content_type: str) -> bool:
    """True if the file really starts like a JPG/PNG/WebP of the claimed type."""
    if content_type == "image/webp":
        return file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP"
    return any(file_bytes.startswith(sig) for sig in _IMAGE_SIGNATURES.get(content_type, ()))


def upload_course_image(file_bytes: bytes, content_type: str) -> ActionResult:
    """Upload a JPG/PNG/WebP (max 2 MB) to the 'course-images' bucket under an app-generated
    file name. On success data={"image_url": <public url>}. Story US-704 (U3-09), US-703 AC3.
    """
    if not _is_admin():
        return ActionResult(ok=False, message=STAFF_ONLY)
    if content_type not in ALLOWED_IMAGE_TYPES:
        return ActionResult(ok=False, message="Use a JPG, PNG or WebP image.")
    if not file_bytes:
        return ActionResult(ok=False, message="The file is empty.")
    if len(file_bytes) > MAX_IMAGE_BYTES:
        return ActionResult(ok=False, message="The image is larger than 2 MB. Use a smaller one.")
    if not _image_type_matches(file_bytes, content_type):
        return ActionResult(ok=False, message="This file is not a real JPG, PNG or WebP image.")
    # A random name: never the user's file name, so nothing personal or unsafe ends up
    # in the URL, and two uploads never overwrite each other (NFR-SEC-16).
    path = f"{uuid.uuid4().hex}.{_IMAGE_EXTENSIONS[content_type]}"
    try:
        bucket = get_client().storage.from_(COURSE_IMAGE_BUCKET)
        bucket.upload(path, file_bytes, {"content-type": content_type, "upsert": "false"})
        image_url = bucket.get_public_url(path)
    except Exception as error:
        logger.warning("upload_course_image failed: %s", type(error).__name__)
        return ActionResult(ok=False, message="The image could not be uploaded. Please try again.")
    return ActionResult(ok=True, message="Image uploaded.", data={"image_url": image_url})


def _storage_path(image_url: str) -> str:
    """The file name inside our bucket, or "" if the URL is not one of our uploads."""
    marker = f"/object/public/{COURSE_IMAGE_BUCKET}/"
    if marker not in image_url:
        return ""
    path = image_url.split(marker, 1)[1].split("?", 1)[0]
    # Only names this app made (uuid hex + image extension), so nothing else gets deleted.
    return path if re.fullmatch(r"[0-9a-f]{32}\.(jpg|png|webp)", path) else ""


def delete_course_image(image_url: str | None) -> bool:
    """Try to delete an uploaded course image that is no longer used. Never raises.

    Returns True if a delete was sent. A failure only leaves an unused file behind.
    """
    path = _storage_path(image_url or "")
    if not path or not _is_admin():
        return False
    try:
        get_client().storage.from_(COURSE_IMAGE_BUCKET).remove([path])
    except Exception as error:
        logger.info("delete_course_image failed: %s", type(error).__name__)
        return False
    return True


@_refreshes_catalog
def set_published(course_id: int, published: bool) -> ActionResult:
    """Publish or unpublish a course (audit logged). Story US-705 (U3-06).

    Orders are not touched: they keep their own copy of title and price (AC2).
    Carts flag the course as unavailable on their next check (US-307).
    """
    if not _is_admin():
        return ActionResult(ok=False, message=STAFF_ONLY)
    try:
        rows = (
            get_client()
            .table("courses")
            .update({"is_published": bool(published)})
            .eq("id", course_id)
            .execute()
            .data
            or []
        )
    except Exception as error:
        logger.warning("set_published failed: course_id=%s %s", course_id, type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_ERROR)
    if not rows:
        return ActionResult(ok=False, message=NOT_FOUND)
    title = escape_markdown(rows[0].get("title", "The course"))  # shown as Markdown
    if published:
        return ActionResult(ok=True, message=f'"{title}" is now published.')
    return ActionResult(ok=True, message=f'"{title}" is now hidden from the catalog.')


def _read_seats(course_id: int) -> dict[str, Any] | None:
    rows = (
        get_client()
        .table("courses")
        .select("id, title, seats_total, seats_available, image_url")
        .eq("id", course_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def check_seat_change(seats_total: int, seats_available: int, change: int) -> str:
    """Return "" if the change is allowed, otherwise a friendly reason (pure function).

    Adding or removing seats changes BOTH totals by the same number, because the
    seats already sold (total - available) stay sold. So "available >= 0" and
    "total >= seats sold" are the same rule (US-706 AC2).
    """
    sold = seats_total - seats_available
    if change == 0:
        return "Enter a number of seats to add (+) or remove (-)."
    if seats_available + change < 0:
        return f"You can remove at most {seats_available} seat(s): {sold} seat(s) are already sold."
    if seats_total + change < SEATS_MIN:
        return "A course needs at least 1 seat in total."
    if seats_total + change > SEATS_MAX:
        return f"A course can have at most {SEATS_MAX:,} seats in total."
    return ""


@_refreshes_catalog
def adjust_seats(course_id: int, change: int, reason: str) -> ActionResult:
    """Add (+) or remove (-) seats with a reason (audit logged).

    seats_available can't go below 0 and seats_total can't go below seats sold.
    Save the reason with RPC write_audit_log(action, entity, entity_id, before, after).
    Story US-706 (U3-07).
    """
    if not _is_admin():
        return ActionResult(ok=False, message=STAFF_ONLY)
    reason = reason.strip()
    if not reason:
        return ActionResult(ok=False, message="Enter a reason for the change.")
    if len(reason) > SEAT_REASON_MAX:
        return ActionResult(
            ok=False, message=f"Keep the reason under {SEAT_REASON_MAX} characters."
        )
    course = _read_seats(course_id)
    if course is None:
        return ActionResult(ok=False, message=NOT_FOUND)
    total, available = int(course["seats_total"]), int(course["seats_available"])
    problem = check_seat_change(total, available, change)
    if problem:
        return ActionResult(ok=False, message=problem)

    before = {"seats_total": total, "seats_available": available}
    after = {"seats_total": total + change, "seats_available": available + change}
    try:
        # "Optimistic" update: it only matches if nobody bought a seat since we read the
        # numbers, so a checkout happening at the same moment can't be overwritten.
        rows = (
            get_client()
            .table("courses")
            .update(after)
            .eq("id", course_id)
            .eq("seats_total", total)
            .eq("seats_available", available)
            .execute()
            .data
            or []
        )
    except Exception as error:
        logger.warning("adjust_seats failed: course_id=%s %s", course_id, type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_ERROR)
    if not rows:
        return ActionResult(ok=False, message=SEATS_CHANGED)
    _write_seat_reason(course_id, before, after, change, reason)
    return ActionResult(
        ok=True,
        message=f"Seats updated: {after['seats_available']} of {after['seats_total']} available.",
        data=after,
    )


def _write_seat_reason(course_id: int, before: dict, after: dict, change: int, reason: str) -> None:
    """Save the reason in the audit log. The trigger already logged the numbers themselves."""
    try:
        get_client().rpc(
            "write_audit_log",
            {
                "p_action": "seat_adjust_reason",
                "p_entity": "course",
                "p_entity_id": str(course_id),
                "p_before": before,
                "p_after": {**after, "change": change, "reason": reason},
            },
        ).execute()
    except Exception as error:  # the seats ARE changed; don't report the whole action failed
        logger.warning("write_audit_log failed: course_id=%s %s", course_id, type(error).__name__)


@_refreshes_catalog
def delete_course(course_id: int, typed_title: str) -> ActionResult:
    """Owner only: delete a course with no orders, if typed_title matches its title exactly.

    If it has orders, return ok=False suggesting unpublish. Story US-710 (U3-08).
    The database also blocks it (foreign key "restrict" on order_items, NFR-DATA-05).
    """
    if not _is_owner():
        return ActionResult(ok=False, message="Only the owner can delete courses.")
    course = _read_seats(course_id)
    if course is None:
        return ActionResult(ok=False, message=NOT_FOUND)
    if typed_title.strip() != str(course["title"]).strip():
        return ActionResult(
            ok=False, message="The title you typed does not match. Type it exactly to confirm."
        )
    client = get_client()
    if (
        client.table("order_items")
        .select("order_id")
        .eq("course_id", course_id)
        .limit(1)
        .execute()
        .data
    ):
        return ActionResult(ok=False, message=HAS_ORDERS)
    try:
        rows = client.table("courses").delete().eq("id", course_id).execute().data or []
    except Exception as error:
        if _error_code(error) == "23503":  # an order was placed in the meantime
            return ActionResult(ok=False, message=HAS_ORDERS)
        logger.warning("delete_course failed: course_id=%s %s", course_id, type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_ERROR)
    if not rows:
        return ActionResult(ok=False, message="Only the owner can delete courses.")
    logger.info("course deleted: course_id=%s", course_id)
    return ActionResult(ok=True, message=f'"{escape_markdown(course["title"])}" was deleted.')


# ---------------------------------------------------------------- categories and paths
def list_categories_and_paths() -> tuple[list[Category], list[LearningPath]]:
    """Return all categories and all paths (with ordered courses) for editing.

    Story US-711 (U3-12).
    """
    categories = (
        get_client().table("categories").select("*").order("sort_order").execute().data or []
    )
    return categories, gamification.load_paths_with_courses()


def badge_names() -> dict[str, str]:
    """{badge_code: name} so the path editor can show each path's badge name."""
    rows = get_client().table("badges").select("code, name").execute().data or []
    return {row["code"]: row["name"] for row in rows}


def validate_category(name: str, icon: str, sort_order: int) -> dict[str, str]:
    """Return {field: message} for the category form (pure function). US-711 AC1."""
    errors: dict[str, str] = {}
    if not name.strip():
        errors["name"] = "Enter a name."
    elif len(name.strip()) > CATEGORY_NAME_MAX:
        errors["name"] = f"Use at most {CATEGORY_NAME_MAX} characters."
    if not icon.strip() or len(icon.strip()) > ICON_MAX:
        errors["icon"] = "Enter one emoji as the icon."
    if not isinstance(sort_order, int) or sort_order < 0:
        errors["sort_order"] = "Enter 0 or a higher whole number."
    return errors


@_refreshes_catalog
def save_category(
    name: str, icon: str, sort_order: int, category_id: int | None = None
) -> ActionResult:
    """Create (category_id=None) or update a category. icon is an emoji. Story US-711 (U3-12)."""
    if not _is_admin():
        return ActionResult(ok=False, message=STAFF_ONLY)
    errors = validate_category(name, icon, sort_order)
    if errors:
        return ActionResult(ok=False, message=" ".join(errors.values()), data={"errors": errors})
    values = {"name": name.strip(), "icon": icon.strip(), "sort_order": sort_order}
    table = get_client().table("categories")
    try:
        if category_id is None:
            rows = table.insert(values).execute().data or []
        else:
            rows = table.update(values).eq("id", category_id).execute().data or []
    except Exception as error:
        if _error_code(error) == "23505":
            return ActionResult(ok=False, message="A category with this name already exists.")
        logger.warning("save_category failed: %s", type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_ERROR)
    if not rows:
        return ActionResult(ok=False, message="Category not found.")
    return ActionResult(ok=True, message=f'Category "{escape_markdown(values["name"])}" saved.')


def validate_path(
    name: str, description: str, course_ids_in_order: list[int], badge_name: str
) -> dict[str, str]:
    """Return {field: message} for the learning path form (pure function). US-711 AC2."""
    errors: dict[str, str] = {}
    if not name.strip():
        errors["name"] = "Enter a name."
    elif len(name.strip()) > PATH_NAME_MAX:
        errors["name"] = f"Use at most {PATH_NAME_MAX} characters."
    if len(description.strip()) > PATH_DESCRIPTION_MAX:
        errors["description"] = f"Use at most {PATH_DESCRIPTION_MAX} characters."
    if not course_ids_in_order:
        errors["courses"] = "Add at least one course."
    elif len(course_ids_in_order) > PATH_COURSES_MAX:
        errors["courses"] = f"Use at most {PATH_COURSES_MAX} courses."
    elif len(set(course_ids_in_order)) != len(course_ids_in_order):
        errors["courses"] = "Add each course only once."
    if not badge_name.strip():
        errors["badge_name"] = "Enter the completion badge name."
    elif len(badge_name.strip()) > BADGE_NAME_MAX:
        errors["badge_name"] = f"Use at most {BADGE_NAME_MAX} characters."
    return errors


def _badge_code_for(path_name: str) -> str:
    """e.g. "Data Analyst Path" -> "path_master_data_analyst_path" (stable, readable)."""
    return ("path_master_" + re.sub(r"[^a-z0-9]+", "_", path_name.lower()).strip("_"))[:60]


def _save_path_badge(badge_code: str | None, badge_name: str, path_name: str) -> str:
    """Create or rename the path's completion badge. Returns its code."""
    client = get_client()
    if badge_code and client.table("badges").select("code").eq("code", badge_code).execute().data:
        client.table("badges").update({"name": badge_name}).eq("code", badge_code).execute()
        return badge_code
    code = badge_code or _badge_code_for(path_name)
    client.table("badges").insert(
        {
            "code": code,
            "name": badge_name,
            "description": f"You own every course in {path_name}."[:300],
            "icon": "🏆",
            "hint": f"Unlock every course in {path_name}"[:200],
            "sort_order": 20,
        }
    ).execute()
    return code


@_refreshes_catalog
def save_path(
    name: str,
    description: str,
    course_ids_in_order: list[int],
    badge_name: str,
    path_id: int | None = None,
) -> ActionResult:
    """Create (path_id=None) or update a learning path and its ordered courses.

    Story US-711 (U3-12). The bonus XP stays at the database default (+250).
    """
    if not _is_admin():
        return ActionResult(ok=False, message=STAFF_ONLY)
    errors = validate_path(name, description, course_ids_in_order, badge_name)
    if errors:
        return ActionResult(ok=False, message=" ".join(errors.values()), data={"errors": errors})
    try:
        path_id = _upsert_path(name.strip(), description.strip(), badge_name.strip(), path_id)
    except Exception as error:
        if _error_code(error) == "23505":
            return ActionResult(ok=False, message="A learning path or badge with this name exists.")
        logger.warning("save_path failed: %s", type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_ERROR)
    if path_id is None:
        return ActionResult(ok=False, message="Learning path not found.")
    try:
        # Replace the ordered course list in ONE transaction (migration 0025):
        # if it fails, the path keeps its old courses.
        get_client().rpc(
            "admin_replace_path_courses",
            {"p_path_id": path_id, "p_course_ids": [int(cid) for cid in course_ids_in_order]},
        ).execute()
    except Exception as error:
        logger.warning("save_path courses failed: %s", type(error).__name__)
        return ActionResult(
            ok=False,
            message="The path name was saved, but its courses were not changed: "
            + _children_error_message(error),
        )
    return ActionResult(
        ok=True,
        message=f'Learning path "{escape_markdown(name.strip())}" saved.',
        data={"path_id": path_id},
    )


def _upsert_path(name: str, description: str, badge_name: str, path_id: int | None) -> int | None:
    """Insert or update the learning_paths row (and its badge). Returns the path id."""
    table = get_client().table("learning_paths")
    if path_id is None:
        badge_code = _save_path_badge(None, badge_name, name)
        rows = (
            table.insert({"name": name, "description": description, "badge_code": badge_code})
            .execute()
            .data
            or []
        )
        return int(rows[0]["id"]) if rows else None
    existing = table.select("id, badge_code").eq("id", path_id).limit(1).execute().data or []
    if not existing:
        return None
    badge_code = _save_path_badge(existing[0].get("badge_code"), badge_name, name)
    get_client().table("learning_paths").update(
        {"name": name, "description": description, "badge_code": badge_code}
    ).eq("id", path_id).execute()
    return path_id


# ---------------------------------------------------------------- orders and dashboard
# Supabase (PostgREST) returns at most 1000 rows per request by default. Totals that
# silently stopped at 1000 orders would be wrong, so these reads fetch page by page.
PAGE_ROWS = 1000


def _all_rows(make_query: Callable[[], Any]) -> list[dict]:
    """Run make_query() once per page of PAGE_ROWS rows and return every row.

    make_query must build a NEW query with a stable .order(...), so pages don't overlap.
    """
    rows: list[dict] = []
    start = 0
    while True:
        page = make_query().range(start, start + PAGE_ROWS - 1).execute().data or []
        rows.extend(page)
        if len(page) < PAGE_ROWS:
            return rows
        start += PAGE_ROWS


def _emails_by_user() -> dict[str, str]:
    rows = _all_rows(lambda: get_client().table("profiles").select("id, email").order("id"))
    return {row["id"]: str(row.get("email") or "") for row in rows}


def _next_day(day: str) -> str:
    return (date.fromisoformat(day[:10]) + timedelta(days=1)).isoformat()


def list_all_orders(
    status: OrderStatus | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str = "",
) -> list[Order]:
    """Return all orders with customer_email and item_count, newest first.

    search matches order number or email. Use orders.get_order() and
    email_outbox.get_email_for_order() for the detail panel. Story US-707 (U2-18).
    date_from / date_to are "YYYY-MM-DD" and both days are included.
    item_count is the number of seats (sum of quantities) in the order.
    """
    if not _is_admin():
        return []
    client = get_client()

    def orders_query() -> Any:
        query = client.table("orders").select("*")
        if status:
            query = query.eq("status", status)
        if date_from:
            query = query.gte("created_at", date_from[:10])
        if date_to:
            query = query.lt("created_at", _next_day(date_to))  # "<" next day: whole day
        return query.order("created_at", desc=True).order("id", desc=True)

    orders = _all_rows(orders_query)
    if not orders:
        return []

    emails = _emails_by_user()
    seats: dict[int, int] = defaultdict(int)
    order_ids = {order["id"] for order in orders}
    items = _all_rows(
        lambda: (
            client.table("order_items")
            .select("order_id, course_id, quantity")
            .order("order_id")
            .order("course_id")
        )
    )
    for item in items:
        if item["order_id"] in order_ids:
            seats[item["order_id"]] += int(item.get("quantity") or 0)

    needle = search.strip().lower()
    result: list[Order] = []
    for order in orders:
        order["customer_email"] = emails.get(order.get("user_id", ""), "")
        order["item_count"] = seats[order["id"]]
        haystack = f"{order.get('order_number', '')} {order['customer_email']}".lower()
        if needle and needle not in haystack:
            continue
        order.pop("idempotency_key", None)  # internal value; staff don't need it
        result.append(order)
    return result


def _orders_per_day(orders: list[dict], today: date) -> list[dict[str, Any]]:
    """Count orders per day for the last DASHBOARD_DAYS days, including days with 0."""
    counts: dict[str, int] = defaultdict(int)
    for order in orders:
        counts[str(order.get("created_at", ""))[:10]] += 1
    days = [today - timedelta(days=offset) for offset in range(DASHBOARD_DAYS - 1, -1, -1)]
    return [{"day": day.isoformat(), "orders": counts[day.isoformat()]} for day in days]


def is_low_seats(seats_available: int, seats_total: int) -> bool:
    """Same "few seats" rule as the seat meter (pure function)."""
    if seats_available <= LOW_SEATS_ABSOLUTE:
        return True
    return seats_total > 0 and seats_available / seats_total <= LOW_SEATS_SHARE


def get_dashboard_metrics() -> DashboardMetrics:
    """Return KPI totals, orders per day (last 30 days), top 5 courses by seats sold,
    and low-seat courses. Story US-708 (U3-11).

    Only confirmed orders count; cancelled orders gave their seats back.
    All numbers come from real rows (US-606 AC1).
    """
    client = get_client()
    orders = _all_rows(
        lambda: (
            client.table("orders")
            .select("id, total, created_at")
            .eq("status", "confirmed")
            .order("id")
        )
    )
    confirmed_ids = {order["id"] for order in orders}
    all_items = _all_rows(
        lambda: (
            client.table("order_items")
            .select("order_id, course_id, title_snapshot, quantity")
            .order("order_id")
            .order("course_id")
        )
    )
    items = [item for item in all_items if item["order_id"] in confirmed_ids]

    sold_by_course: dict[int, int] = defaultdict(int)
    titles: dict[int, str] = {}
    for item in items:
        sold_by_course[item["course_id"]] += int(item.get("quantity") or 0)
        titles[item["course_id"]] = item.get("title_snapshot", "")
    courses = _all_rows(lambda: client.table("courses").select("*").order("id"))
    for course in courses:
        titles[course["id"]] = course.get("title", titles.get(course["id"], ""))
    top = sorted(sold_by_course.items(), key=lambda pair: pair[1], reverse=True)[:TOP_COURSES]

    customers = (
        client.table("profiles").select("id", count="exact").eq("role", "customer").execute()
    )
    low = [
        course
        for course in courses
        if course.get("is_published")
        and is_low_seats(int(course["seats_available"]), int(course["seats_total"]))
    ]
    return DashboardMetrics(
        total_orders=len(orders),
        total_revenue=round(sum(float(order.get("total") or 0) for order in orders), 2),
        seats_sold=sum(sold_by_course.values()),
        customer_count=int(customers.count or len(customers.data or [])),
        orders_per_day=_orders_per_day(orders, datetime.now(UTC).date()),
        top_courses=[{"title": titles.get(cid, ""), "seats_sold": seats} for cid, seats in top],
        low_seat_courses=sorted(low, key=lambda course: course["seats_available"]),
    )


# ---------------------------------------------------------------- staff (owner only)
def list_users() -> list[UserRow]:
    """Return all users with role and joined date (owner only).

    Reads profiles (id, display_name, email, role, created_at). Story US-709 (U3-10).
    """
    if not _is_owner():
        return []
    rows = (
        get_client()
        .table("profiles")
        .select("id, display_name, email, role, created_at")
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    return [
        UserRow(
            id=row["id"],
            display_name=str(row.get("display_name") or ""),
            email=str(row.get("email") or ""),
            role=row.get("role") or "customer",
            created_at=str(row.get("created_at") or ""),
        )
        for row in rows
    ]


def change_user_role(user_id: str, new_role: Role) -> ActionResult:
    """Owner only: switch a user between 'customer' and 'staff' (updates profiles.role).

    The database raises NOT_ALLOWED (caller is not the owner) or LAST_OWNER (the
    last owner can't be demoted); map both to friendly text. A trigger writes the audit log.
    Story US-709 (U3-10).
    """
    if new_role not in ("customer", "staff"):
        return ActionResult(ok=False, message=ROLE_ERRORS["NOT_ALLOWED"])
    owner = auth.require_role(*OWNER_ONLY)
    if owner is None:
        return ActionResult(ok=False, message=ROLE_ERRORS["NOT_ALLOWED"])
    if user_id == owner.id:
        # The owner role itself is managed by the trainer in the database (US-709 AC2).
        return ActionResult(ok=False, message=OWN_ROLE_MESSAGE)
    try:
        rows = (
            get_client()
            .table("profiles")
            .update({"role": new_role})
            .eq("id", user_id)
            .execute()
            .data
            or []
        )
    except Exception as error:
        text = _error_text(error)
        for code, message in ROLE_ERRORS.items():
            if code in text:
                return ActionResult(ok=False, message=message)
        logger.warning("change_user_role failed: %s", type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_ERROR)
    if not rows:
        return ActionResult(ok=False, message="User not found.")
    logger.info("role changed: user_id=%s new_role=%s", user_id, new_role)
    # The name was typed by a customer: escape it before it is shown as Markdown.
    name = escape_markdown(rows[0].get("display_name") or "The user")
    return ActionResult(ok=True, message=f"{name} is now {new_role}.")
