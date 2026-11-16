"""My orders and order detail with email preview (doc 02 S11). Signed-in users only.

Stub created by the foundation. Replace coming_soon() with the real screen.
"""

import streamlit as st

from app.components.guards import guard_customer_page
from app.components.states import coming_soon
from app.config import routes

user = guard_customer_page(return_to=routes.MY_ORDERS)  # stops the page for guests

st.title("My orders")
coming_soon("US-407, US-408 (U2-15, U2-16)")
