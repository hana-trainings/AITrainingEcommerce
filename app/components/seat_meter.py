"""Seat meter: "8 of 30 seats left" with a bar (US-203, doc 02 S3/S4).

Numbers must come from the database. No fake scarcity (US-606).
The "few seats" rule itself lives in catalog.seat_status (a business rule);
this file only draws it. Polish story: D-03 (U1-19). Keep the function signatures.
"""

from typing import Literal, cast

import streamlit as st

from app.services.catalog import FEW_SEATS_ABSOLUTE, FEW_SEATS_SHARE, seat_status

SeatState = Literal["available", "few", "sold_out"]

# Kept here too so older imports keep working.
__all__ = ["FEW_SEATS_ABSOLUTE", "FEW_SEATS_SHARE", "SeatState", "seat_meter", "seat_state"]


def seat_state(seats_available: int, seats_total: int) -> SeatState:
    """Return "sold_out", "few" or "available" (pure function, easy to unit test)."""
    return cast(SeatState, seat_status(seats_available, seats_total))


def seat_label(seats_available: int, seats_total: int) -> str:
    """The text of the meter, e.g. "8 of 30 seats left" (US-203 AC1)."""
    left = max(int(seats_available), 0)
    seats_word = "seat" if seats_total == 1 else "seats"
    return f"{left} of {seats_total} {seats_word} left"


def seat_meter(seats_available: int, seats_total: int) -> None:
    """Show the seat bar plus a text label (never color alone, doc 02 section 8).

    The bar shows how FULL the course is, so it grows as seats are taken.
    "Few seats left" / "Sold out" appear as a badge with words AND an icon,
    so the state is never shown by color alone.
    """
    state = seat_state(seats_available, seats_total)
    taken_share = 0.0 if seats_total <= 0 else 1 - max(seats_available, 0) / seats_total
    st.progress(min(max(taken_share, 0.0), 1.0), text=seat_label(seats_available, seats_total))
    if state == "sold_out":
        st.badge("Sold out", icon=":material/block:", color="gray")
    elif state == "few":
        st.badge("Few seats left", icon=":material/event_seat:", color="orange")
