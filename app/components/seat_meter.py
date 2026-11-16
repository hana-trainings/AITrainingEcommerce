"""Seat meter: "8 of 30 seats left" with a bar (US-203, doc 02 S3/S4).

Numbers must come from the database. No fake scarcity (US-606).
Polish story: D-03 (U1-19). Keep the function signatures.
"""

from typing import Literal

import streamlit as st

SeatState = Literal["available", "few", "sold_out"]

FEW_SEATS_ABSOLUTE = 5  # 5 or fewer seats is "few" ...
FEW_SEATS_SHARE = 0.10  # ... and so is 10% or less of the total (US-203 AC2)


def seat_state(seats_available: int, seats_total: int) -> SeatState:
    """Return "sold_out", "few" or "available" (pure function, easy to unit test)."""
    if seats_available <= 0:
        return "sold_out"
    if seats_available <= FEW_SEATS_ABSOLUTE:
        return "few"
    if seats_total > 0 and seats_available / seats_total <= FEW_SEATS_SHARE:
        return "few"
    return "available"


def seat_meter(seats_available: int, seats_total: int) -> None:
    """Show the seat bar plus a text label (never color alone, doc 02 section 8)."""
    state = seat_state(seats_available, seats_total)
    filled = 0.0 if seats_total <= 0 else 1 - max(seats_available, 0) / seats_total
    st.progress(
        min(max(filled, 0.0), 1.0), text=f"{max(seats_available, 0)} of {seats_total} seats left"
    )
    if state == "sold_out":
        st.badge("Sold out", icon=":material/block:", color="gray")
    elif state == "few":
        st.badge("Few seats left", icon=":material/event_seat:", color="orange")
