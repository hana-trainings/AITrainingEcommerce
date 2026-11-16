"""Checkout (doc 02 S7). Signed-in users only; guests are asked to sign in (US-401).

Stub created by the foundation. Replace coming_soon() with the real screen.
"""

import streamlit as st

from app.components.guards import guard_customer_page
from app.components.states import coming_soon
from app.config import routes

user = guard_customer_page(return_to=routes.CHECKOUT)  # stops the page for guests

st.title("Checkout")
coming_soon("US-402, US-404 (U2-03, U2-07)")
