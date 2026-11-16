"""Sign in, sign out, register, and role checks (US-501, US-502, US-503, US-701).

How sign-in state is kept:
- The Supabase client for this browser session lives in st.session_state
  (see supabase_client.py). It holds the access and refresh tokens in memory.
- A copy of the tokens is kept under AUTH_TOKENS_KEY so the token-refresh story
  (U3-15) can use them. Tokens are never logged, written to files or shown.
- The signed-in user's public info (CurrentUser) is kept under CURRENT_USER_KEY.

Security notes for learners:
- Error messages are generic so nobody can find out which emails are registered.
- The role is ALWAYS re-read from the database in require_role(), because a
  role can change while someone is signed in (NFR-SEC-10). The database's Row
  Level Security is the real protection; these checks just give a nice page.
"""

import re

import streamlit as st

from app.models.domain import ActionResult, CurrentUser, Role
from app.services.supabase_client import get_client, reset_client
from app.utils.log import get_logger

logger = get_logger(__name__)

CURRENT_USER_KEY = "current_user"
AUTH_TOKENS_KEY = "auth_tokens"

GENERIC_SIGN_IN_ERROR = "Email or password is incorrect."
GENERIC_REGISTER_ERROR = "We could not create your account. Please try again."
DUPLICATE_EMAIL_ERROR = "An account with this email already exists."

DISPLAY_NAME_MAX = 50
EMAIL_MAX = 254
PASSWORD_MIN = 8
PASSWORD_MAX = 72  # Supabase (bcrypt) ignores characters after 72 bytes

# A simple shape check only; Supabase does the real email validation.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------- validation (pure functions)
def validate_password(password: str) -> list[str]:
    """Return a list of problems with the password (empty list = OK). NFR-SEC-03."""
    problems = []
    if len(password) < PASSWORD_MIN:
        problems.append(f"Use at least {PASSWORD_MIN} characters.")
    if len(password) > PASSWORD_MAX:
        problems.append(f"Use at most {PASSWORD_MAX} characters.")
    if not re.search(r"[A-Za-z]", password):
        problems.append("Include at least one letter.")
    if not re.search(r"\d", password):
        problems.append("Include at least one number.")
    return problems


def validate_registration(
    display_name: str, email: str, password: str, confirm_password: str
) -> dict[str, str]:
    """Check the register form. Returns {field_name: message} for each problem (US-501 AC2)."""
    errors: dict[str, str] = {}
    name = display_name.strip()
    if not name:
        errors["display_name"] = "Enter a display name."
    elif len(name) > DISPLAY_NAME_MAX:
        errors["display_name"] = f"Use at most {DISPLAY_NAME_MAX} characters."

    clean_email = email.strip()
    if not clean_email or len(clean_email) > EMAIL_MAX or not _EMAIL_PATTERN.match(clean_email):
        errors["email"] = "Enter a valid email address."

    password_problems = validate_password(password)
    if password_problems:
        errors["password"] = " ".join(password_problems)
    elif password != confirm_password:
        errors["confirm_password"] = "The passwords do not match."  # noqa: S105 (a message)
    return errors


# ---------------------------------------------------------------- session helpers
def current_user() -> CurrentUser | None:
    """Return the signed-in user from this session, or None for a guest."""
    return st.session_state.get(CURRENT_USER_KEY)


def _remember_session(session: object, user: CurrentUser) -> None:
    """Keep tokens and user info in this browser session only (NFR-AUTH-03)."""
    st.session_state[AUTH_TOKENS_KEY] = {
        "access_token": getattr(session, "access_token", None),
        "refresh_token": getattr(session, "refresh_token", None),
        "expires_at": getattr(session, "expires_at", None),
    }
    st.session_state[CURRENT_USER_KEY] = user


def _load_profile_row(user_id: str) -> dict:
    """Read this user's profile row. Returns {} if it cannot be read."""
    response = (
        get_client()
        .table("profiles")
        .select("display_name, role, xp_total, level")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else {}


def _build_current_user(auth_user: object) -> CurrentUser:
    user_id = str(getattr(auth_user, "id", ""))
    email = getattr(auth_user, "email", "") or ""
    metadata = getattr(auth_user, "user_metadata", None) or {}
    profile = _load_profile_row(user_id)
    return CurrentUser(
        id=user_id,
        email=email,
        display_name=profile.get("display_name") or metadata.get("display_name") or "Learner",
        role=profile.get("role") or "customer",
        xp_total=int(profile.get("xp_total") or 0),
        level=int(profile.get("level") or 1),
    )


# ---------------------------------------------------------------- public functions
def sign_in(email: str, password: str) -> ActionResult:
    """Sign in with email + password (US-502).

    Returns ActionResult(ok=True) on success, otherwise ok=False with the
    generic message "Email or password is incorrect." (NFR-AUTH-07).
    """
    if not email.strip() or not password:
        return ActionResult(ok=False, message=GENERIC_SIGN_IN_ERROR)
    try:
        response = get_client().auth.sign_in_with_password(
            {"email": email.strip(), "password": password}
        )
        if response.user is None or response.session is None:
            return ActionResult(ok=False, message=GENERIC_SIGN_IN_ERROR)
        user = _build_current_user(response.user)
    except Exception as error:  # any failure gets the same generic message
        # Only the error TYPE is logged: messages can contain the email address.
        logger.info("sign_in failed: %s", type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_SIGN_IN_ERROR)

    _remember_session(response.session, user)
    # U2-14 (US-306) adds ONE call here: cart.merge_guest_cart(user.id)
    logger.info("sign_in ok: user_id=%s role=%s", user.id, user.role)
    return ActionResult(ok=True, message=f"Welcome back, {user.display_name}!")


def register(display_name: str, email: str, password: str, confirm_password: str) -> ActionResult:
    """Create a customer account and sign the user in (US-501).

    The display name goes into the user metadata; a database trigger creates the
    profiles row with role 'customer' (the role can never be chosen by the client,
    NFR-SEC-01). Returns ActionResult; on validation problems, `data["errors"]`
    holds {field_name: message} for inline errors.
    """
    errors = validate_registration(display_name, email, password, confirm_password)
    if errors:
        return ActionResult(
            ok=False, message="Please fix the highlighted fields.", data={"errors": errors}
        )

    try:
        response = get_client().auth.sign_up(
            {
                "email": email.strip(),
                "password": password,
                "options": {"data": {"display_name": display_name.strip()}},
            }
        )
    except Exception as error:
        if _is_duplicate_email_error(error):
            return ActionResult(ok=False, message=DUPLICATE_EMAIL_ERROR)
        logger.warning("register failed: %s", type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_REGISTER_ERROR)

    if response.user is None or response.session is None:
        # No session means email confirmation is ON in Supabase; the demo needs it OFF.
        logger.warning("register returned no session; is email confirmation disabled?")
        return ActionResult(ok=False, message=GENERIC_REGISTER_ERROR)

    user = _build_current_user(response.user)
    _remember_session(response.session, user)
    logger.info("register ok: user_id=%s", user.id)
    return ActionResult(ok=True, message=f"Welcome, {user.display_name}! Your account is ready.")


def _is_duplicate_email_error(error: Exception) -> bool:
    code = str(getattr(error, "code", "") or "")
    text = str(error).lower()
    return code in ("user_already_exists", "email_exists") or "already registered" in text


def sign_out() -> None:
    """Sign out and forget everything about this session (US-503, NFR-AUTH-05)."""
    if CURRENT_USER_KEY in st.session_state:
        try:
            get_client().auth.sign_out()
        except Exception as error:  # we still clear local state below
            logger.info("sign_out remote call failed: %s", type(error).__name__)
    # Clear tokens, user, guest cart and every other per-session value.
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    reset_client()


def fetch_role(user_id: str) -> Role | None:
    """Read the user's CURRENT role from the database, or None if it can't be read."""
    try:
        role = _load_profile_row(user_id).get("role")
    except Exception as error:
        logger.warning("fetch_role failed: user_id=%s %s", user_id, type(error).__name__)
        return None
    return role if role in ("customer", "staff", "owner") else None


def require_role(*allowed_roles: Role) -> CurrentUser | None:
    """Return the signed-in user if their role (read fresh from the DB) is allowed.

    Returns None for guests, for users with another role, or if the role can't be
    read (we "fail closed"). Pages normally call components.guards.guard_page(),
    which uses this and shows the right message. US-701 AC2, NFR-SEC-10.
    """
    user = current_user()
    if user is None:
        return None
    role = fetch_role(user.id)
    if role is None:
        return None
    if role != user.role:
        # Role changed since sign-in (e.g. owner promoted/demoted them): remember the new one.
        user.role = role
        st.session_state[CURRENT_USER_KEY] = user
    return user if role in allowed_roles else None


def refresh_session() -> bool:
    """Refresh an expired access token with the refresh token (U3-15, NFR-AUTH-04).

    Returns True if the session is still valid (refreshed or not expired yet).
    Returns False if refresh failed; the caller then calls sign_out() and shows
    "Your session expired, please sign in again."
    """
    raise NotImplementedError("U3-15 NFR-AUTH-04")
