"""Cart (doc 02 S6). Public: guests have a session cart.

Stories: US-302 view (U2-02), US-303 quantity (U2-10), US-304 remove (U2-11),
US-307 price check (U2-12), US-305 saved cart (U2-13), US-404 AC2 stock conflict (U2-07).
Prices and seats are re-read from the database on every load (cart.get_items).
"""

import streamlit as st

from app.components.states import empty_state, error_state, flash
from app.components.xp import xp_pill
from app.config import routes
from app.models.domain import CartLine
from app.services import auth, cart, orders
from app.utils.log import get_logger
from app.utils.text import escape_markdown, format_price

logger = get_logger(__name__)

st.title("Your cart")
st.caption("Demo store: no payment is taken.")

# A problem sent back from checkout, e.g. "Only 1 seat left for ..." (US-404 AC2).
checkout_problem = st.session_state.pop(orders.CHECKOUT_PROBLEM_KEY, None)
if checkout_problem:
    st.error(
        escape_markdown(checkout_problem),
        title="Please update your cart",
        icon=":material/warning:",
    )

try:
    lines = cart.get_items()
except Exception as error:
    logger.warning("cart page: could not load cart: %s", type(error).__name__)
    error_state()
    st.stop()

if not lines:
    empty_state(
        "Your cart is empty",
        "Find a course to start unlocking new skills.",
        action_label="Browse courses",
        action_page=routes.COURSES,
        icon=":material/school:",
    )
    st.stop()

for message in cart.price_changes(lines):
    st.info(escape_markdown(message), icon=":material/sell:")


def change_quantity(course_id: int, widget_key: str) -> None:
    """Callback for the quantity box: save the new quantity, show a toast."""
    result = cart.update_quantity(course_id, int(st.session_state[widget_key]))
    flash(result.message)
    # Drop the widget value so it is redrawn with the saved (maybe capped) quantity.
    st.session_state.pop(widget_key, None)


def remove(course_id: int) -> None:
    """Callback for the Remove button."""
    flash(cart.remove_item(course_id).message)


def draw_line(line: CartLine) -> None:
    """One cart row: image, title, price, quantity, line total, remove."""
    course_id = line["course_id"]
    with st.container(border=True):
        image_col, info_col, action_col = st.columns([1, 3, 2], vertical_alignment="center")
        with image_col:
            if line.get("image_url"):
                st.image(line["image_url"], alt=line["title"])
            else:
                st.markdown(":material/school:")
        with info_col:
            title = escape_markdown(line["title"])
            if line.get("slug"):
                st.page_link(
                    routes.COURSE_DETAIL,
                    label=f"**{title}**",
                    query_params={routes.COURSE_PARAM: line["slug"]},
                )
            else:
                st.markdown(f"**{title}**")
            st.markdown(
                f"{format_price(line['unit_price'])} per seat · "
                f"Line total **{format_price(line['line_total'])}**"
            )
            if line.get("already_owned"):
                st.caption("You already own this course, so it earns no new XP.")
            elif line.get("xp_reward"):
                xp_pill(int(line["xp_reward"]))
            if line.get("problem"):
                # Icon + words, not only color (accessibility).
                st.warning(escape_markdown(line["problem"]), icon=":material/error:")
        with action_col:
            widget_key = f"cart_qty_{course_id}"
            max_seats = max(1, min(cart.MAX_QUANTITY, int(line.get("seats_available") or 1)))
            st.number_input(
                "Seats",
                min_value=cart.MIN_QUANTITY,
                max_value=max(max_seats, int(line["quantity"])),
                value=int(line["quantity"]),
                step=1,
                key=widget_key,
                on_change=change_quantity,
                args=(course_id, widget_key),
                disabled=not line.get("slug"),
                help="1 to 5 seats, no more than the seats left.",
            )
            st.button(
                "Remove",
                key=f"cart_remove_{course_id}",
                icon=":material/delete:",
                on_click=remove,
                args=(course_id,),
                width="stretch",
            )


for line in lines:
    draw_line(line)

summary = cart.summarize(lines)
has_problems = any(not line.get("is_available") for line in lines)

with st.container(border=True):
    st.subheader("Summary")
    st.markdown(f"Seats: **{summary['item_count']}**")
    st.markdown(f"Subtotal: **{format_price(summary['subtotal'])}**")
    st.markdown(f"Total: **{format_price(summary['total'])}**")
    st.markdown(f"XP to earn: **+{summary['total_xp']} XP**")
    st.success(
        f"Placing this order unlocks: {summary['courses_unlocked']} course(s), "
        f"{summary['modules_unlocked']} module(s), +{summary['total_xp']} XP.",
        title="Unlock preview",
        icon=":material/lock_open:",
    )
    if has_problems:
        st.warning(
            "Some items need your attention. Fix or remove them before checkout.",
            icon=":material/warning:",
        )
    elif auth.current_user() is None:
        # Guests go to sign in first, then come back to checkout (US-401 AC1).
        st.page_link(
            routes.CHECKOUT, label="Sign in to check out", icon=":material/login:", width="stretch"
        )
    else:
        st.page_link(
            routes.CHECKOUT,
            label="Checkout",
            icon=":material/shopping_cart_checkout:",
            width="stretch",
        )
