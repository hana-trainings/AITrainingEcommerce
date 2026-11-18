"""Unit tests for app/services/orders.py (US-402, US-404, US-405, US-407, US-408)."""

import uuid

import pytest

from app.models.domain import CurrentUser
from app.services import orders
from app.services.auth import CURRENT_USER_KEY
from tests.conftest import CUSTOMER_ID, STAFF_ID


class FakeApiError(Exception):
    """Looks like postgrest.exceptions.APIError: has .message and .details."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.details = details


SUCCESS = {
    "order_id": 2,
    "order_number": "ORD-20261117-0002",
    "total": 79.0,
    "xp_awarded": 100,
    "new_level": 3,
    "level_up": True,
    "new_badges": [],
    "already_existed": False,
}


def sign_in(state: dict, user_id: str = CUSTOMER_ID, role: str = "customer") -> None:
    state[CURRENT_USER_KEY] = CurrentUser(
        id=user_id, email=f"{role}@example.test", display_name=role.title(), role=role
    )


@pytest.fixture
def customer(session_state) -> dict:
    sign_in(session_state)
    return session_state


@pytest.fixture
def staff(session_state) -> dict:
    sign_in(session_state, STAFF_ID, "staff")
    return session_state


# ---------------------------------------------------------------- idempotency key
def test_new_idempotency_key_is_a_new_uuid_each_time():
    first, second = orders.new_idempotency_key(), orders.new_idempotency_key()

    assert uuid.UUID(first) and uuid.UUID(second)
    assert first != second


def test_checkout_key_is_reused_until_finished(session_state):
    key = orders.checkout_key()

    assert orders.checkout_key() == key  # a rerun / double click sends the same key
    orders.finish_checkout_attempt()
    assert orders.checkout_key() != key


# ---------------------------------------------------------------- place_order
def test_place_order_success_calls_rpc_with_key(customer, fake_client):
    fake_client.rpc_results["place_order"] = SUCCESS
    key = orders.new_idempotency_key()

    outcome = orders.place_order(key)

    assert outcome.ok
    assert outcome.order["order_number"] == "ORD-20261117-0002"
    assert fake_client.rpc_calls == [("place_order", {"p_idempotency_key": key})]


def test_place_order_refreshes_header_xp(customer, fake_client):
    fake_client.rpc_results["place_order"] = SUCCESS
    fake_client.tables["profiles"][0]["xp_total"] = 250

    orders.place_order(orders.new_idempotency_key())

    assert customer[CURRENT_USER_KEY].xp_total == 250


def test_place_order_guest_is_refused_without_calling_db(session_state, fake_client):
    outcome = orders.place_order(orders.new_idempotency_key())

    assert outcome.error_code == "NOT_SIGNED_IN"
    assert fake_client.rpc_calls == []


def test_place_order_bad_key_is_invalid_request(customer, fake_client):
    outcome = orders.place_order("not-a-uuid")

    assert outcome.error_code == "INVALID_REQUEST"
    assert fake_client.rpc_calls == []


def test_place_order_not_enough_seats_names_course_and_seats(customer, fake_client):
    fake_client.rpc_results["place_order"] = FakeApiError(
        "NOT_ENOUGH_SEATS: SQL for Analysts", details="seats_available=1"
    )

    outcome = orders.place_order(orders.new_idempotency_key())

    assert not outcome.ok
    assert outcome.error_code == "NOT_ENOUGH_SEATS"
    assert outcome.problem_titles == ["SQL for Analysts"]
    assert (
        outcome.message
        == "Only 1 seat(s) left for SQL for Analysts. Update the quantity to continue."
    )


@pytest.mark.parametrize(
    ("db_message", "code", "text"),
    [
        ("CART_EMPTY", "CART_EMPTY", "Your cart is empty."),
        ("NOT_SIGNED_IN", "NOT_SIGNED_IN", "Please sign in to place your order."),
        (
            "COURSE_UNAVAILABLE: Old Course",
            "COURSE_UNAVAILABLE",
            "Old Course is no longer available",
        ),
        (
            "INVALID_REQUEST: an idempotency key is required",
            "INVALID_REQUEST",
            "Something went wrong",
        ),
    ],
)
def test_place_order_maps_database_errors(customer, fake_client, db_message, code, text):
    fake_client.rpc_results["place_order"] = FakeApiError(db_message)

    outcome = orders.place_order(orders.new_idempotency_key())

    assert outcome.error_code == code
    assert outcome.message.startswith(text)


def test_place_order_unknown_error_is_generic(customer, fake_client):
    fake_client.rpc_results["place_order"] = FakeApiError("duplicate key value violates constraint")

    outcome = orders.place_order(orders.new_idempotency_key())

    assert outcome.error_code == "UNKNOWN"
    assert outcome.message == "Something went wrong, please try again."
    assert "constraint" not in outcome.message


def test_place_order_unexpected_result_is_generic(customer, fake_client):
    fake_client.rpc_results["place_order"] = None

    assert orders.place_order(orders.new_idempotency_key()).error_code == "UNKNOWN"


# ---------------------------------------------------------------- reading orders
def test_get_order_includes_items(customer):
    order = orders.get_order(1)

    assert order["order_number"] == "ORD-20261101-0001"
    assert order["items"][0]["title_snapshot"] == "Python for Data Beginners"
    assert order["item_count"] == 1
    assert isinstance(order["total"], float)


def test_get_order_missing_or_bad_id(customer):
    assert orders.get_order(999) is None
    assert orders.get_order("abc") is None  # type: ignore[arg-type]


def test_list_my_orders_newest_first_only_mine(customer, fake_client):
    fake_client.tables["orders"].append(
        {
            "id": 2,
            "order_number": "ORD-20261105-0002",
            "user_id": CUSTOMER_ID,
            "status": "confirmed",
            "total": 79.0,
            "xp_awarded": 100,
            "badges_awarded": [],
            "created_at": "2026-11-05T10:00:00+00:00",
        }
    )
    fake_client.tables["orders"].append(
        {
            "id": 3,
            "order_number": "ORD-20261106-0003",
            "user_id": STAFF_ID,
            "status": "confirmed",
            "total": 10.0,
            "xp_awarded": 0,
            "badges_awarded": [],
            "created_at": "2026-11-06T10:00:00+00:00",
        }
    )

    numbers = [order["order_number"] for order in orders.list_my_orders()]

    assert numbers == ["ORD-20261105-0002", "ORD-20261101-0001"]


def test_list_my_orders_guest_gets_empty_list(session_state):
    assert orders.list_my_orders() == []


def test_get_owned_course_ids(session_state, fake_client):
    assert orders.get_owned_course_ids(CUSTOMER_ID) == {101}
    fake_client.tables["orders"][0]["status"] = "cancelled"
    assert orders.get_owned_course_ids(CUSTOMER_ID) == set()
    assert orders.get_owned_course_ids("") == set()


def test_badge_names_falls_back_to_readable_code(session_state, fake_client):
    fake_client.tables["badges"].append({"code": "collector", "name": "Collector"})

    assert orders.badge_names(["collector", "first_unlock"]) == ["Collector", "First Unlock"]
    assert orders.badge_names([]) == []


# ---------------------------------------------------------------- US-408 cancel
def test_staff_can_cancel_order(staff, fake_client):
    result = orders.cancel_order(1)

    assert result.ok
    assert fake_client.tables["orders"][0]["status"] == "cancelled"


def test_customer_cannot_cancel(customer, fake_client):
    result = orders.cancel_order(1)

    assert not result.ok
    assert result.message == orders.CANCEL_ORDER_ERRORS["NOT_ALLOWED"]
    assert fake_client.tables["orders"][0]["status"] == "confirmed"


def test_cancel_already_cancelled(staff, fake_client):
    fake_client.tables["orders"][0]["status"] = "cancelled"

    assert orders.cancel_order(1).message == orders.CANCEL_ORDER_ERRORS["ORDER_ALREADY_CANCELLED"]


def test_cancel_maps_database_trigger_error(staff, fake_client, monkeypatch):
    original_table = fake_client.table

    def table(name):
        query = original_table(name)
        if name == "orders":
            original_update = query.update

            def update(values):
                raise FakeApiError("ORDER_ALREADY_CANCELLED: ORD-20261101-0001 cannot be changed")

            query.update = update
            del original_update
        return query

    monkeypatch.setattr(fake_client, "table", table)

    assert orders.cancel_order(1).message == orders.CANCEL_ORDER_ERRORS["ORDER_ALREADY_CANCELLED"]


def test_item_rows_and_readable_date(customer):
    order = orders.get_order(1)

    assert orders.item_rows(order) == [
        {
            "Course": "Python for Data Beginners",
            "Seats": 1,
            "Price": "$49.00",
            "Line total": "$49.00",
        }
    ]
    assert orders.readable_date("2026-11-01T10:00:00+00:00") == "2026-11-01 10:00"
    assert orders.readable_date("") == ""
