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

# (level number, name, XP needed) from US-602. The database function
# level_for_xp(xp) uses the same table; keep them in sync.
LEVELS: tuple[tuple[int, str, int], ...] = (
    (1, "Novice", 0),
    (2, "Explorer", 150),
    (3, "Practitioner", 400),
    (4, "Expert", 800),
    (5, "Master", 1500),
)


def get_level_progress(xp_total: int) -> LevelProgress:
    """Return the level, its name, and the XP needed for the next level (pure function).

    Used by the header XP bar and level chip. Story US-602 (U1-17).
    """
    raise NotImplementedError("U1-17 US-602")


def list_my_xp_events() -> list[XpEvent]:
    """Return the signed-in user's XP history, newest first. Story US-601 (U3-13)."""
    raise NotImplementedError("U3-13 US-601")


def list_badges_with_status() -> list[BadgeStatus]:
    """Return every badge with earned True/False and an unlock hint. Story US-603 (U3-14)."""
    raise NotImplementedError("U3-14 US-603")


def build_path_nodes(
    path: LearningPath, owned_course_ids: set[int], cart_course_ids: set[int]
) -> list[PathNode]:
    """Turn a path's courses into nodes with state owned / in_cart / locked (pure function).

    Story US-604 (U1-14).
    """
    raise NotImplementedError("U1-14 US-604")


def get_path_progress() -> list[PathProgress]:
    """Return every path with the signed-in user's nodes and "X of Y unlocked".

    Used on the Learner Passport. Stories US-504 (U3-04), US-604 (U1-14).
    """
    raise NotImplementedError("U3-04 US-504")
