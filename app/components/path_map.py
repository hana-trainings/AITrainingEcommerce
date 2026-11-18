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


def path_node_map(path_name: str, nodes: list[PathNode], *, bonus_xp: int = 0) -> None:
    """Show a path's courses in order with their state and "X of Y unlocked"."""
    with st.container(border=True):
        st.markdown(f"**{escape_markdown(path_name)}**")
        st.caption(path_summary(nodes, bonus_xp))
        if not nodes:
            st.caption("No courses in this path yet.")
            return
        # A horizontal container wraps onto new lines on narrow screens (phones).
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            for position, node in enumerate(nodes, start=1):
                if position > 1:
                    st.markdown(":material/arrow_forward:", width="content")
                _node(position, node)


def _node(position: int, node: PathNode) -> None:
    icon, state_label, color = _NODE_STYLE.get(node["state"], _NODE_STYLE["locked"])
    with st.container(border=True, width=220, gap="small"):
        # Labels understand some Markdown, so escape the title (it comes from the DB).
        st.page_link(
            routes.COURSE_DETAIL,
            label=f"Step {position}: {escape_markdown(node['title'])}",
            icon=icon,
            query_params={routes.COURSE_PARAM: node["slug"]},
            help=f"{state_label}. Open the course page.",
        )
        st.badge(state_label, icon=icon, color=color)
