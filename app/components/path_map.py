"""Learning path node map ("skill tree"), kept as a simple chain (doc 02 section 10).

Node states: owned (check), in cart (cart icon), locked (lock). Each state has an
icon AND a label, never color alone. Clicking a node opens the course detail
(US-604 AC3). Polish story: D-04 (U1-20). Keep the function signature.
"""

import streamlit as st

from app.config import routes
from app.models.domain import LearningPath, PathNode
from app.services import gamification
from app.utils.log import get_logger
from app.utils.text import escape_markdown

logger = get_logger(__name__)

# state -> (Material icon, label, st.badge color)
_NODE_STYLE = {
    "owned": (":material/check_circle:", "Unlocked", "green"),
    "in_cart": (":material/shopping_cart:", "In cart", "blue"),
    "locked": (":material/lock:", "Locked", "gray"),
}


MAX_STEPS_PER_ROW = 5  # longer paths continue on the next row


def path_summary(nodes: list[PathNode], bonus_xp: int = 0) -> str:
    """ "2 of 4 unlocked · +250 XP bonus" (US-604 AC2). Pure function, easy to test."""
    owned = sum(1 for node in nodes if node["state"] == "owned")
    summary = f"{owned} of {len(nodes)} unlocked"
    if bonus_xp:
        summary += f" · +{bonus_xp} XP bonus"
    return summary


def path_nodes_for(
    path: LearningPath, owned_course_ids: set[int], cart_course_ids: set[int]
) -> list[PathNode]:
    """Ask the gamification service for the node states of one path.

    If that service is not ready or fails, show every course as "locked" so the
    map still works for browsing (it is only display, nothing is unlocked by it).
    """
    try:
        return gamification.build_path_nodes(path, owned_course_ids, cart_course_ids)
    except Exception:  # the map must never break the page
        logger.warning("build_path_nodes unavailable, showing locked nodes", exc_info=True)
        return [
            {
                "course_id": course["id"],
                "slug": course.get("slug", ""),
                "title": course.get("title", ""),
                "state": "locked",
            }
            for course in path.get("courses", [])
        ]


def path_node_map(
    path_name: str, nodes: list[PathNode], *, bonus_xp: int = 0, show_title: bool = True
) -> None:
    """Show a path's courses in order with their state and "X of Y unlocked".

    show_title=False when the page already shows the path name as a heading
    (Learning paths page), so the name is not printed twice.
    Steps are colored by state (style.py): green unlocked, indigo in cart, grey locked,
    and each one ALSO has an icon and a word, so color is never the only signal.
    """
    map_key = _key_part(path_name)
    with st.container(key=f"pathmap-{map_key}"):
        if show_title:
            st.markdown(f"**:material/route: {escape_markdown(path_name)}**")
        st.caption(path_summary(nodes, bonus_xp))
        if not nodes:
            st.caption("No courses in this path yet.")
            return
        # One row of equal steps on desktop; the grid wraps onto more rows on phones.
        grid = st.grid(min(len(nodes), MAX_STEPS_PER_ROW), min_column_width=150, gap="small")
        for position, node in enumerate(nodes, start=1):
            with grid:
                _node(position, len(nodes), node, map_key)


def _key_part(text: str) -> str:
    """Letters, digits and "-" only, so the text can be part of a widget key."""
    return "".join(char if char.isalnum() else "-" for char in text.lower())[:40] or "path"


def _node(position: int, total: int, node: PathNode, map_key: str) -> None:
    state = node["state"] if node["state"] in _NODE_STYLE else "locked"
    icon, state_label, color = _NODE_STYLE[state]
    # The key gives the container a CSS class (st-key-node-<state>-...) for its color.
    with st.container(key=f"node-{state}-{map_key}-{position}", height="stretch", gap="small"):
        st.caption(f"Step {position} of {total}")
        # Titles come from the database: escape them, and let them wrap (never cut off).
        st.markdown(f"**{escape_markdown(node['title'])}**")
        st.badge(state_label, icon=icon, color=color)
        st.page_link(
            routes.COURSE_DETAIL,
            label="View course",
            icon=":material/arrow_forward:",
            query_params={routes.COURSE_PARAM: node["slug"]},
            help=f"{state_label}. Open the course page.",
        )
