"""Unit tests for app/services/cart.py (US-301 to US-307), using the fake Supabase client.

Sample courses (tests/conftest.py): 101 has 22 seats, 102 has 3 seats,
103 is sold out, 104 is unpublished.
"""

import pytest

from app.models.domain import CurrentUser
from app.services import cart
from app.services.auth import CURRENT_USER_KEY
from tests.conftest import CUSTOMER_ID


@pytest.fixture
def signed_in(session_state) -> dict:
    """The fake session with the sample customer signed in."""
    session_state[CURRENT_USER_KEY] = CurrentUser(
        id=CUSTOMER_ID, email="customer@example.test", display_name="Casey"
    )
    return session_state


def saved_cart(fake_client) -> dict[int, int]:
    return {row["course_id"]: row["quantity"] for row in fake_client.tables["cart_items"]}


# ---------------------------------------------------------------- US-301 add (guest)
def test_guest_add_item_puts_course_in_session_cart(session_state):
    result = cart.add_item(101)

    assert result.ok
    assert "Added Python for Data Beginners" in result.message
    assert session_state[cart.GUEST_CART_KEY] == {101: 1}


def test_adding_again_increases_quantity(session_state):
    cart.add_item(101)
    result = cart.add_item(101)

    assert result.ok
    assert session_state[cart.GUEST_CART_KEY] == {101: 2}


def test_add_sold_out_course_is_refused(session_state):
    result = cart.add_item(103)

    assert not result.ok
    assert "sold out" in result.message
    assert session_state.get(cart.GUEST_CART_KEY, {}) == {}


def test_add_unpublished_or_missing_course_is_refused(session_state):
    assert not cart.add_item(104).ok
    assert not cart.add_item(999).ok


def test_add_is_capped_at_five(session_state):
    for _ in range(5):
        cart.add_item(101)
    result = cart.add_item(101)

    assert not result.ok
    assert session_state[cart.GUEST_CART_KEY] == {101: 5}


def test_add_is_capped_at_seats_left(session_state):
    result = cart.add_item(102, quantity=4)  # only 3 seats left

    assert result.ok
    assert "most allowed" in result.message
    assert session_state[cart.GUEST_CART_KEY] == {102: 3}


def test_add_returns_friendly_error_when_database_fails(session_state, fake_client):
    def broken_table(_name):
        raise ConnectionError("offline")

    fake_client.table = broken_table
    result = cart.add_item(101)

    assert not result.ok
    assert "offline" not in result.message


def test_get_item_count_sums_seats(session_state):
    assert cart.get_item_count() == 0
    cart.add_item(101)
    cart.add_item(101)
    cart.add_item(102)

    assert cart.get_item_count() == 3


def test_get_item_count_is_zero_when_database_fails(signed_in, fake_client):
    fake_client.table = lambda _name: (_ for _ in ()).throw(ConnectionError("offline"))

    assert cart.get_item_count() == 0


# ---------------------------------------------------------------- US-305 signed-in cart
def test_signed_in_add_item_saves_to_cart_items_table(signed_in, fake_client):
    cart.add_item(101)
    cart.add_item(101)

    assert saved_cart(fake_client) == {101: 2}
    assert cart.GUEST_CART_KEY not in signed_in or signed_in[cart.GUEST_CART_KEY] == {}


def test_signed_in_cart_ignores_other_users_rows(signed_in, fake_client):
    fake_client.tables["cart_items"].append(
        {"user_id": "someone-else", "course_id": 102, "quantity": 2}
    )

    assert cart.get_item_count() == 0


# ---------------------------------------------------------------- US-302 view + US-307 price check
def test_get_items_reads_fresh_prices_and_flags_problems(session_state, fake_client):
    session_state[cart.GUEST_CART_KEY] = {101: 2, 103: 1, 104: 1}
    fake_client.tables["courses"][0]["price"] = 59.0  # price changed in the database

    lines = {line["course_id"]: line for line in cart.get_items()}

    assert lines[101]["unit_price"] == 59.0
    assert lines[101]["line_total"] == 118.0
    assert lines[101]["is_available"]
    assert not lines[103]["is_available"] and "sold out" in lines[103]["problem"]
    # A guest can't read the unpublished course (RLS), the fake returns it unpublished.
    assert not lines[104]["is_available"]


def test_get_items_flags_quantity_above_seats(session_state, fake_client):
    session_state[cart.GUEST_CART_KEY] = {102: 3}
    fake_client.tables["courses"][1]["seats_available"] = 1

    line = cart.get_items()[0]

    assert not line["is_available"]
    assert "Only 1 seat(s) left" in line["problem"]


def test_get_items_marks_missing_course(session_state):
    session_state[cart.GUEST_CART_KEY] = {999: 1}

    line = cart.get_items()[0]

    assert not line["is_available"]
    assert line["slug"] == ""


def test_get_items_empty_cart(session_state):
    assert cart.get_items() == []


def test_get_items_gives_no_xp_for_owned_course(signed_in, fake_client):
    # The customer already owns course 101 (sample order 1).
    fake_client.tables["cart_items"].append(
        {"user_id": CUSTOMER_ID, "course_id": 101, "quantity": 1}
    )

    line = cart.get_items()[0]

    assert line["already_owned"]
    assert line["xp_reward"] == 0


def test_price_changes_reports_each_change_once(session_state, fake_client):
    session_state[cart.GUEST_CART_KEY] = {101: 1}
    assert cart.price_changes(cart.get_items()) == []  # first look: nothing to compare

    fake_client.tables["courses"][0]["price"] = 59.0
    messages = cart.price_changes(cart.get_items())

    assert messages == ["The price of Python for Data Beginners changed from $49.00 to $59.00."]
    assert cart.price_changes(cart.get_items()) == []


def test_summarize_counts_only_available_lines():
    lines = [
        {
            "course_id": 1,
            "quantity": 2,
            "line_total": 98.0,
            "xp_reward": 100,
            "is_available": True,
            "module_count": 4,
            "already_owned": False,
        },
        {
            "course_id": 2,
            "quantity": 1,
            "line_total": 79.0,
            "xp_reward": 100,
            "is_available": False,
            "module_count": 5,
            "already_owned": False,
        },
        {
            "course_id": 3,
            "quantity": 1,
            "line_total": 39.0,
            "xp_reward": 0,
            "is_available": True,
            "module_count": 3,
            "already_owned": True,
        },
    ]

    summary = cart.summarize(lines)

    assert summary == {
        "item_count": 3,
        "subtotal": 137.0,
        "total": 137.0,
        "total_xp": 100,
        "courses_unlocked": 1,
        "modules_unlocked": 4,
    }


def test_summarize_empty():
    assert cart.summarize([])["total"] == 0


# ---------------------------------------------------------------- US-303 quantity
def test_update_quantity_sets_value(session_state):
    cart.add_item(101)
    result = cart.update_quantity(101, 4)

    assert result.ok
    assert session_state[cart.GUEST_CART_KEY] == {101: 4}


def test_update_quantity_caps_at_seats_and_says_so(session_state):
    cart.add_item(102)
    result = cart.update_quantity(102, 5)  # only 3 seats

    assert result.ok
    assert "at most 3" in result.message
    assert session_state[cart.GUEST_CART_KEY] == {102: 3}


def test_update_quantity_never_below_one(signed_in, fake_client):
    cart.add_item(101)
    cart.update_quantity(101, 0)

    assert saved_cart(fake_client) == {101: 1}


def test_update_quantity_for_course_not_in_cart(session_state):
    assert not cart.update_quantity(101, 2).ok


# ---------------------------------------------------------------- US-304 remove
def test_remove_item_guest(session_state):
    cart.add_item(101)
    cart.add_item(102)

    assert cart.remove_item(101).ok
    assert session_state[cart.GUEST_CART_KEY] == {102: 1}


def test_remove_item_signed_in(signed_in, fake_client):
    cart.add_item(101)

    assert cart.remove_item(101).ok
    assert saved_cart(fake_client) == {}


def test_remove_item_not_in_cart_is_harmless(session_state):
    assert cart.remove_item(101).ok


# ---------------------------------------------------------------- US-306 merge
def test_merge_adds_quantities_and_caps(session_state, fake_client):
    fake_client.tables["cart_items"].append(
        {"user_id": CUSTOMER_ID, "course_id": 101, "quantity": 4}
    )
    session_state[cart.GUEST_CART_KEY] = {101: 3, 102: 2}

    result = cart.merge_guest_cart(CUSTOMER_ID)

    assert result.ok
    assert saved_cart(fake_client) == {101: 5, 102: 2}  # 4 + 3 capped at 5
    assert session_state[cart.GUEST_CART_KEY] == {}


def test_merge_skips_sold_out_and_unpublished(session_state, fake_client):
    session_state[cart.GUEST_CART_KEY] = {103: 1, 104: 1}

    assert cart.merge_guest_cart(CUSTOMER_ID).ok
    assert saved_cart(fake_client) == {}


def test_merge_with_empty_guest_cart_does_nothing(session_state, fake_client):
    assert cart.merge_guest_cart(CUSTOMER_ID).ok
    assert saved_cart(fake_client) == {}


def test_merge_keeps_guest_cart_if_database_fails(session_state, fake_client):
    session_state[cart.GUEST_CART_KEY] = {101: 1}
    fake_client.table = lambda _name: (_ for _ in ()).throw(ConnectionError("offline"))

    result = cart.merge_guest_cart(CUSTOMER_ID)

    assert not result.ok
    assert session_state[cart.GUEST_CART_KEY] == {101: 1}
