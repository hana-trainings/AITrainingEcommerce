"""Admin dashboard (doc 02 S12). Staff and owner only.

Stories: US-701 (U3-02) admin landing, US-708 (U3-11) metrics.
Plain styling, no gamification. All numbers come from real rows (US-606 AC1).
"""

import streamlit as st

from app.components.guards import guard_admin_page
from app.components.states import error_state
from app.config import routes
from app.services import admin
from app.utils.log import get_logger
from app.utils.text import escape_markdown, format_price

logger = get_logger(__name__)

user = guard_admin_page()  # stops the page for guests and customers (US-701 AC2)

st.title("Admin dashboard")
st.caption(f"Signed in as {escape_markdown(user.display_name)} ({user.role}).")

# ---------------------------------------------------------------- landing links (US-701)
with st.container(horizontal=True):
    st.page_link(routes.ADMIN_COURSES, label="Manage courses", icon=":material/list_alt:")
    st.page_link(routes.ADMIN_COURSE_FORM, label="New course", icon=":material/add:")
    st.page_link(
        routes.ADMIN_CATEGORIES_PATHS, label="Categories & paths", icon=":material/category:"
    )
    st.page_link(routes.ADMIN_ORDERS, label="Orders", icon=":material/receipt:")
    if user.role == "owner":  # the staff page checks the role again itself
        st.page_link(routes.ADMIN_STAFF, label="Staff", icon=":material/manage_accounts:")

# ---------------------------------------------------------------- metrics (US-708)
try:
    metrics = admin.get_dashboard_metrics()
except Exception as error:  # never show technical details (NFR-SEC-17)
    logger.warning("dashboard metrics failed: %s", type(error).__name__)
    error_state()
    st.stop()

with st.container(horizontal=True):
    st.metric("Total orders", metrics["total_orders"], border=True)
    st.metric("Revenue (demo)", format_price(metrics["total_revenue"]), border=True)
    st.metric("Seats sold", metrics["seats_sold"], border=True)
    st.metric("Customers", metrics["customer_count"], border=True)
st.caption("Confirmed orders only. Cancelled orders gave their seats back.")

st.subheader("Orders per day (last 30 days)")
st.bar_chart(
    metrics["orders_per_day"],
    x="day",
    y="orders",
    x_label="Day",
    y_label="Orders",
    alt="Bar chart of the number of orders on each of the last 30 days.",
)

left, right = st.columns(2)
with left:
    st.subheader("Top 5 courses by seats sold")
    if metrics["top_courses"]:
        st.dataframe(
            [
                {"Course": row["title"], "Seats sold": row["seats_sold"]}
                for row in metrics["top_courses"]
            ],
            hide_index=True,
        )
    else:
        st.caption("No seats sold yet.")
with right:
    st.subheader("Low-seat courses")
    if metrics["low_seat_courses"]:
        st.dataframe(
            [
                {
                    "Course": course["title"],
                    "Seats left": course["seats_available"],
                    "Total": course["seats_total"],
                }
                for course in metrics["low_seat_courses"]
            ],
            hide_index=True,
        )
    else:
        st.caption("No published course is low on seats.")
