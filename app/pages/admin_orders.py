"""Admin orders with detail panel (doc 02 S14). Staff and owner only.

Stories: US-707 view orders (U2-18), US-408 cancel order (U2-16).
The list comes from admin.list_all_orders (built by the Account track).
"""

from datetime import date, timedelta

import streamlit as st

from app.components.guards import guard_admin_page
from app.components.states import empty_state, error_state, flash
from app.components.status_badge import status_badge
from app.services import admin, email_outbox, orders
from app.utils.log import get_logger
from app.utils.text import escape_markdown, format_price

logger = get_logger(__name__)

user = guard_admin_page()  # stops the page for guests and customers

st.title("Orders")

# ---------------------------------------------------------------- filters (AC2)
STATUS_CHOICES = {"All": None, "Confirmed": "confirmed", "Cancelled": "cancelled"}
with st.container(horizontal=True, vertical_alignment="bottom"):
    status_label = st.segmented_control(
        "Status", list(STATUS_CHOICES), default="All", key="admin_orders_status"
    )
    use_dates = st.toggle("Filter by date", key="admin_orders_use_dates")
    search = st.text_input("Search", placeholder="Order number or email", key="admin_orders_search")

date_from = date_to = None
date_range = None
if use_dates:
    date_range = st.date_input(
        "Date range",
        value=(date.today() - timedelta(days=30), date.today()),
        key="admin_orders_dates",
    )
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    date_from, date_to = date_range[0].isoformat(), date_range[1].isoformat()

try:
    all_orders = admin.list_all_orders(
        status=STATUS_CHOICES.get(status_label or "All"),
        date_from=date_from,
        date_to=date_to,
        search=search.strip(),
    )
except NotImplementedError:  # until the Account track builds admin.list_all_orders
    st.info("The order list is not ready yet.", icon=":material/construction:")
    st.stop()
except Exception as error:
    logger.warning("admin_orders: could not load orders: %s", type(error).__name__)
    error_state()
    st.stop()

if not all_orders:
    empty_state("No orders match these filters", "Try another date range or status.")
    st.stop()

# ---------------------------------------------------------------- table (AC1)
st.dataframe(
    [
        {
            "Order": order.get("order_number", ""),
            "Customer email": order.get("customer_email", ""),
            "Date": orders.readable_date(order.get("created_at", "")),
            "Total": format_price(order.get("total")),
            "Seats": order.get("item_count", 0),
            "Status": str(order.get("status", "")).title(),
        }
        for order in all_orders
    ],
    hide_index=True,
    alt="All orders",
)

# ---------------------------------------------------------------- detail panel (AC3)
labels = {
    order["id"]: f"{order.get('order_number', '')} · {order.get('customer_email', '')}"
    for order in all_orders
}
selected_id = st.selectbox(
    "Open an order",
    options=list(labels),
    format_func=lambda order_id: labels[order_id],
    key="admin_orders_selected",
)

try:
    detail = orders.get_order(selected_id)
except Exception as error:
    logger.warning("admin_orders: could not load order: %s", type(error).__name__)
    detail = None
if detail is None:
    error_state("This order could not be loaded.")
    st.stop()


CONFIRM_CANCEL_KEY = "admin_orders_confirm_cancel"  # order id waiting for "Yes, cancel"


def ask_cancel(order_id: int) -> None:
    st.session_state[CONFIRM_CANCEL_KEY] = order_id


def do_cancel(order_id: int) -> None:
    flash(orders.cancel_order(order_id).message)
    st.session_state.pop(CONFIRM_CANCEL_KEY, None)


def keep_order() -> None:
    st.session_state.pop(CONFIRM_CANCEL_KEY, None)


def cancel_controls(order_id: int, order_number: str) -> None:
    """Cancel button with a confirmation step (S14). Seats go back; XP is kept (no penalties)."""
    if st.session_state.get(CONFIRM_CANCEL_KEY) != order_id:
        st.button(
            "Cancel order...",
            icon=":material/cancel:",
            key="admin_cancel_open",
            on_click=ask_cancel,
            args=(order_id,),
        )
        return
    st.warning(
        f"Cancel order **{escape_markdown(order_number)}**? Its seats go back to the courses. "
        "The customer keeps their XP and badges.",
        icon=":material/warning:",
    )
    with st.container(horizontal=True):
        st.button(
            "Yes, cancel order",
            type="primary",
            icon=":material/cancel:",
            key="admin_cancel_yes",
            on_click=do_cancel,
            args=(order_id,),
        )
        st.button("Keep order", key="admin_cancel_no", on_click=keep_order)


with st.container(border=True):
    st.subheader(f"Order {escape_markdown(detail['order_number'])}", anchor=False)
    status_badge(detail["status"])
    st.markdown(
        f"Customer: **{escape_markdown(labels[selected_id].split(' · ', 1)[-1])}** · "
        f"Date: **{orders.readable_date(detail['created_at'])}** · "
        f"Total: **{format_price(detail['total'])}**"
    )
    st.dataframe(orders.item_rows(detail), hide_index=True, alt="Courses in this order")

    if detail["status"] == "confirmed":
        cancel_controls(detail["id"], detail["order_number"])

    if st.toggle("View confirmation email", key=f"admin_orders_email_{selected_id}"):
        try:
            email = email_outbox.get_email_for_order(selected_id)
        except Exception as error:
            logger.info("admin_orders: email not loaded: %s", type(error).__name__)
            email = None
        if email:
            st.caption(
                f"To: {escape_markdown(email['to_email'])} · "
                f"Subject: {escape_markdown(email['subject'])}"
            )
            with st.container(border=True):
                # Simple tags only, no attributes: links and forms in a stored row are inert.
                st.html(email_outbox.safe_preview_html(email["html_body"]))
        else:
            st.info("No saved email for this order.", icon=":material/mail:")
