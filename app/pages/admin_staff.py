"""Staff management (doc 02 S15). OWNER only (US-709 AC3).

Stub created by the foundation. Replace coming_soon() with the real screen.
"""

import streamlit as st

from app.components.guards import guard_owner_page
from app.components.states import coming_soon

user = guard_owner_page()  # stops the page for everyone except the owner

st.title("Staff management")
coming_soon("US-709 (U3-10)")
