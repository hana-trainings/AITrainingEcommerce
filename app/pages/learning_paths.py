"""Learning paths with skill maps (doc 02 S5). Public.

Story US-604 (U1-14): each path shows its courses in order as nodes (owned /
in cart / locked), "X of Y unlocked", the completion bonus XP and the badge,
and clicking a node opens the course detail.
Guests see "In cart" for courses in their session cart; "Unlocked" (owned)
needs a sign-in. The badge preview uses the real badge name and only shows when
the path has a badge.
"""

import streamlit as st

from app.components.course_card import shopper_course_ids
from app.components.path_map import path_node_map, path_nodes_for
from app.components.states import empty_state, load_or_stop
from app.config import routes
from app.models.domain import LearningPath
from app.services import auth, catalog
from app.utils.text import escape_markdown, format_price

user = auth.current_user()

st.title("Learning paths")
st.caption("Follow a path step by step. Unlock every course in it to earn the bonus XP and badge.")

paths = load_or_stop(catalog.list_paths, "learning paths page")
owned_ids, cart_ids = shopper_course_ids(user)

if user is None:
    st.info(
        "Sign in to see which steps you have already unlocked.",
        icon=":material/login:",
    )


def path_facts(path: LearningPath) -> None:
    """Course count, total price, bonus XP and the badge preview (doc 02 S5)."""
    courses = path.get("courses", [])
    total_price = sum(float(course.get("price") or 0) for course in courses)
    with st.container(horizontal=True, gap="small"):
        st.badge(
            f"{len(courses)} {'course' if len(courses) == 1 else 'courses'}",
            icon=":material/school:",
            color="gray",
        )
        st.badge(f"Total {format_price(total_price)}", icon=":material/sell:", color="gray")
        st.badge(
            f"+{int(path.get('bonus_xp') or 0)} XP bonus", icon=":material/bolt:", color="yellow"
        )
        badge_name = load_or_stop(lambda: catalog.path_badge_name(path), "learning paths page")
        if badge_name:  # only paths with a real badge show one (badge_code is optional)
            st.badge(
                f"Badge: {escape_markdown(badge_name)}",
                icon=":material/workspace_premium:",
                color="violet",
            )


if not paths:
    empty_state(
        "No learning paths yet",
        "Paths are on their way. Meanwhile, explore all courses.",
        action_label="Browse courses",
        action_page=routes.COURSES,
        icon=":material/school:",
    )
    st.stop()

for path in paths:
    st.header(escape_markdown(path.get("name", "")))
    if path.get("description"):
        st.markdown(escape_markdown(path["description"]))
    path_facts(path)
    path_node_map(
        path["name"],
        path_nodes_for(path, owned_ids, cart_ids),
        bonus_xp=int(path.get("bonus_xp") or 0),
    )
