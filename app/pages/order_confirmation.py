"""Order confirmation (doc 02 S8). Signed-in users only.

Order id is in st.query_params[routes.ORDER_PARAM].

Stub created by the foundation. Replace coming_soon() with the real screen.
"""

import streamlit as st

from app.components.guards import guard_customer_page
from app.components.states import coming_soon
from app.config import routes

user = guard_customer_page(return_to=routes.MY_ORDERS)  # stops the page for guests

st.title("Order confirmed")
coming_soon("US-405, US-605 (U2-05, U2-17)")
