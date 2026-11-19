"""My orders and order detail with email preview (doc 02 S11). Signed-in users only.

Stories: US-407 order history (U2-15), US-408 order status shown (U2-16).
Cancelling is a staff action (US-408 AC2) and lives on the admin orders page.
"""

import streamlit as st

from app.components.guards import guard_customer_page
from app.components.states import empty_state, error_state
from app.components.status_badge import status_badge
from app.config import routes
from app.services import email_outbox, orders
from app.utils.log import get_logger
from app.utils.text import escape_markdown, format_price

logger = get_logger(__name__)

user = guard_customer_page(return_to=routes.MY_ORDERS)  # stops the page for guests

st.title("My orders")

try:
    my_orders = orders.list_my_orders()
except Exception as error:
    logger.warning("my_orders: could not load orders: %s", type(error).__name__)
    error_state()
    st.stop()

if not my_orders:
    empty_state(
        "No orders yet",
        "When you place an order, it shows up here.",
        action_label="Browse courses",
        action_page=routes.COURSES,
        icon=":material/school:",
    )
    st.stop()

# AC1: newest first with number, date, total, item count, status.
st.dataframe(
    [
        {
            "Order": order["order_number"],
            "Date": orders.readable_date(order["created_at"]),
            "Total": format_price(order["total"]),
            "Seats": order["item_count"],
            "Status": order["status"].title(),
        }
        for order in my_orders
    ],
    hide_index=True,
    alt="My orders, newest first",
)

# AC2: open one order to see its details and the saved email.
labels = {order["id"]: order["order_number"] for order in my_orders}
requested = st.query_params.get(routes.ORDER_PARAM, "")
default_index = next((i for i, order in enumerate(my_orders) if str(order["id"]) == requested), 0)
selected_id = st.selectbox(
    "Open an order",
    options=list(labels),
    index=default_index,
    format_func=lambda order_id: labels[order_id],
    key="my_orders_selected",
)
selected = next(order for order in my_orders if order["id"] == selected_id)

with st.container(border=True):
    st.subheader(f"Order {escape_markdown(selected['order_number'])}", anchor=False)
    status_badge(selected["status"])
    st.markdown(
        f"Date: **{orders.readable_date(selected['created_at'])}** · "
        f"Total: **{format_price(selected['total'])}** · XP earned: **+{selected['xp_awarded']}**"
    )
    st.dataframe(orders.item_rows(selected), hide_index=True, alt="Courses in this order")

    show_email = st.toggle("View confirmation email", key=f"my_orders_email_{selected_id}")
    if show_email:  # only load the email when asked for
        try:
            email = email_outbox.get_email_for_order(selected_id)
        except Exception as error:
            logger.info("my_orders: email not loaded: %s", type(error).__name__)
            email = None
        if email:
            st.caption(f"Subject: {escape_markdown(email['subject'])}")
            # Shown with simple tags only: links and forms in a stored row can't work.
            with st.container(border=True):
                st.html(email_outbox.safe_preview_html(email["html_body"]))
        else:
            st.info("No saved email for this order.", icon=":material/mail:")
