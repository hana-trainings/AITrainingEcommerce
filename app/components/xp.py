"""XP pill, XP bar and level chip (US-601, US-602, doc 02 section 4).

These only DISPLAY numbers they are given; XP is awarded by the database.
Polish story: D-04 (U1-20). Keep the function signatures.
"""

import streamlit as st


def xp_pill(points: int) -> None:
    """Amber "+100 XP" tag (dark text on amber for contrast)."""
    st.badge(f"+{points} XP", icon=":material/bolt:", color="yellow")


def level_chip(level: int, name: str) -> None:
    """Small chip such as "Level 2 · Explorer"."""
    st.badge(f"Level {level} · {name}", icon=":material/military_tech:", color="violet")


def xp_bar(xp_total: int, level_start_xp: int, next_level_xp: int | None) -> None:
    """Progress from the current level to the next, e.g. "120 / 150 XP".

    next_level_xp=None means the top level is reached.
    """
    if next_level_xp is None:
        st.progress(1.0, text=f"{xp_total} XP · top level reached")
        return
    span = max(next_level_xp - level_start_xp, 1)
    progress = (xp_total - level_start_xp) / span
    st.progress(min(max(progress, 0.0), 1.0), text=f"{xp_total} / {next_level_xp} XP")
