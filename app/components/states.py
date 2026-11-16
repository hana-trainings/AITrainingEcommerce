"""System states shown on any screen (doc 02 S16): empty, error, not found,
store unavailable, access denied, sign-in prompt, "coming soon", and toasts
that survive a page switch.

Polish story: U1-18. Keep these function signatures.
"""

import streamlit as st

from app.config import routes

GENERIC_ERROR = "Something went wrong, please try again."
RETURN_TO_KEY = "return_to"  # page to open after sign-in (US-401 AC1)
_FLASH_KEY = "flash_message"


def coming_soon(story_ids: str) -> None:
    """Placeholder body for a page whose story is not built yet."""
    st.info(f"Coming soon - {story_ids}", icon=":material/construction:")


def empty_state(
    title: str,
    message: str = "",
    *,
    action_label: str | None = None,
    action_page: str | None = None,
    icon: str = ":material/inbox:",
) -> None:
    """Friendly "nothing here yet" box with an optional link to another page."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        if message:
            st.caption(message)
        if action_label and action_page:
            st.page_link(action_page, label=action_label, icon=icon)


def error_state(message: str = GENERIC_ERROR) -> None:
    """Show an error without technical details (NFR-SEC-17). Log details separately."""
    st.error(message, icon=":material/error:")


def not_found(what: str = "Page") -> None:
    """Shown when a course, order or page does not exist (or is not visible to you)."""
    st.warning(f"{what} not found.", icon=":material/search_off:")
    st.page_link(routes.COURSES, label="Browse courses", icon=":material/school:")


def store_unavailable() -> None:
    """Shown when Supabase can't be reached (NFR-REL-01)."""
    st.error(
        "The store is temporarily unavailable. Please try again in a minute.",
        title="Store unavailable",
        icon=":material/cloud_off:",
    )


def access_denied() -> None:
    """Shown when the user's role may not open this page (US-701 AC2). Shows no data."""
    st.error(
        "You don't have access to this page.",
        title="You don't have access",
        icon=":material/lock:",
    )
    st.page_link(routes.HOME, label="Back to store", icon=":material/storefront:")


def sign_in_prompt(
    reason: str = "Please sign in to continue.", return_to: str | None = None
) -> None:
    """Ask a guest to sign in. After sign-in they come back to `return_to` (a routes path)."""
    if return_to:
        st.session_state[RETURN_TO_KEY] = return_to
    st.info(reason, icon=":material/login:")
    with st.container(horizontal=True):
        st.page_link(routes.SIGN_IN, label="Sign in", icon=":material/login:")
        st.page_link(routes.REGISTER, label="Create an account", icon=":material/person_add:")


def flash(message: str) -> None:
    """Queue a toast to show on the NEXT page run (use before st.switch_page)."""
    st.session_state[_FLASH_KEY] = message


def show_flash() -> None:
    """Show a queued toast once. Called by the header on every run."""
    message = st.session_state.pop(_FLASH_KEY, None)
    if message:
        st.toast(message, icon=":material/check_circle:")
