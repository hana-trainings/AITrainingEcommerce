"""Sign in (doc 02 S9). Stories US-502 (foundation), US-505 note (U1-16).

After a successful sign-in the user goes back to the page that asked them to
sign in (e.g. checkout, US-401), or to Home.
"""

import streamlit as st

from app.components.states import RETURN_TO_KEY, flash
from app.config import routes
from app.services import auth

st.title("Sign in")

user = auth.current_user()
if user is not None:
    st.success("You are already signed in.", icon=":material/check_circle:")
    st.page_link(routes.PASSPORT, label="Go to your Learner Passport", icon=":material/badge:")
    st.stop()

# A form sends email + password together, only when the button is pressed.
with st.form("sign_in_form"):
    email = st.text_input("Email", max_chars=254, autocomplete="email")
    # type="password" hides the text and adds a show/hide toggle.
    password = st.text_input(
        "Password", type="password", max_chars=72, autocomplete="current-password"
    )
    submitted = st.form_submit_button("Sign in", type="primary", icon=":material/login:")

if submitted:
    with st.spinner("Signing you in..."):
        result = auth.sign_in(email, password)
    if result.ok:
        flash(result.message)
        st.switch_page(st.session_state.pop(RETURN_TO_KEY, routes.HOME))
    else:
        st.error(result.message, icon=":material/error:")

# US-505: password reset emails are out of scope for the demo (doc 00 Q3).
st.caption("Forgot password? Ask your trainer.")
st.page_link(routes.REGISTER, label="New here? Create an account", icon=":material/person_add:")
