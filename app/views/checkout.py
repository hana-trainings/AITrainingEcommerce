"""Checkout (doc 02 S7). Signed-in users only; guests are asked to sign in (US-401).

Stories: US-401 sign-in first (U2-04), US-402 review and place order (U2-03),
US-404 stock conflict (U2-07), US-406 confirmation email (U2-06).
The total shown here is re-read from the database; the place_order database
function recalculates everything again and is the source of truth (NFR-SEC-09).
"""

import streamlit as st

from app.components.guards import guard_customer_page
from app.components.states import empty_state, error_state, flash
from app.config import routes
from app.services import cart, email_outbox, orders
from app.utils.log import get_logger
from app.utils.text import escape_markdown, format_price

logger = get_logger(__name__)

# Guests see "Please sign in" and come back here afterwards (US-401 AC1).
user = guard_customer_page(return_to=routes.CHECKOUT)  # stops the page for guests

PLACING_KEY = "checkout_placing"  # set by the click; read and cleared on the very next run
# After a successful order: data for the confirmation page's celebration (US-605).
CELEBRATION_KEY = orders.CELEBRATION_KEY
ERROR_KEY = "checkout_error"  # a general error from the last attempt, shown once

st.title("Checkout")
st.info("Demo store: no payment is taken.", icon=":material/info:")

try:
    lines = cart.get_items()
except Exception as error:
    logger.warning("checkout: could not load cart: %s", type(error).__name__)
    error_state()
    st.stop()

if not lines:
    empty_state(
        "Your cart is empty",
        "Add a course before checking out.",
        action_label="Browse courses",
        action_page=routes.COURSES,
        icon=":material/school:",
    )
    st.stop()

# Unavailable lines are excluded from checkout until removed (US-307 AC2).
problem_lines = [line for line in lines if not line.get("is_available")]
if problem_lines:
    st.warning(
        "Some items in your cart need your attention before you can check out.",
        icon=":material/warning:",
    )
    for line in problem_lines:
        st.markdown(f"- **{escape_markdown(line['title'])}**: {escape_markdown(line['problem'])}")
    st.page_link(routes.CART, label="Go to cart", icon=":material/shopping_cart:")
    st.stop()

summary = cart.summarize(lines)
# One idempotency key per checkout attempt, made when the page opens (NFR-DATA-04).
orders.checkout_key()

st.subheader("Order review")
st.dataframe(
    [
        {
            "Course": line["title"],
            "Seats": line["quantity"],
            "Price": format_price(line["unit_price"]),
            "Line total": format_price(line["line_total"]),
            "XP": line["xp_reward"],
        }
        for line in lines
    ],
    hide_index=True,
    alt="Courses in this order",
)
with st.container(horizontal=True):
    st.metric("Total", format_price(summary["total"]))
    st.metric("XP to earn", f"+{summary['total_xp']}")
    st.metric("Seats", summary["item_count"])
st.success(
    f"Placing this order unlocks: {summary['courses_unlocked']} course(s), "
    f"{summary['modules_unlocked']} module(s), +{summary['total_xp']} XP.",
    title="Unlock preview",
    icon=":material/lock_open:",
)
st.markdown(f"The confirmation email goes to **{escape_markdown(user.email)}**.")
st.page_link(routes.CART, label="Change my cart", icon=":material/edit:")

understood = st.checkbox("I understand this is a demo order", key="checkout_understood")


def start_placing() -> None:
    """Runs on click BEFORE the page reruns, so the button is drawn disabled (US-402 AC4)."""
    st.session_state[PLACING_KEY] = True


last_error = st.session_state.pop(ERROR_KEY, None)
if last_error:
    st.error(escape_markdown(last_error), icon=":material/error:")

# Read AND clear the click flag now, before the slow call: if the user leaves the page
# mid-call, a later visit must not place an order without a new click.
clicked = bool(st.session_state.pop(PLACING_KEY, False))
placing = clicked and understood  # only with the demo box ticked (US-402 AC3)
st.button(
    "Placing order..." if placing else "Place order",
    type="primary",
    icon=":material/task_alt:",
    disabled=placing or not understood,
    on_click=start_placing,
    key="checkout_place_order",
)

if placing:
    with st.spinner("Placing your order..."):
        # The same key is reused on a rerun or double click (NFR-DATA-04).
        outcome = orders.place_order(orders.checkout_key())

    if outcome.ok and outcome.order:
        order_id = outcome.order["order_id"]
        orders.finish_checkout_attempt()
        email_result = email_outbox.save_confirmation_email(order_id)  # never raises
        st.session_state[CELEBRATION_KEY] = {
            "order_id": order_id,
            "level_up": bool(outcome.order.get("level_up")),
            "new_level": outcome.order.get("new_level"),
            "email_saved": email_result.ok,
            "show": not outcome.order.get("already_existed"),
        }
        st.session_state.pop("checkout_understood", None)
        flash("Order placed!")
        st.switch_page(routes.ORDER_CONFIRMATION, query_params={routes.ORDER_PARAM: str(order_id)})
    elif outcome.error_code in ("NOT_ENOUGH_SEATS", "COURSE_UNAVAILABLE", "CART_EMPTY"):
        # Back to the cart, where the problem lines are highlighted (US-404 AC2).
        st.session_state[orders.CHECKOUT_PROBLEM_KEY] = outcome.message
        st.switch_page(routes.CART)
    else:
        # Rerun so the button is enabled again; the message is shown above it.
        st.session_state[ERROR_KEY] = outcome.message
        st.rerun()
