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


def seats_left_percent(seats_available: int, seats_total: int) -> int:
    """How much of the bar is filled: the share of seats still LEFT, 0-100 (pure)."""
    if seats_total <= 0:
        return 0
    return round(min(max(seats_available / seats_total, 0.0), 1.0) * 100)


def seat_meter(seats_available: int, seats_total: int) -> None:
    """Show the seat bar plus a text label (never color alone, doc 02 section 8).

    The bar shows the seats LEFT, like a fuel gauge: green when there is room,
    orange when few seats are left, grey when sold out (doc 02 section 4).
    "Few seats left" / "Sold out" also appear as a badge with words AND an icon.
    The HTML holds only numbers we computed and fixed words: no text from users.
    """
    state = seat_state(seats_available, seats_total)
    percent = seats_left_percent(seats_available, seats_total)
    label = seat_label(seats_available, seats_total)
    st.html(
        f'<p class="sf-seat-text">{label}</p>'
        f'<div class="sf-seat-track" role="img" aria-label="{label}">'
        f'<div class="sf-seat-fill sf-{state}" style="width: {percent}%"></div></div>'
    )
    if state == "sold_out":
        st.badge("Sold out", icon=":material/block:", color="gray")
    elif state == "few":
        st.badge("Few seats left", icon=":material/event_seat:", color="orange")
