"""Public catalog: courses, categories, learning paths (Epics E1, E2, US-604).

How this module works (read this first):

1. A few small "loader" functions read the PUBLIC catalog from Supabase:
   published courses, categories, learning paths and their course lists.
2. Those loaders are cached with @st.cache_data(ttl=60) (U1-09, NFR-PERF-03).
   The data is the same for every visitor, so one copy can be shared by all
   browser sessions for up to a minute.
3. Search, filters, sorting and paging then run in plain Python on that cached
   list. The catalog is small (tens of courses), so this is instant
   (NFR-PERF-02) and much easier to read and test than a big SQL query.

Safety rules for the cache:
- Loaders ALWAYS filter is_published = true themselves, even though RLS also
  does it for guests. Why: a staff member's session can see drafts, and if a
  staff session filled the shared cache, drafts would leak to guests.
- Nothing that depends on who is signed in (cart, orders, XP) is cached here.
- Seat counts here may be up to a minute old. That is fine for browsing, but the
  cart and checkout re-read seats FRESH (cart.get_items, place_order), NFR-PERF-04.
"""

from typing import Any

import streamlit as st

from app.models.domain import (
    Category,
    Course,
    CourseFilters,
    CourseModule,
    CoursePage,
    LearningPath,
    SortOption,
)
from app.services.supabase_client import get_client

PAGE_SIZE = 12  # US-101 AC4
CACHE_SECONDS = 60  # NFR-PERF-03: "a short TTL (e.g. 60 seconds)"

# Seat rule (US-203 AC2): "few seats" when 5 or fewer are left,
# or when 10% or less of all seats are left.
FEW_SEATS_ABSOLUTE = 5
FEW_SEATS_SHARE = 0.10

# The sort options of US-104, with the label shown in the dropdown.
SORT_LABELS: dict[str, str] = {
    "featured": "Featured",
    "newest": "Newest",
    "price_asc": "Price: low to high",
    "price_desc": "Price: high to low",
    "fewest_seats": "Fewest seats left",
}


# ---------------------------------------------------------------- seat rule
def seat_status(seats_available: int, seats_total: int) -> str:
    """Return "sold_out", "few" or "available" for a course (US-203 AC2).

    This is a business rule, so it lives in the service. The seat meter
    component and the "Almost full" strip both use it.
    """
    if seats_available <= 0:
        return "sold_out"
    if seats_available <= FEW_SEATS_ABSOLUTE:
        return "few"
    if seats_total > 0 and seats_available / seats_total <= FEW_SEATS_SHARE:
        return "few"
    return "available"


# ---------------------------------------------------------------- cached loaders
# The leading underscore means "private to this module": pages call the public
# functions further down, never these.


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def _load_categories() -> list[Category]:
    response = get_client().table("categories").select("*").order("sort_order").execute()
    return list(response.data or [])


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def _load_published_courses() -> list[Course]:
    """All published courses, with category_name added, ordered by title."""
    response = (
        get_client()
        .table("courses")
        .select("*")
        .eq("is_published", True)  # never cache drafts (see module docstring)
        .order("title")
        .execute()
    )
    category_names = {category["id"]: category["name"] for category in _load_categories()}
    courses: list[Course] = []
    for row in response.data or []:
        course: Course = dict(row)  # type: ignore[assignment]
        course["category_name"] = category_names.get(row.get("category_id"), "")
        courses.append(course)
    return courses


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def _load_paths() -> list[dict[str, Any]]:
    """Learning path rows, ordered by id (the order they were created)."""
    response = get_client().table("learning_paths").select("*").order("id").execute()
    return list(response.data or [])


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def _load_path_links() -> list[dict[str, Any]]:
    """Rows of learning_path_courses: {path_id, course_id, position}."""
    response = (
        get_client()
        .table("learning_path_courses")
        .select("path_id, course_id, position")
        .order("position")
        .execute()
    )
    return list(response.data or [])


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def _load_modules(course_id: int) -> list[CourseModule]:
    """The syllabus of one PUBLISHED course (callers make sure of that)."""
    response = (
        get_client()
        .table("course_modules")
        .select("*")
        .eq("course_id", course_id)
        .order("position")
        .execute()
    )
    return list(response.data or [])


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def _load_badge_names() -> dict[str, str]:
    """{badge code: badge name}. Badge definitions are public (anon can read them)."""
    response = get_client().table("badges").select("code, name").execute()
    return {row["code"]: row["name"] for row in response.data or []}


def clear_cache() -> None:
    """Forget the cached catalog, e.g. right after staff edit a course or an order
    changes seat counts, so the next page shows fresh data at once."""
    for loader in (
        _load_categories,
        _load_published_courses,
        _load_paths,
        _load_path_links,
        _load_modules,
        _load_badge_names,
    ):
        loader.clear()


# ---------------------------------------------------------------- small helpers
def _published_by_id() -> dict[int, Course]:
    return {course["id"]: course for course in _load_published_courses()}


def _path_course_ids(path_id: int) -> list[int]:
    """Published course ids of one path, in path order."""
    published = _published_by_id()
    links = sorted(
        (link for link in _load_path_links() if link["path_id"] == path_id),
        key=lambda link: link["position"],
    )
    return [link["course_id"] for link in links if link["course_id"] in published]


def _matches_keyword(course: Course, keyword: str) -> bool:
    """US-102 AC1: title, summary, description or a tag contains the keyword."""
    texts = [
        course.get("title", ""),
        course.get("summary", ""),
        course.get("description", ""),
        *(course.get("tags") or []),
    ]
    return any(keyword in str(text).lower() for text in texts)


def _matches_filters(course: Course, filters: CourseFilters, path_course_ids: set[int]) -> bool:
    """US-103: every filter that is set must match (AND logic, AC2)."""
    price = float(course.get("price") or 0)
    duration = float(course.get("duration_hours") or 0)
    checks = [
        not filters.get("category_ids") or course.get("category_id") in filters["category_ids"],
        not filters.get("levels") or course.get("level") in filters["levels"],
        filters.get("price_min") is None or price >= float(filters["price_min"]),
        filters.get("price_max") is None or price <= float(filters["price_max"]),
        filters.get("duration_min") is None or duration >= float(filters["duration_min"]),
        filters.get("duration_max") is None or duration <= float(filters["duration_max"]),
        not filters.get("path_id") or course.get("id") in path_course_ids,
        not filters.get("only_available") or int(course.get("seats_available") or 0) > 0,
    ]
    return all(checks)


def _sort_courses(courses: list[Course], sort: SortOption) -> list[Course]:
    """US-104 AC1. Ties are always broken by title so the order never jumps around."""
    by_title = sorted(courses, key=lambda course: str(course.get("title", "")).lower())
    if sort == "newest":
        return sorted(
            by_title, key=lambda course: str(course.get("created_at") or ""), reverse=True
        )
    if sort == "price_asc":
        return sorted(by_title, key=lambda course: float(course.get("price") or 0))
    if sort == "price_desc":
        return sorted(by_title, key=lambda course: float(course.get("price") or 0), reverse=True)
    if sort == "fewest_seats":
        # Sold-out courses have no seats "left" to buy, so they go last.
        return sorted(
            by_title,
            key=lambda course: (
                int(course.get("seats_available") or 0) <= 0,
                int(course.get("seats_available") or 0),
            ),
        )
    # "featured" (default): featured courses first, then the rest, each by title.
    return sorted(by_title, key=lambda course: not course.get("is_featured", False))


def _one_page(courses: list[Course], page: int, page_size: int) -> CoursePage:
    page_size = max(int(page_size), 1)
    page = max(int(page), 1)
    start = (page - 1) * page_size
    return {"courses": courses[start : start + page_size], "total": len(courses)}


# ---------------------------------------------------------------- public functions
def list_courses(page: int = 1, page_size: int = PAGE_SIZE) -> CoursePage:
    """Return one page of published courses with category_name filled in.

    Returns {"courses": [...], "total": <all published courses>}. Story US-101 (U1-03).
    """
    return search_courses(page=page, page_size=page_size)


def search_courses(
    keyword: str = "",
    filters: CourseFilters | None = None,
    sort: SortOption = "featured",
    page: int = 1,
    page_size: int = PAGE_SIZE,
) -> CoursePage:
    """Search published courses by keyword (title, summary, description, tags; case-insensitive),
    combine with filters (AND) and sort.

    Leading/trailing spaces in keyword are ignored; "" means all courses.
    Returns {"courses": [...], "total": <matches>}.
    Stories US-102 (U1-05), US-103 (U1-06), sort options US-104 (U1-07).
    """
    needle = (keyword or "").strip().lower()  # US-102 AC4
    filters = filters or {}
    path_course_ids = set(_path_course_ids(filters["path_id"])) if filters.get("path_id") else set()
    matches = [
        course
        for course in _load_published_courses()
        if (not needle or _matches_keyword(course, needle))
        and _matches_filters(course, filters, path_course_ids)
    ]
    return _one_page(_sort_courses(matches, sort), page, page_size)


def filter_bounds() -> dict[str, float]:
    """Highest price and duration in the catalog, for the range sliders (US-103).

    Returns {"max_price": ..., "max_duration": ...}, both at least 1 so a slider
    always has a real range.
    """
    courses = _load_published_courses()
    max_price = max((float(c.get("price") or 0) for c in courses), default=0.0)
    max_duration = max((float(c.get("duration_hours") or 0) for c in courses), default=0.0)
    return {"max_price": max(max_price, 1.0), "max_duration": max(max_duration, 1.0)}


def list_categories() -> list[Category]:
    """Return all categories ordered by sort_order (filters, card labels). Story US-103 (U1-06)."""
    return _load_categories()


def get_course(slug: str, include_unpublished: bool = False) -> Course | None:
    """Return one course with "modules" (ordered by position) and "paths"
    ([{"path_id", "path_name", "position", "course_count"}]), or None if not found.

    include_unpublished=True is only for staff preview; guests/customers get None
    for unpublished courses (US-201 AC4). Story US-201 (U1-04).
    """
    slug = (slug or "").strip()
    if not slug:
        return None
    course = next((c for c in _load_published_courses() if c.get("slug") == slug), None)
    if course is not None:
        course = dict(course)  # type: ignore[assignment]  # a copy: never change cached data
        course["modules"] = _load_modules(course["id"])
    elif include_unpublished:
        course = _load_draft_for_staff(slug)
    if course is None:
        return None
    course["paths"] = _paths_of_course(course["id"])
    return course


def _load_draft_for_staff(slug: str) -> Course | None:
    """Staff preview of a draft (US-201 AC4). Never cached: drafts are not public.

    RLS only returns draft rows to staff/owner, so a guest who forces this path
    still gets nothing back.
    """
    client = get_client()
    response = client.table("courses").select("*").eq("slug", slug).limit(1).execute()
    if not response.data:
        return None
    course: Course = dict(response.data[0])  # type: ignore[assignment]
    category_names = {category["id"]: category["name"] for category in _load_categories()}
    course["category_name"] = category_names.get(course.get("category_id"), "")
    modules = (
        client.table("course_modules")
        .select("*")
        .eq("course_id", course["id"])
        .order("position")
        .execute()
    )
    course["modules"] = list(modules.data or [])
    return course


def _paths_of_course(course_id: int) -> list[dict[str, Any]]:
    """US-201 AC3: which paths a course is in, and its step number ("Course 2 of 4")."""
    result = []
    for path in _load_paths():
        ordered_ids = _path_course_ids(path["id"])
        if course_id not in ordered_ids:
            continue
        result.append(
            {
                "path_id": path["id"],
                "path_name": path["name"],
                "position": ordered_ids.index(course_id) + 1,
                "course_count": len(ordered_ids),
            }
        )
    return result


def featured_courses(limit: int = 6) -> list[Course]:
    """Return published courses with is_featured = true. Stories US-106 (U1-13), US-105 (U1-08)."""
    featured = [course for course in _load_published_courses() if course.get("is_featured")]
    return featured[: max(limit, 0)]


def almost_full_courses(limit: int = 4) -> list[Course]:
    """Return published, not sold-out courses with the FEWEST seats left (real data only).

    Only courses that really are in the "few seats left" state (same rule as
    the seat meter) are returned, so the strip never exaggerates (US-606).
    It can be empty; the Home page then hides the strip.
    Story US-106 (U1-13).
    """
    few = [
        course
        for course in _load_published_courses()
        if seat_status(int(course.get("seats_available") or 0), int(course.get("seats_total") or 0))
        == "few"
    ]
    few.sort(key=lambda course: int(course.get("seats_available") or 0))
    return few[: max(limit, 0)]


def related_courses(course_id: int, limit: int = 4) -> list[Course]:
    """Return up to `limit` courses from the same path or category, excluding course_id.

    Courses from the same path come first (in path order), then the same category.
    Story US-205 (U1-12).
    """
    published = _published_by_id()
    same_path_ids: list[int] = []
    for path in _load_paths():
        ordered_ids = _path_course_ids(path["id"])
        if course_id in ordered_ids:
            same_path_ids.extend(ordered_ids)
    category_id = published.get(course_id, {}).get("category_id")
    same_category_ids = [
        course["id"] for course in published.values() if course.get("category_id") == category_id
    ]
    related: list[Course] = []
    for candidate_id in [*same_path_ids, *same_category_ids]:
        already_added = any(course["id"] == candidate_id for course in related)
        if candidate_id == course_id or already_added or candidate_id not in published:
            continue
        related.append(published[candidate_id])
    return related[: max(limit, 0)]


def next_in_path(owned_course_ids: set[int], limit: int = 3) -> list[Course]:
    """Return the next not-owned course of each path the user has started.

    "Started" means the user owns at least one course of the path. The next
    course is the first one in path order the user does not own yet.
    Used by "Next in your path" on Home (signed in), order confirmation (US-405 AC3)
    and the Passport. Stories US-405 (U2-05), US-205 (U1-12).
    """
    published = _published_by_id()
    suggestions: list[Course] = []
    for path in _load_paths():
        ordered_ids = _path_course_ids(path["id"])
        if not any(course_id in owned_course_ids for course_id in ordered_ids):
            continue  # the user has not started this path
        next_id = next((cid for cid in ordered_ids if cid not in owned_course_ids), None)
        if next_id is not None and all(course["id"] != next_id for course in suggestions):
            suggestions.append(published[next_id])
    return suggestions[: max(limit, 0)]


def next_course_in_path(path_id: int, course_id: int) -> Course | None:
    """Return the course right after course_id in one path, or None at the end (US-205)."""
    ordered_ids = _path_course_ids(path_id)
    if course_id not in ordered_ids:
        return None
    position = ordered_ids.index(course_id)
    if position + 1 >= len(ordered_ids):
        return None
    return _published_by_id()[ordered_ids[position + 1]]


def list_paths() -> list[LearningPath]:
    """Return all learning paths, each with "courses" in path order. Story US-604 (U1-14)."""
    published = _published_by_id()
    paths: list[LearningPath] = []
    for row in _load_paths():
        path: LearningPath = dict(row)  # type: ignore[assignment]
        path["courses"] = [published[course_id] for course_id in _path_course_ids(row["id"])]
        paths.append(path)
    return paths


def path_badge_name(path: LearningPath) -> str | None:
    """The real name of the badge a path awards, or None if the path has no badge
    (badge_code empty, or the code is not in the badges table). Story US-604 (U1-14)."""
    code = path.get("badge_code")
    if not code:
        return None
    return _load_badge_names().get(code)
