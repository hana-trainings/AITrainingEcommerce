"""Helpers for showing text that came from users or the database.

Streamlit does not render raw HTML unless unsafe_allow_html=True (we never use
that with user data, NFR-SEC-15). Markdown is still interpreted, so a course
title like "[click me](http://...)" would turn into a link. escape_markdown()
makes such text show exactly as typed.
"""

_MARKDOWN_SPECIAL = "\\`*_{}[]<>()#+-.!|~$"


def escape_markdown(text: object) -> str:
    """Return text with Markdown characters escaped so it displays literally."""
    value = "" if text is None else str(text)
    return "".join("\\" + char if char in _MARKDOWN_SPECIAL else char for char in value)


def format_price(amount: float | int | str | None) -> str:
    """Format a price in demo US dollars, e.g. 49 -> "$49.00"."""
    try:
        return f"${float(amount or 0):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"
