"""Home (doc 02 S1). Public.

Stories: US-106 featured courses, learning paths and the "Almost full" strip
(U1-13). Signed-in users see a welcome card and "Next in your path" instead of
the hero (doc 02 S1 signed-in variant).

Honesty rule (US-606): the "Almost full" strip only shows courses that really
have few seats left in the database. If none do, the strip is not shown.
"""

import streamlit as st

from app.components.course_card import add_course_to_cart, course_card, shopper_course_ids
from app.components.path_map import path_node_map, path_nodes_for
from app.components.states import load_or_stop
from app.components.xp import level_chip, xp_progress_text
from app.config import routes
from app.models.domain import Course, CurrentUser
from app.services import auth, catalog, gamification
from app.utils.log import get_logger
from app.utils.text import escape_markdown

logger = get_logger(__name__)

user = auth.current_user()
owned_ids, cart_ids = shopper_course_ids(user)


def show_cards(courses: list[Course], key_prefix: str) -> None:
    grid = st.grid(4, min_column_width=240, gap="medium")
    for course in courses:
        with grid:
            clicked = course_card(
                course,
                owned=course["id"] in owned_ids,
                in_cart=course["id"] in cart_ids,
                key_prefix=key_prefix,
            )
        if clicked:
            add_course_to_cart(course)


def hero() -> None:
    """Guest hero with the two main calls to action."""
    with st.container(border=True):
        st.title("Unlock your AI & Data skills")
        st.markdown(
            "Pick a learning path, unlock hands-on courses, and earn XP and badges "
            "as you grow. Made for curious learners."
        )
        with st.container(horizontal=True):
            st.page_link(routes.COURSES, label="Explore courses", icon=":material/school:")
            st.page_link(routes.LEARNING_PATHS, label="Find your path", icon=":material/route:")


def welcome_card(signed_in: CurrentUser) -> None:
    """Signed-in variant: "Welcome back, name · Level 2 Explorer · 120 XP to Practitioner"."""
    with st.container(border=True):
        st.title(f"Welcome back, {escape_markdown(signed_in.display_name)}")
        try:
            progress = gamification.get_level_progress(signed_in.xp_total)
        except Exception:  # level display is a bonus; the page works without it
            logger.warning("level progress unavailable on home", exc_info=True)
            progress = None
        if progress is not None:
            with st.container(horizontal=True, vertical_alignment="center"):
                level_chip(progress["level"], progress["name"])
                st.caption(
                    xp_progress_text(
                        progress["xp_total"],
                        progress["next_level_xp"],
                        progress.get("next_level_name") or "",
                    )
                )
        next_courses = load_or_stop(lambda: catalog.next_in_path(owned_ids), "home page")
        if next_courses:
            st.markdown("**Next in your path**")
            for course in next_courses:
                st.page_link(
                    routes.COURSE_DETAIL,
                    label=escape_markdown(course["title"]),
                    icon=":material/arrow_forward:",
                    query_params={routes.COURSE_PARAM: course["slug"]},
                )
        else:
            st.page_link(
                routes.LEARNING_PATHS,
                label="Pick a path to get started",
                icon=":material/route:",
            )


# ---------------------------------------------------------------- top of the page
if user is None:
    hero()
else:
    welcome_card(user)

# ---------------------------------------------------------------- how it works
with st.container(horizontal=True, gap="medium"):
    for icon, title, text in (
        (":material/route:", "1. Pick a path", "Choose a learning path that fits your goal."),
        (":material/lock_open:", "2. Unlock courses", "Add courses to your cart and unlock them."),
        (
            ":material/bolt:",
            "3. Earn XP & badges",
            "Every course you unlock adds XP to your level.",
        ),
    ):
        with st.container(border=True, width=300):
            st.markdown(f"{icon} **{title}**")
            st.caption(text)

# ---------------------------------------------------------------- learning paths
st.header("Learning paths")
paths = load_or_stop(catalog.list_paths, "home page")
for path in paths:
    # One full-width row per path, so its chain of steps has room to read left to right.
    path_node_map(
        path["name"],
        path_nodes_for(path, owned_ids, cart_ids),
        bonus_xp=int(path.get("bonus_xp") or 0),
    )
st.page_link(routes.LEARNING_PATHS, label="See all paths", icon=":material/route:")

# ---------------------------------------------------------------- featured
st.header("Featured courses")
featured = load_or_stop(lambda: catalog.featured_courses(limit=4), "home page")
if featured:
    show_cards(featured, key_prefix="featured")
else:
    st.caption("New featured courses are on their way.")

# ---------------------------------------------------------------- almost full (real data only)
almost_full = load_or_stop(lambda: catalog.almost_full_courses(limit=4), "home page")
if almost_full:
    st.header("Almost full")
    st.caption("These courses have only a few seats left, based on live seat counts.")
    show_cards(almost_full, key_prefix="almost_full")

st.divider()
st.caption(
    ":material/info: SkillForge Academy is a demo store for training. "
    "No real payments are taken and no real emails are sent."
)
