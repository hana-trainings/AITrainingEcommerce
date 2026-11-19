"""Unit tests for the Storefront components' pure helpers (U1-17 to U1-20)."""

import pytest

from app.components import course_card, path_map
from app.components.header import cart_label
from app.components.seat_meter import seat_label, seat_state
from app.components.xp import xp_progress_text
from app.models.domain import CurrentUser
from tests.conftest import CUSTOMER_ID

CUSTOMER = CurrentUser(id=CUSTOMER_ID, email="c@example.test", display_name="Casey")


# ---------------------------------------------------------------- seat meter (US-203, D-03)
def test_seat_label_words():
    assert seat_label(8, 30) == "8 of 30 seats left"
    assert seat_label(-2, 30) == "0 of 30 seats left"  # never a negative number
    assert seat_label(1, 1) == "1 of 1 seat left"


def test_seat_state_matches_the_catalog_rule():
    assert seat_state(3, 30) == "few"
    assert seat_state(0, 30) == "sold_out"


# ---------------------------------------------------------------- XP (US-602, D-04)
def test_xp_progress_text():
    assert xp_progress_text(120, 150, "Explorer") == "120 / 150 XP · 30 XP to Explorer"
    assert xp_progress_text(120, 150) == "120 / 150 XP"
    assert xp_progress_text(1600, None) == "1600 XP · top level reached"


def test_cart_label():
    assert cart_label(0) == "Cart (0)"
    assert cart_label(3) == "Cart (3)"


# ---------------------------------------------------------------- path map (US-604, D-04)
def test_path_summary():
    nodes = [
        {"course_id": 1, "slug": "a", "title": "A", "state": "owned"},
        {"course_id": 2, "slug": "b", "title": "B", "state": "in_cart"},
        {"course_id": 3, "slug": "c", "title": "C", "state": "locked"},
    ]
    assert path_map.path_summary(nodes, 250) == "1 of 3 unlocked · +250 XP bonus"
    assert path_map.path_summary([], 0) == "0 of 0 unlocked"


def test_path_nodes_for_uses_gamification(monkeypatch):
    expected = [{"course_id": 1, "slug": "a", "title": "A", "state": "owned"}]
    monkeypatch.setattr(path_map.gamification, "build_path_nodes", lambda *args: expected)
    assert path_map.path_nodes_for({"courses": []}, {1}, set()) == expected


def test_path_nodes_for_falls_back_to_locked_nodes(monkeypatch):
    def not_ready(*_args):
        raise NotImplementedError

    monkeypatch.setattr(path_map.gamification, "build_path_nodes", not_ready)
    path = {"courses": [{"id": 7, "slug": "x", "title": "X"}]}
    assert path_map.path_nodes_for(path, {7}, set()) == [
        {"course_id": 7, "slug": "x", "title": "X", "state": "locked"}
    ]


# ---------------------------------------------------------------- course card (S3, D-03)
@pytest.mark.parametrize("level", ["Beginner", "Intermediate", "Advanced", "Unknown"])
def test_placeholder_image_is_static_svg(level):
    svg = course_card.placeholder_image(level)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "<script" not in svg


def test_guest_owns_nothing_but_has_a_session_cart(monkeypatch):
    """Guests have a cart in the session (US-305), so "In cart" must show for them too."""

    def must_not_be_called(user_id):
        raise AssertionError("guests have no orders to look up")

    monkeypatch.setattr(course_card.orders, "get_owned_course_ids", must_not_be_called)
    monkeypatch.setattr(course_card.cart, "get_cart_course_ids", lambda: {102})
    assert course_card.shopper_course_ids(None) == (set(), {102})


def test_guest_with_empty_cart(monkeypatch):
    monkeypatch.setattr(course_card.cart, "get_cart_course_ids", lambda: set())
    assert course_card.shopper_course_ids(None) == (set(), set())


def test_shopper_ids_for_signed_in_user(monkeypatch):
    monkeypatch.setattr(course_card.orders, "get_owned_course_ids", lambda user_id: {101})
    monkeypatch.setattr(course_card.cart, "get_cart_course_ids", lambda: {102})
    assert course_card.shopper_course_ids(CUSTOMER) == ({101}, {102})


def test_shopper_ids_survive_service_errors(monkeypatch):
    def broken(*_args):
        raise RuntimeError("database down")

    monkeypatch.setattr(course_card.orders, "get_owned_course_ids", broken)
    monkeypatch.setattr(course_card.cart, "get_cart_course_ids", broken)
    assert course_card.shopper_course_ids(CUSTOMER) == (set(), set())
