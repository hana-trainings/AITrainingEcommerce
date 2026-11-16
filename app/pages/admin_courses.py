"""Admin course list (doc 02 S13). Staff and owner only.

Stub created by the foundation. Replace coming_soon() with the real screen.
"""

import streamlit as st

from app.components.guards import guard_admin_page
from app.components.states import coming_soon

user = guard_admin_page()  # stops the page for guests and customers

st.title("Manage courses")
coming_soon("US-702, US-705, US-706, US-710 (U3-01, U3-06, U3-07, U3-08)")
