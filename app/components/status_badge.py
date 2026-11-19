"""Status badge for orders and courses (admin tables, My Orders).

Each status has a color AND a text label. Keep the function signature.
"""

import streamlit as st

# status -> (label, Material icon, st.badge color)
_STATUS_STYLES: dict[str, tuple[str, str, str]] = {
    "confirmed": ("Confirmed", ":material/check_circle:", "green"),
    "cancelled": ("Cancelled", ":material/cancel:", "gray"),
    "published": ("Published", ":material/visibility:", "green"),
    "draft": ("Draft", ":material/edit_note:", "gray"),
    "featured": ("Featured", ":material/star:", "blue"),
    "sold_out": ("Sold out", ":material/block:", "red"),
}


def status_badge(status: str) -> None:
    """Show a colored status label. Unknown statuses show as a grey label."""
    label, icon, color = _STATUS_STYLES.get(status, (status.title(), ":material/info:", "gray"))
    st.badge(label, icon=icon, color=color)
