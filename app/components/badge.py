"""Badge medallion for the badge shelf (US-603, doc 02 section 4).

Locked badges show a grey silhouette AND the word "Locked" plus a hint
(never color alone). Polish story: D-04 (U1-20). Keep the function signature.
"""

import streamlit as st

from app.utils.text import escape_markdown


def badge_medallion(
    name: str,
    description: str,
    *,
    earned: bool,
    hint: str = "",
    icon: str = ":material/workspace_premium:",
) -> None:
    """One badge in a bordered box: earned (color) or locked (grey + hint)."""
    with st.container(border=True):
        if earned:
            st.badge(name, icon=icon, color="green")
            st.caption(escape_markdown(description))
        else:
            st.badge(f"{name} · Locked", icon=":material/lock:", color="gray")
            st.caption(escape_markdown(hint or description))
