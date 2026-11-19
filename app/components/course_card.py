"""Course card (doc 02 S3) and level tag, plus the shared "Add to cart" behavior.

Shows image, category, title, level, duration, price, "+XP" pill, seat meter and
an "Add to cart" button. Owned courses show "Unlocked" instead of the button;
sold-out courses show a disabled button.
Polish story: D-03 (U1-19). Keep the function signatures.
"""

import streamlit as st

from app.components.seat_meter import seat_meter, seat_state
from app.components.states import flash
from app.components.xp import xp_pill
from app.config import routes
from app.models.domain import Course, CurrentUser
from app.services import cart, orders
from app.utils.log import get_logger
from app.utils.text import escape_markdown, format_price

logger = get_logger(__name__)

# Level colors from doc 02 section 3.2 (the named colors are set in .streamlit/config.toml).
_LEVEL_COLORS = {"Beginner": "green", "Intermediate": "blue", "Advanced": "violet"}

# Neutral gradient used when a course has no image (doc 02 section 3.4:
# abstract, 16:9, no people or logos). Colors are the design tokens.
# This is STATIC text: no course data is ever put inside the SVG.
_GRADIENTS = {
    "Beginner": ("#10B981", "#4F46E5"),
    "Intermediate": ("#4F46E5", "#0EA5E9"),
    "Advanced": ("#7C3AED", "#4F46E5"),
}
_PLACEHOLDER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 90">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="{start}"/><stop offset="1" stop-color="{end}"/>'
    "</linearGradient></defs>"
    '<rect width="160" height="90" fill="url(#g)"/>'
    '<circle cx="128" cy="22" r="30" fill="#FFFFFF" fill-opacity="0.12"/>'
    '<circle cx="24" cy="78" r="22" fill="#FFFFFF" fill-opacity="0.10"/>'
    '<path d="M20 60 L60 40 L100 52 L140 30" stroke="#FFFFFF" stroke-opacity="0.35" '
    'stroke-width="3" fill="none" stroke-linecap="round"/>'
    "</svg>"
)


# One icon per category (doc 02 section 3.4). Unknown categories get a book.
_CATEGORY_ICONS = {
    "Artificial Intelligence": ":material/auto_awesome:",
    "Machine Learning": ":material/hub:",
    "Data Analytics": ":material/bar_chart:",
    "Data Engineering": ":material/database:",
}


def category_icon(category_name: str) -> str:
    """Material icon for a category name, e.g. "Data Analytics" -> bar chart."""
    return _CATEGORY_ICONS.get(category_name, ":material/menu_book:")


def placeholder_image(level: str) -> str:
    """Return a small static SVG gradient for a course without an image."""
    start, end = _GRADIENTS.get(level, ("#94A3B8", "#475569"))
    return _PLACEHOLDER_SVG.format(start=start, end=end)


def course_image(course: Course) -> None:
    """The course image (16:9), or the neutral gradient when image_url is empty."""
    title = str(course.get("title") or "Course")
    if course.get("image_url"):
        st.image(course["image_url"], alt=f"Illustration for {title}", width="stretch")
    else:
        st.image(
            placeholder_image(str(course.get("level", ""))),
            alt=f"Abstract placeholder image for {title}",
            width="stretch",
        )


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
            add_course_to_cart(course)
    key_prefix keeps button keys unique when the same course appears twice on a page.
    """
    title = escape_markdown(course.get("title", "Untitled course"))
    seats_available = int(course.get("seats_available") or 0)
    seats_total = int(course.get("seats_total") or 0)

    # height="stretch" makes cards in the same grid row equally tall.
    # The key gives a CSS class (st-key-card-<level>-...) for the level's color stripe.
    level = str(course.get("level", "")).lower() or "other"
    card_key = f"card-{level}-{key_prefix}-{course.get('id', '')}"
    with st.container(key=card_key, height="stretch"):
        course_image(course)
        category = str(course.get("category_name", ""))
        st.caption(f"{category_icon(category)} {escape_markdown(category)}")
        st.page_link(
            routes.COURSE_DETAIL,
            label=f"**{title}**",
            query_params={routes.COURSE_PARAM: course.get("slug", "")},
        )
        with st.container(horizontal=True, gap="small"):
            level_tag(course.get("level", ""))
            st.badge(
                f"{float(course.get('duration_hours') or 0):g} h",
                icon=":material/schedule:",
                color="gray",
            )
            xp_pill(int(course.get("xp_reward") or 0))
        st.markdown(f"#### {format_price(course.get('price'))}")
        seat_meter(seats_available, seats_total)
        st.space("stretch")  # keeps the buttons of a row lined up at the bottom
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
        icon=":material/block:" if state == "sold_out" else ":material/add_shopping_cart:",
        type="primary",
        disabled=state == "sold_out",  # US-101 AC3, US-301 AC4
        width="stretch",
    )


# ---------------------------------------------------------------- shared behavior
def shopper_course_ids(user: CurrentUser | None) -> tuple[set[int], set[int]]:
    """Return (owned course ids, in-cart course ids) for the "Unlocked" / "In cart" states.

    Guests own nothing, but they DO have a cart (kept in the session, US-305),
    so the in-cart ids are read for everyone; cart.get_cart_course_ids()
    handles guests and signed-in users alike. Showing "In cart" also stops a
    second click from silently adding another seat.
    These come from other areas (orders, cart). If one is not ready or fails,
    we show the normal card instead of breaking the whole page.
    """
    owned: set[int] = set()
    in_cart: set[int] = set()
    if user is not None:
        try:
            owned = set(orders.get_owned_course_ids(user.id))
        except Exception:  # a missing widget state must not break the page
            logger.warning("owned courses unavailable on storefront page", exc_info=True)
    try:
        in_cart = {int(course_id) for course_id in cart.get_cart_course_ids()}
    except Exception:
        logger.warning("cart lines unavailable on storefront page", exc_info=True)
    return owned, in_cart


def add_course_to_cart(course: Course) -> None:
    """Add one seat of a course to the cart and show the result (US-204, US-301).

    On success the page reruns so the header cart count updates at once
    (US-301 AC3); the toast is queued with flash() so it survives the rerun.
    """
    try:
        result = cart.add_item(int(course["id"]))
    except NotImplementedError:
        st.info("The cart is coming soon.", icon=":material/construction:")
        return
    except Exception:  # never show a stack trace, NFR-SEC-17
        logger.exception("add to cart failed for course %s", course.get("id"))
        st.error("Something went wrong, please try again.", icon=":material/error:")
        return
    if result.ok:
        flash(result.message or f"Added {course.get('title', 'the course')} to your cart.")
        st.rerun()
    st.warning(result.message or "This course could not be added.", icon=":material/warning:")
