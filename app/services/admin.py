"""Staff and owner tools (Epic E7). Admin pages are plain: no gamification.

Every page using these functions must call guard_page(*ADMIN_ROLES) first, and
the database RLS policies are the real protection (NFR-SEC-05). Course, role
and order-cancel changes are written to audit_log automatically by database
triggers (NFR-SEC-18); use RPC write_audit_log only for extra details such as
the reason for a seat adjustment.
"""

from app.models.domain import (
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

COURSE_IMAGE_BUCKET = "course-images"
ALLOWED_IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB, US-703 AC3


# ---------------------------------------------------------------- courses
def list_courses(
    search: str = "", published: bool | None = None, category_id: int | None = None
) -> list[Course]:
    """Return ALL courses (including unpublished) for the admin table, newest update first.

    published=None means both. Story US-702 (U3-01).
    """
    raise NotImplementedError("U3-01 US-702")


def validate_course_input(data: CourseInput) -> dict[str, str]:
    """Return {field: message} for every invalid field (pure function, no DB).

    Rules: title, summary (<= 200 chars), description, category, level, duration
    required; price 0-9,999; seats 1-10,000. Story US-703 AC2 (U3-03).
    """
    raise NotImplementedError("U3-03 US-703")


def create_course(data: CourseInput) -> ActionResult:
    """Insert a new course (unpublished by default; the insert must set
    seats_available = seats_total) with its modules and path positions.
    On success data={"course_id": ...}. Story US-703 (U3-03).
    """
    raise NotImplementedError("U3-03 US-703")


def get_course_for_edit(course_id: int) -> Course | None:
    """Return any course (published or not) with modules and paths for the edit form.

    Story US-704 (U3-09).
    """
    raise NotImplementedError("U3-09 US-704")


def update_course(course_id: int, data: CourseInput) -> ActionResult:
    """Save edits (sets updated_by). Past orders keep their price snapshot. Story US-704 (U3-09)."""
    raise NotImplementedError("U3-09 US-704")


def upload_course_image(file_bytes: bytes, content_type: str) -> ActionResult:
    """Upload a JPG/PNG/WebP (max 2 MB) to the 'course-images' bucket under an app-generated
    file name. On success data={"image_url": <public url>}. Story US-704 (U3-09), US-703 AC3.
    """
    raise NotImplementedError("U3-09 US-704")


def set_published(course_id: int, published: bool) -> ActionResult:
    """Publish or unpublish a course (audit logged). Story US-705 (U3-06)."""
    raise NotImplementedError("U3-06 US-705")


def adjust_seats(course_id: int, change: int, reason: str) -> ActionResult:
    """Add (+) or remove (-) seats with a reason (audit logged).

    seats_available can't go below 0 and seats_total can't go below seats sold.
    Save the reason with RPC write_audit_log(action, entity, entity_id, before, after).
    Story US-706 (U3-07).
    """
    raise NotImplementedError("U3-07 US-706")


def delete_course(course_id: int, typed_title: str) -> ActionResult:
    """Owner only: delete a course with no orders, if typed_title matches its title exactly.

    If it has orders, return ok=False suggesting unpublish. Story US-710 (U3-08).
    """
    raise NotImplementedError("U3-08 US-710")


# ---------------------------------------------------------------- categories and paths
def list_categories_and_paths() -> tuple[list[Category], list[LearningPath]]:
    """Return all categories and all paths (with ordered courses) for editing.

    Story US-711 (U3-12).
    """
    raise NotImplementedError("U3-12 US-711")


def save_category(
    name: str, icon: str, sort_order: int, category_id: int | None = None
) -> ActionResult:
    """Create (category_id=None) or update a category. icon is an emoji. Story US-711 (U3-12)."""
    raise NotImplementedError("U3-12 US-711")


def save_path(
    name: str,
    description: str,
    course_ids_in_order: list[int],
    badge_name: str,
    path_id: int | None = None,
) -> ActionResult:
    """Create (path_id=None) or update a learning path and its ordered courses.

    Story US-711 (U3-12).
    """
    raise NotImplementedError("U3-12 US-711")


# ---------------------------------------------------------------- orders and dashboard
def list_all_orders(
    status: OrderStatus | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str = "",
) -> list[Order]:
    """Return all orders with customer_email and item_count, newest first.

    search matches order number or email. Use orders.get_order() and
    email_outbox.get_email_for_order() for the detail panel. Story US-707 (U2-18).
    """
    raise NotImplementedError("U2-18 US-707")


def get_dashboard_metrics() -> DashboardMetrics:
    """Return KPI totals, orders per day (last 30 days), top 5 courses by seats sold,
    and low-seat courses. Story US-708 (U3-11).
    """
    raise NotImplementedError("U3-11 US-708")


# ---------------------------------------------------------------- staff (owner only)
def list_users() -> list[UserRow]:
    """Return all users with role and joined date (owner only).

    Reads profiles (id, display_name, email, role, created_at). Story US-709 (U3-10).
    """
    raise NotImplementedError("U3-10 US-709")


def change_user_role(user_id: str, new_role: Role) -> ActionResult:
    """Owner only: switch a user between 'customer' and 'staff' (updates profiles.role).

    The database raises NOT_ALLOWED (caller is not the owner) or LAST_OWNER (the
    last owner can't be demoted); map both to friendly text. A trigger writes the audit log.
    Story US-709 (U3-10).
    """
    raise NotImplementedError("U3-10 US-709")
