"""Public catalog: courses, categories, learning paths (Epics E1, E2, US-604).

Stories fill in these stubs. Keep the signatures; if one must change, open a
small separate PR first (work plan section 4.2).

Caching (U1-09, NFR-PERF-03): published catalog data is the same for everyone,
so it may be cached with @st.cache_data(ttl=60). Never cache anything that
depends on who is signed in, and never cache seat counts used at checkout.
Guests and customers only ever see is_published = true courses (RLS also
enforces this).
"""

from app.models.domain import Category, Course, CourseFilters, CoursePage, LearningPath, SortOption

PAGE_SIZE = 12  # US-101 AC4


def list_courses(page: int = 1, page_size: int = PAGE_SIZE) -> CoursePage:
    """Return one page of published courses with category_name filled in.

    Returns {"courses": [...], "total": <all published courses>}. Story US-101 (U1-03).
    """
    raise NotImplementedError("U1-03 US-101")


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
    raise NotImplementedError("U1-05 US-102 / U1-06 US-103 / U1-07 US-104")


def list_categories() -> list[Category]:
    """Return all categories ordered by sort_order (filters, card labels). Story US-103 (U1-06)."""
    raise NotImplementedError("U1-06 US-103")


def get_course(slug: str, include_unpublished: bool = False) -> Course | None:
    """Return one course with "modules" (ordered by position) and "paths"
    ([{"path_id", "path_name", "position", "course_count"}]), or None if not found.

    include_unpublished=True is only for staff preview; guests/customers get None
    for unpublished courses (US-201 AC4). Story US-201 (U1-04).
    """
    raise NotImplementedError("U1-04 US-201")


def featured_courses(limit: int = 6) -> list[Course]:
    """Return published courses with is_featured = true. Stories US-106 (U1-13), US-105 (U1-08)."""
    raise NotImplementedError("U1-13 US-106")


def almost_full_courses(limit: int = 4) -> list[Course]:
    """Return published, not sold-out courses with the FEWEST seats left (real data only).

    Story US-106 (U1-13).
    """
    raise NotImplementedError("U1-13 US-106")


def related_courses(course_id: int, limit: int = 4) -> list[Course]:
    """Return up to `limit` courses from the same path or category, excluding course_id.

    Story US-205 (U1-12).
    """
    raise NotImplementedError("U1-12 US-205")


def next_in_path(owned_course_ids: set[int], limit: int = 3) -> list[Course]:
    """Return the next not-owned course of each path the user has started.

    Used by "Next in your path" on Home (signed in), order confirmation (US-405 AC3)
    and the Passport. Stories US-405 (U2-05), US-205 (U1-12).
    """
    raise NotImplementedError("U2-05 US-405")


def list_paths() -> list[LearningPath]:
    """Return all learning paths, each with "courses" in path order. Story US-604 (U1-14)."""
    raise NotImplementedError("U1-14 US-604")
