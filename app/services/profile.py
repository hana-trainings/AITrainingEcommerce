"""Learner Passport profile data (US-504, US-605 setting).

Customers may update only display_name, avatar, interests and reduce_motion.
role, email and xp_total are protected by the database and can never be changed from here.
"""

import streamlit as st

from app.models.domain import ActionResult, Profile
from app.services import auth
from app.services.supabase_client import get_client
from app.utils.log import get_logger

logger = get_logger(__name__)

# Preset avatars only: no photo uploads (NFR-PRIV-02). Material Symbols names.
AVATAR_CHOICES = ("rocket", "psychology", "neurology", "bolt", "explore", "school")
INTEREST_CHOICES = (
    "Artificial Intelligence",
    "Machine Learning",
    "Data Analytics",
    "Data Engineering",
)
MAX_INTERESTS = 3

SAVE_ERROR = "We could not save your profile. Please try again."
NOT_SIGNED_IN = "Please sign in first."
PROFILE_INCOMPLETE = "Pick an avatar and 1-3 interests first."

# Remember the "Reduce motion" choice for this session, so pages that check it
# often (every celebration) don't need a database call each time.
_REDUCE_MOTION_KEY = "reduce_motion"


def get_my_profile() -> Profile | None:
    """Return the signed-in user's profile row, or None for guests. Story US-504 (U3-04)."""
    user = auth.current_user()
    if user is None:
        return None
    response = (
        get_client()
        .table("profiles")
        .select("id, email, display_name, avatar, interests, role, xp_total, level, reduce_motion")
        .eq("id", user.id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return None
    row = rows[0]
    row["interests"] = list(row.get("interests") or [])
    return Profile(**row)  # type: ignore[typeddict-item]


def validate_profile(display_name: str, avatar: str, interests: list[str]) -> dict[str, str]:
    """Return {field: message} for each problem (pure function). US-504 AC2/AC3.

    Only a display name, a PRESET avatar and preset interests are allowed, so no
    free-text personal data is ever collected (NFR-PRIV-01, NFR-PRIV-02).
    """
    errors: dict[str, str] = {}
    name = display_name.strip()
    if not name:
        errors["display_name"] = "Enter a display name."
    elif len(name) > auth.DISPLAY_NAME_MAX:
        errors["display_name"] = f"Use at most {auth.DISPLAY_NAME_MAX} characters."
    if avatar not in AVATAR_CHOICES:
        errors["avatar"] = "Pick one of the avatars."
    if not 1 <= len(interests) <= MAX_INTERESTS:
        errors["interests"] = f"Pick 1 to {MAX_INTERESTS} interests."
    elif any(interest not in INTEREST_CHOICES for interest in interests):
        errors["interests"] = "Pick interests from the list."
    elif len(set(interests)) != len(interests):
        errors["interests"] = "Pick each interest only once."
    return errors


def update_profile(display_name: str, avatar: str, interests: list[str]) -> ActionResult:
    """Validate and save the editable profile fields (1-3 interests, avatar from AVATAR_CHOICES).

    Then call claim_profile_completion() for the one-time +25 XP. Story US-504 (U3-04).
    On success data may hold {"xp_awarded": 25, "new_badges": [...], "level_up": bool}.
    """
    user = auth.current_user()
    if user is None:
        return ActionResult(ok=False, message=NOT_SIGNED_IN)
    errors = validate_profile(display_name, avatar, interests)
    if errors:
        return ActionResult(
            ok=False, message="Please fix the highlighted fields.", data={"errors": errors}
        )
    try:
        get_client().table("profiles").update(
            {"display_name": display_name.strip(), "avatar": avatar, "interests": interests}
        ).eq("id", user.id).execute()
    except Exception as error:
        logger.warning("update_profile failed: user_id=%s %s", user.id, type(error).__name__)
        return ActionResult(ok=False, message=SAVE_ERROR)

    user.display_name = display_name.strip()
    st.session_state[auth.CURRENT_USER_KEY] = user  # header shows the new name right away

    # The profile is now complete, so ask the DATABASE for the one-time reward.
    reward = claim_profile_completion()
    return ActionResult(ok=True, message="Your Learner Passport is saved.", data=reward.data)


def claim_profile_completion() -> ActionResult:
    """Call RPC claim_profile_completion(): the DATABASE awards +25 XP and the
    Identity Set badge once (US-601 AC2) if avatar + 1-3 interests are set.

    Error PROFILE_INCOMPLETE -> ok=False "Pick an avatar and 1-3 interests first."
    Story US-504 AC3 (U3-04).
    """
    if auth.current_user() is None:
        return ActionResult(ok=False, message=NOT_SIGNED_IN)
    try:
        response = get_client().rpc("claim_profile_completion", {}).execute()
    except Exception as error:
        if "PROFILE_INCOMPLETE" in str(error):
            return ActionResult(ok=False, message=PROFILE_INCOMPLETE)
        logger.warning("claim_profile_completion failed: %s", type(error).__name__)
        return ActionResult(ok=False, message=SAVE_ERROR)

    result = response.data or {}
    data = {
        "xp_awarded": int(result.get("xp_awarded") or 0),
        "new_level": int(result.get("new_level") or 0),
        "level_up": bool(result.get("level_up")),
        "new_badges": list(result.get("new_badges") or []),
    }
    if data["xp_awarded"]:
        auth.reload_current_user()  # the header shows the new XP right away
        return ActionResult(
            ok=True, message=f"+{data['xp_awarded']} XP for your Passport!", data=data
        )
    return ActionResult(ok=True, message="", data=data)  # already claimed before: nothing new


def set_reduce_motion(enabled: bool) -> ActionResult:
    """Save the "Reduce motion" setting (turns off celebrations). Story US-605 (U2-17)."""
    user = auth.current_user()
    if user is None:
        return ActionResult(ok=False, message=NOT_SIGNED_IN)
    try:
        get_client().table("profiles").update({"reduce_motion": bool(enabled)}).eq(
            "id", user.id
        ).execute()
    except Exception as error:
        logger.warning("set_reduce_motion failed: user_id=%s %s", user.id, type(error).__name__)
        return ActionResult(ok=False, message="We could not save this setting. Please try again.")
    st.session_state[_REDUCE_MOTION_KEY] = bool(enabled)
    message = "Celebrations are off." if enabled else "Celebrations are on."
    return ActionResult(ok=True, message=message)


def get_reduce_motion() -> bool:
    """Return True if celebrations should be skipped (guests: False). Story US-605 (U2-17)."""
    user = auth.current_user()
    if user is None:
        return False
    if _REDUCE_MOTION_KEY in st.session_state:
        return bool(st.session_state[_REDUCE_MOTION_KEY])
    try:
        rows = (
            get_client()
            .table("profiles")
            .select("reduce_motion")
            .eq("id", user.id)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as error:
        logger.info("get_reduce_motion failed: %s", type(error).__name__)
        return False  # celebrations are harmless, so fall back to the default
    enabled = bool(rows[0].get("reduce_motion")) if rows else False
    st.session_state[_REDUCE_MOTION_KEY] = enabled
    return enabled
