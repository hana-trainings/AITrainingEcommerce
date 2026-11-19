"""Order confirmation (doc 02 S8). Signed-in users only.

Order id is in st.query_params[routes.ORDER_PARAM].
Stories: US-405 confirmation page (U2-05), US-605 celebrations (U2-17).
"""

import streamlit as st

from app.components.course_card import course_card
from app.components.guards import guard_customer_page
from app.components.states import error_state, flash, not_found
from app.config import routes
from app.services import cart, catalog, email_outbox, orders, profile
from app.utils.log import get_logger
from app.utils.text import escape_markdown, format_price

logger = get_logger(__name__)

user = guard_customer_page(return_to=routes.MY_ORDERS)  # stops the page for guests

order_id = st.query_params.get(routes.ORDER_PARAM, "")
try:
    order = orders.get_order(order_id) if order_id else None
except Exception as error:
    logger.warning("confirmation: could not load order: %s", type(error).__name__)
    error_state()
    st.stop()

# RLS hides other customers' orders, but staff and owner may read ALL orders. This page
# is only for the buyer, so an order that isn't yours is "not found" for everyone.
if order is None or order.get("user_id") != user.id:
    not_found("Order")
    st.stop()


def reduce_motion() -> bool:
    """True if this user turned celebrations off (US-605 AC2)."""
    try:
        return profile.get_reduce_motion()
    except NotImplementedError:  # until the Account agent builds the setting
        return False
    except Exception as error:
        logger.info("reduce motion not loaded: %s", type(error).__name__)
        return False


# Celebration data is only there right after placing THIS order (not on a later visit).
celebration = st.session_state.get(orders.CELEBRATION_KEY) or {}
is_fresh = celebration.get("order_id") == order["id"] and celebration.get("show")
if is_fresh:
    st.session_state.pop(orders.CELEBRATION_KEY, None)
    if not reduce_motion():
        st.balloons()

if order["status"] == "cancelled":
    st.title("Order cancelled", anchor=False)
    st.warning(
        f"Order **{escape_markdown(order['order_number'])}** was cancelled.",
        icon=":material/cancel:",
    )
else:
    st.title("Order confirmed", anchor=False)
    st.success(
        f"Thank you! Order **{escape_markdown(order['order_number'])}** is confirmed.",
        icon=":material/check_circle:",
    )
st.markdown(
    f"Date: **{orders.readable_date(order['created_at'])}** · "
    f"Total: **{format_price(order['total'])}** · "
    f"Status: **{order['status'].title()}**"
)
st.dataframe(orders.item_rows(order), hide_index=True, alt="Courses in this order")

# Email note (US-406): the email is saved, never sent.
try:
    email = email_outbox.get_email_for_order(order["id"])
except Exception as error:
    logger.info("confirmation: email not loaded: %s", type(error).__name__)
    email = None
if email:
    st.info(
        f"Confirmation email saved for **{escape_markdown(email['to_email'])}** "
        "(demo: no real email is sent).",
        icon=":material/mail:",
    )
else:
    st.info(
        f"Your order is confirmed for **{escape_markdown(user.email)}**. "
        "The email copy could not be saved, but you can see this order in My orders.",
        icon=":material/mail:",
    )

# Celebration summary card (US-405 AC2): real numbers only (US-606).
with st.container(border=True):
    st.subheader("What you earned", anchor=False)
    st.markdown(f":material/bolt: **+{order['xp_awarded']} XP**")
    if is_fresh and celebration.get("level_up"):
        st.markdown(
            f":material/military_tech: You reached **level {celebration.get('new_level')}**!"
        )
    badges = orders.badge_names(order.get("badges_awarded", []))
    if badges:
        st.markdown(
            ":material/workspace_premium: Badges unlocked: "
            + ", ".join(f"**{escape_markdown(name)}**" for name in badges)
        )
    if not order["xp_awarded"] and not badges:
        st.caption("You already owned these courses, so there is no new XP this time.")

# "Next in your path" (US-405 AC3).
try:
    recommendations = catalog.next_in_path(orders.get_owned_course_ids(user.id))
except NotImplementedError:  # until the Storefront agent builds it
    recommendations = []
except Exception as error:
    logger.info("next_in_path failed: %s", type(error).__name__)
    recommendations = []
if recommendations:
    st.subheader("Next in your path", anchor=False)
    in_cart = cart.get_cart_course_ids()
    columns = st.columns(min(3, len(recommendations)))
    for index, course in enumerate(recommendations):
        with columns[index % len(columns)]:
            if course_card(course, in_cart=course["id"] in in_cart, key_prefix="next"):
                flash(cart.add_item(course["id"]).message)
                st.rerun()

with st.container(horizontal=True):
    st.page_link(routes.MY_ORDERS, label="View my orders", icon=":material/receipt_long:")
    st.page_link(routes.COURSES, label="Keep exploring", icon=":material/school:")
