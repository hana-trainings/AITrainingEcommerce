"""Course card (doc 02 S3) and level tag.

Shows image, category, title, level, duration, price, "+XP" pill, seat meter and
an "Add to cart" button. Owned courses show "Unlocked" instead of the button;
sold-out courses show a disabled button.
Polish story: D-03 (U1-19). Keep the function signatures.
"""

import streamlit as st

from app.components.seat_meter import seat_meter, seat_state
from app.components.xp import xp_pill
from app.config import routes
from app.models.domain import Course
from app.utils.text import escape_markdown, format_price

_LEVEL_COLORS = {"Beginner": "green", "Intermediate": "blue", "Advanced": "violet"}


def level_tag(level: str) -> None:
    """Colored level tag: Beginner (emerald), Intermediate (indigo), Advanced (purple)."""
    st.badge(level, icon=":material/signal_cellular_alt:", color=_LEVEL_COLORS.get(level, "gray"))


def course_card(
    course: Course,
    *,
    owned: bool = False,
    in_cart: bool = False,
    key_prefix: str = "card",
) -> bool:
    """Draw one course card. Returns True on the run where "Add to cart" was clicked.

    The caller decides what clicking does, e.g.:
        if course_card(course):
            result = cart.add_item(course["id"])
    key_prefix keeps button keys unique when the same course appears twice on a page.
    """
    title = escape_markdown(course.get("title", "Untitled course"))
    seats_available = int(course.get("seats_available", 0))
    seats_total = int(course.get("seats_total", 0))

    with st.container(border=True):
        if course.get("image_url"):
            st.image(course["image_url"], alt=course.get("title", "Course image"))
        st.caption(escape_markdown(course.get("category_name", "")))
        st.page_link(
            routes.COURSE_DETAIL,
            label=f"**{title}**",
            query_params={routes.COURSE_PARAM: course.get("slug", "")},
        )
        with st.container(horizontal=True):
            level_tag(course.get("level", ""))
            st.badge(
                f"{course.get('duration_hours', 0):g} h", icon=":material/schedule:", color="gray"
            )
            xp_pill(int(course.get("xp_reward", 0)))
        st.markdown(f"**{format_price(course.get('price'))}**")
        seat_meter(seats_available, seats_total)
        return _card_action(
            course, owned, in_cart, seat_state(seats_available, seats_total), key_prefix
        )


def _card_action(course: Course, owned: bool, in_cart: bool, state: str, key_prefix: str) -> bool:
    """The bottom of the card: Unlocked ribbon, In cart link, or Add to cart button."""
    if owned:
        st.badge("Unlocked", icon=":material/lock_open:", color="green")
        return False
    if in_cart:
        st.page_link(routes.CART, label="In cart · View cart", icon=":material/shopping_cart:")
        return False
    return st.button(
        "Sold out" if state == "sold_out" else "Add to cart",
        key=f"{key_prefix}_add_{course.get('id', '')}",
        icon=":material/add_shopping_cart:",
        type="primary",
        disabled=state == "sold_out",
        width="stretch",
    )
