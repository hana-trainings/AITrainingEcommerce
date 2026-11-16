"""Manage categories and learning paths. Staff and owner only.

Stub created by the foundation. Replace coming_soon() with the real screen.
"""

import streamlit as st

from app.components.guards import guard_admin_page
from app.components.states import coming_soon

user = guard_admin_page()  # stops the page for guests and customers

st.title("Categories & paths")
coming_soon("US-711 (U3-12)")
