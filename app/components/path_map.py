"""Learning path node map ("skill tree"), kept as a simple chain (doc 02 section 10).

Node states: owned (check), in cart (cart icon), locked (lock). Each state has an
icon AND a label. Clicking a node opens the course detail (US-604 AC3).
Polish story: D-04 (U1-20). Keep the function signature.
"""

import streamlit as st

from app.config import routes
from app.models.domain import PathNode
from app.utils.text import escape_markdown

_NODE_STYLE = {
    "owned": (":material/check_circle:", "Unlocked"),
    "in_cart": (":material/shopping_cart:", "In cart"),
    "locked": (":material/lock:", "Locked"),
}


def path_node_map(path_name: str, nodes: list[PathNode], *, bonus_xp: int = 0) -> None:
    """Show a path's courses in order with their state and "X of Y unlocked"."""
    owned = sum(1 for node in nodes if node["state"] == "owned")
    summary = f"{owned} of {len(nodes)} unlocked"
    if bonus_xp:
        summary += f" · +{bonus_xp} XP bonus"
    with st.container(border=True):
        st.markdown(f"**{escape_markdown(path_name)}**")
        st.caption(summary)
        if not nodes:
            st.caption("No courses in this path yet.")
            return
        columns = st.columns(len(nodes))
        for position, (column, node) in enumerate(zip(columns, nodes, strict=True), start=1):
            icon, state_label = _NODE_STYLE.get(node["state"], _NODE_STYLE["locked"])
            with column:
                # Labels understand some Markdown, so escape the title (it comes from the DB).
                st.page_link(
                    routes.COURSE_DETAIL,
                    label=f"Step {position}: {escape_markdown(node['title'])}",
                    icon=icon,
                    query_params={routes.COURSE_PARAM: node["slug"]},
                    help=state_label,
                )
                st.caption(state_label)
