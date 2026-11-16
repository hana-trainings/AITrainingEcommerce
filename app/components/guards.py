"""Page guards: the FIRST line of every page that needs a signed-in user or a role.

    user = guard_customer_page(return_to=routes.CHECKOUT)   # any signed-in user
    user = guard_admin_page()                               # staff or owner
    user = guard_owner_page()                               # owner only

If the check fails, the guard shows a message and STOPS the page, so no data
below it is loaded. The role is read fresh from the database on every page load
(NFR-SEC-10). Database RLS is still the real protection (NFR-SEC-05).
"""

import streamlit as st

from app.components.states import access_denied, sign_in_prompt
from app.models.domain import ADMIN_ROLES, OWNER_ONLY, SIGNED_IN_ROLES, CurrentUser, Role
from app.services import auth


def _guard(
    allowed_roles: tuple[Role, ...], guest_sees_sign_in: bool, return_to: str | None
) -> CurrentUser:
    if auth.current_user() is None and guest_sees_sign_in:
        sign_in_prompt("Please sign in to see this page.", return_to=return_to)
        st.stop()
    user = auth.require_role(*allowed_roles)
    if user is None:
        access_denied()
        st.stop()
    return user  # type: ignore[return-value]  # st.stop() above means user is set here


def guard_customer_page(return_to: str | None = None) -> CurrentUser:
    """Any signed-in user (customer, staff, owner). Guests get a sign-in prompt."""
    return _guard(SIGNED_IN_ROLES, guest_sees_sign_in=True, return_to=return_to)


def guard_admin_page() -> CurrentUser:
    """Staff and owner only. Everyone else (guests too) sees "You don't have access" (US-701)."""
    return _guard(ADMIN_ROLES, guest_sees_sign_in=False, return_to=None)


def guard_owner_page() -> CurrentUser:
    """Owner only (staff management, US-709 AC3)."""
    return _guard(OWNER_ONLY, guest_sees_sign_in=False, return_to=None)
