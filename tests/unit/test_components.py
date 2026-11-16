"""Pure helper functions behind the shared UI components."""

import pytest

from app.components.seat_meter import seat_state
from app.utils.text import escape_markdown, format_price


@pytest.mark.parametrize(
    ("available", "total", "expected"),
    [
        (0, 30, "sold_out"),
        (5, 100, "few"),  # 5 or fewer seats (US-203 AC2)
        (9, 100, "few"),  # 10% or less of the total
        (22, 30, "available"),
    ],
)
def test_seat_state(available, total, expected):
    assert seat_state(available, total) == expected


def test_escape_markdown_shows_text_literally():
    assert escape_markdown("[click](http://x)") == "\\[click\\]\\(http://x\\)"
    assert escape_markdown(None) == ""


def test_format_price():
    assert format_price(49) == "$49.00"
    assert format_price(None) == "$0.00"
