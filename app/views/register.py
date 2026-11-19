"""Register (doc 02 S9). Public. Story US-501 (U3-05).

The form only asks for display name, email and password (NFR-PRIV-01). Every new
account is a customer: the role is set by the database, never by this page
(NFR-SEC-01). On success the user is signed in and goes back to where they were.
"""

import streamlit as st

from app.components.states import RETURN_TO_KEY, flash
from app.config import routes
from app.services import auth

st.title("Create your account")

if auth.current_user() is not None:
    st.success("You are already signed in.", icon=":material/check_circle:")
    st.page_link(routes.PASSPORT, label="Go to your Learner Passport", icon=":material/badge:")
    st.stop()

# S9: show the (real) reward for joining. The database awards it, never this page.
st.info(
    "Join and earn your first badge + 50 XP.",
    title="Start your skill map",
    icon=":material/military_tech:",
)
# NFR-PRIV-06: learners should not use their personal email address.
st.caption("Please use a test or training email address, not your personal one.")

# Feedback from the last failed attempt, kept across the rerun below.
FEEDBACK_KEY = "register_feedback"
feedback: dict = st.session_state.get(FEEDBACK_KEY, {})
errors: dict[str, str] = feedback.get("errors", {})
if feedback.get("message") and feedback.get("needs_confirmation"):
    # The account WAS created; it only waits for the email link, so this is not an error.
    st.info(feedback["message"], icon=":material/mark_email_unread:")
elif feedback.get("message"):
    st.error(feedback["message"], icon=":material/error:")

with st.form("register_form"):
    display_name = st.text_input(
        "Display name",
        max_chars=auth.DISPLAY_NAME_MAX,
        help="Shown on your Learner Passport. A nickname is fine.",
        autocomplete="nickname",
    )
    if "display_name" in errors:
        st.error(errors["display_name"], icon=":material/error:")
    email = st.text_input("Email", max_chars=auth.EMAIL_MAX, autocomplete="email")
    if "email" in errors:
        st.error(errors["email"], icon=":material/error:")
    password = st.text_input(
        "Password",
        type="password",
        max_chars=auth.PASSWORD_MAX,
        autocomplete="new-password",
    )
    # Password rules are always visible under the field (doc 02 S9, NFR-SEC-03).
    st.caption(f"At least {auth.PASSWORD_MIN} characters, with at least one letter and one number.")
    if "password" in errors:
        st.error(errors["password"], icon=":material/error:")
    confirm_password = st.text_input(
        "Confirm password",
        type="password",
        max_chars=auth.PASSWORD_MAX,
        autocomplete="new-password",
    )
    if "confirm_password" in errors:
        st.error(errors["confirm_password"], icon=":material/error:")
    submitted = st.form_submit_button(
        "Create account", type="primary", icon=":material/person_add:"
    )

if submitted:
    with st.spinner("Creating your account..."):
        result = auth.register(display_name, email, password, confirm_password)
    if result.ok:
        st.session_state.pop(FEEDBACK_KEY, None)
        flash(result.message)
        st.switch_page(st.session_state.pop(RETURN_TO_KEY, routes.HOME))
    else:
        # Generic messages only (e.g. duplicate email), never technical details.
        st.session_state[FEEDBACK_KEY] = {
            "message": result.message,
            "errors": result.data.get("errors", {}),
            "needs_confirmation": result.data.get("needs_confirmation", False),
        }
        st.rerun()  # draw the messages next to the fields

st.page_link(routes.SIGN_IN, label="Already have an account? Sign in", icon=":material/login:")
