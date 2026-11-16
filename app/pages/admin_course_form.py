"""Create / edit course form (doc 02 S13). Staff and owner only.

Stub created by the foundation. Replace coming_soon() with the real screen.
"""

import streamlit as st

from app.components.guards import guard_admin_page
from app.components.states import coming_soon

user = guard_admin_page()  # stops the page for guests and customers

st.title("Course editor")
coming_soon("US-703, US-704 (U3-03, U3-09)")
