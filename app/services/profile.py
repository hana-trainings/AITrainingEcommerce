"""Learner Passport profile data (US-504, US-605 setting).

Customers may update only display_name, avatar, interests and reduce_motion.
role, email and xp_total are protected by the database and can never be changed from here.
"""

from app.models.domain import ActionResult, Profile

# Preset avatars only: no photo uploads (NFR-PRIV-02). Material Symbols names.
AVATAR_CHOICES = ("rocket", "psychology", "neurology", "bolt", "explore", "school")
INTEREST_CHOICES = (
    "Artificial Intelligence",
    "Machine Learning",
    "Data Analytics",
    "Data Engineering",
)


def get_my_profile() -> Profile | None:
    """Return the signed-in user's profile row, or None for guests. Story US-504 (U3-04)."""
    raise NotImplementedError("U3-04 US-504")


def update_profile(display_name: str, avatar: str, interests: list[str]) -> ActionResult:
    """Validate and save the editable profile fields (1-3 interests, avatar from AVATAR_CHOICES).

    Then call claim_profile_completion() for the one-time +25 XP. Story US-504 (U3-04).
    """
    raise NotImplementedError("U3-04 US-504")


def claim_profile_completion() -> ActionResult:
    """Call RPC claim_profile_completion(): the DATABASE awards +25 XP and the
    Identity Set badge once (US-601 AC2) if avatar + 1-3 interests are set.

    Error PROFILE_INCOMPLETE -> ok=False "Pick an avatar and 1-3 interests first."
    Story US-504 AC3 (U3-04).
    """
    raise NotImplementedError("U3-04 US-504")


def set_reduce_motion(enabled: bool) -> ActionResult:
    """Save the "Reduce motion" setting (turns off celebrations). Story US-605 (U2-17)."""
    raise NotImplementedError("U2-17 US-605")


def get_reduce_motion() -> bool:
    """Return True if celebrations should be skipped (guests: False). Story US-605 (U2-17)."""
    raise NotImplementedError("U2-17 US-605")
