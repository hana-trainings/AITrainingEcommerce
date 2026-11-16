"""Learner Passport profile (doc 02 S10). Signed-in users only.

Stub created by the foundation. Replace coming_soon() with the real screen.
"""

import streamlit as st

from app.components.guards import guard_customer_page
from app.components.states import coming_soon
from app.config import routes

user = guard_customer_page(return_to=routes.PASSPORT)  # stops the page for guests

st.title("Learner Passport")
coming_soon("US-504, US-601, US-603 (U3-04, U3-13, U3-14)")
