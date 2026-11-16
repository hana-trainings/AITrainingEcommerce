"""Admin dashboard (doc 02 S12). Staff and owner only (US-701).

Stub created by the foundation. Replace coming_soon() with the real screen.
"""

import streamlit as st

from app.components.guards import guard_admin_page
from app.components.states import coming_soon

user = guard_admin_page()  # stops the page for guests and customers

st.title("Admin dashboard")
coming_soon("US-708 (U3-11); landing US-701 (U3-02)")
