"""XP, levels, badges and path progress (Epic E6).

XP and badges are only ever AWARDED by the database (register +50 automatically,
place_order, claim_profile_completion; US-601 AC2). Badge codes: first_step,
identity_set, first_unlock, path_starter, collector, path_master_<path>.
This module only READS them and does display math.
Ethical rules (US-606): no timers, fake scarcity, random rewards, leaderboards or penalties.
"""

from app.models.domain import (
    BadgeStatus,
    LearningPath,
    LevelProgress,
    PathNode,
    PathProgress,
    XpEvent,
)
from app.services import auth, orders
from app.services.supabase_client import get_client
from app.utils.log import get_logger

logger = get_logger(__name__)

# (level number, name, XP needed) from US-602. The database function
# level_for_xp(xp) uses the same table; keep them in sync.
LEVELS: tuple[tuple[int, str, int], ...] = (
    (1, "Novice", 0),
    (2, "Explorer", 150),
    (3, "Practitioner", 400),
    (4, "Expert", 800),
    (5, "Master", 1500),
)

# Friendly names for xp_events.action, shown in the XP history (US-601).
XP_ACTION_LABELS = {
    "register": "Created your account",
    "complete_profile": "Completed your Learner Passport",
    "purchase_course": "Unlocked a course",
    "complete_path": "Completed a learning path",
}

DEFAULT_BADGE_HINT = "Keep learning to unlock this badge."


def get_level_progress(xp_total: int) -> LevelProgress:
    """Return the level, its name, and the XP needed for the next level (pure function).

    Used by the header XP bar and level chip. Story US-602 (U1-17).
    """
    xp = max(int(xp_total or 0), 0)  # XP can never be negative (no penalties, US-606)
    current = LEVELS[0]
    next_level = None
    for index, level in enumerate(LEVELS):
        if xp >= level[2]:
            current = level
            next_level = LEVELS[index + 1] if index + 1 < len(LEVELS) else None
    return LevelProgress(
        level=current[0],
        name=current[1],
        xp_total=xp,
        level_start_xp=current[2],
        next_level_xp=next_level[2] if next_level else None,
        next_level_name=next_level[1] if next_level else None,
    )


def list_my_xp_events() -> list[XpEvent]:
    """Return the signed-in user's XP history, newest first. Story US-601 (U3-13).

    Guests get an empty list. RLS also limits the rows to the caller's own events.
    """
    user = auth.current_user()
    if user is None:
        return []
    response = (
        get_client()
        .table("xp_events")
        .select("id, action, points, reference_id, created_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return [
        XpEvent(
            id=int(row.get("id") or 0),
            action=str(row.get("action") or ""),
            points=int(row.get("points") or 0),
            reference_id=int(row.get("reference_id") or 0),
            created_at=str(row.get("created_at") or ""),
        )
        for row in response.data or []
    ]


def xp_action_label(action: str) -> str:
    """Turn an xp_events.action code into friendly text (pure function)."""
    return XP_ACTION_LABELS.get(action, action.replace("_", " ").capitalize())


def _my_badge_awards(user_id: str) -> dict[str, str]:
    """Return {badge_code: awarded_at} for this user."""
    response = (
        get_client()
        .table("user_badges")
        .select("badge_code, awarded_at")
        .eq("user_id", user_id)
        .execute()
    )
    return {row["badge_code"]: str(row.get("awarded_at") or "") for row in response.data or []}


def list_badges_with_status() -> list[BadgeStatus]:
    """Return every badge with earned True/False and an unlock hint. Story US-603 (U3-14).

    Guests see every badge as locked. Only the caller's OWN badges are read, so
    nobody can compare themselves with other learners (US-606 AC3).
    """
    badges = (
        get_client()
        .table("badges")
        .select("code, name, description, icon, hint, sort_order")
        .order("sort_order")
        .execute()
        .data
        or []
    )
    user = auth.current_user()
    awards = _my_badge_awards(user.id) if user else {}
    return [
        BadgeStatus(
            code=row["code"],
            name=row.get("name") or row["code"],
            description=row.get("description") or "",
            icon=row.get("icon") or "🏅",
            sort_order=int(row.get("sort_order") or 0),
            earned=row["code"] in awards,
            awarded_at=awards.get(row["code"]),
            hint=row.get("hint") or DEFAULT_BADGE_HINT,
        )
        for row in badges
    ]


def build_path_nodes(
    path: LearningPath, owned_course_ids: set[int], cart_course_ids: set[int]
) -> list[PathNode]:
    """Turn a path's courses into nodes with state owned / in_cart / locked (pure function).

    path["courses"] must already be in path order. Owned wins over "in cart",
    because a course you own is unlocked even if it is also in the cart.
    Story US-604 (U1-14).
    """
    nodes: list[PathNode] = []
    for course in path.get("courses", []):
        course_id = int(course["id"])
        if course_id in owned_course_ids:
            state = "owned"
        elif course_id in cart_course_ids:
            state = "in_cart"
        else:
            state = "locked"
        nodes.append(
            PathNode(
                course_id=course_id,
                slug=str(course.get("slug", "")),
                title=str(course.get("title", "")),
                state=state,
            )
        )
    return nodes


def _owned_course_ids(user_id: str) -> set[int]:
    """Courses the user owns. Uses the orders service (built by another story)."""
    try:
        return orders.get_owned_course_ids(user_id)
    except NotImplementedError:
        # Until U1-10 builds it, nothing counts as owned (all nodes show as locked).
        return set()


def load_paths_with_courses() -> list[LearningPath]:
    """Read every learning path with its courses in path order.

    RLS hides draft courses from customers, so they never appear in a path.
    Also used by the admin Categories & paths page (US-711).
    """
    client = get_client()
    paths = client.table("learning_paths").select("*").order("id").execute().data or []
    links = client.table("learning_path_courses").select("*").order("position").execute().data
    courses = client.table("courses").select("id, slug, title").execute().data or []
    courses_by_id = {int(course["id"]): course for course in courses}

    result: list[LearningPath] = []
    for path in paths:
        ordered = [
            courses_by_id[int(link["course_id"])]
            for link in (links or [])
            if link["path_id"] == path["id"] and int(link["course_id"]) in courses_by_id
        ]
        result.append(LearningPath(**path, courses=ordered))  # type: ignore[typeddict-item]
    return result


def get_path_progress() -> list[PathProgress]:
    """Return every path with the signed-in user's nodes and "X of Y unlocked".

    Used on the Learner Passport. Stories US-504 (U3-04), US-604 (U1-14).
    """
    user = auth.current_user()
    owned = _owned_course_ids(user.id) if user else set()
    progress: list[PathProgress] = []
    for path in load_paths_with_courses():
        nodes = build_path_nodes(path, owned, set())
        progress.append(
            PathProgress(
                path=path,
                nodes=nodes,
                owned_count=sum(1 for node in nodes if node["state"] == "owned"),
                total_count=len(nodes),
            )
        )
    return progress


def list_my_owned_courses() -> list[dict]:
    """Courses the signed-in user owns: [{"id", "slug", "title"}], sorted by title.

    Shown on the Learner Passport (US-504 AC1). Guests get an empty list.
    """
    user = auth.current_user()
    if user is None:
        return []
    owned = _owned_course_ids(user.id)
    if not owned:
        return []
    rows = (
        get_client()
        .table("courses")
        .select("id, slug, title")
        .in_("id", sorted(owned))
        .order("title")
        .execute()
        .data
        or []
    )
    return rows
