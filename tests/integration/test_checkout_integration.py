"""Integration tests for checkout against a REAL Supabase project (US-403, NFR-MNT-05).

They test the place_order database function itself: seats are deducted, a course
can never be oversold, a failed order changes nothing, and a double submit with the
same idempotency key creates only one order.

These tests are SKIPPED unless all four environment variables are set:
    SUPABASE_TEST_URL, SUPABASE_TEST_PUBLISHABLE_KEY,
    SUPABASE_TEST_EMAIL, SUPABASE_TEST_PASSWORD (a customer account)

WARNING: they place real (demo) orders and take seats. Point them at a TEST
project or a local Supabase (`supabase start`), never at the shared class project.
Run them with:  python -m pytest tests/integration -q
"""

import os
import uuid

import pytest

REQUIRED_VARS = (
    "SUPABASE_TEST_URL",
    "SUPABASE_TEST_PUBLISHABLE_KEY",
    "SUPABASE_TEST_EMAIL",
    "SUPABASE_TEST_PASSWORD",
)
pytestmark = pytest.mark.skipif(
    not all(os.environ.get(name) for name in REQUIRED_VARS),
    reason="Integration tests need SUPABASE_TEST_* environment variables (see module docstring).",
)


@pytest.fixture(scope="module")
def client():
    """A Supabase client signed in as the test customer (publishable key only)."""
    from supabase import create_client

    supabase = create_client(
        os.environ["SUPABASE_TEST_URL"], os.environ["SUPABASE_TEST_PUBLISHABLE_KEY"]
    )
    response = supabase.auth.sign_in_with_password(
        {
            "email": os.environ["SUPABASE_TEST_EMAIL"],
            "password": os.environ["SUPABASE_TEST_PASSWORD"],
        }
    )
    supabase.user_id = response.user.id  # handy for the helpers below
    yield supabase
    supabase.auth.sign_out()


@pytest.fixture(autouse=True)
def empty_cart(client):
    """Start and finish every test with an empty saved cart."""
    client.table("cart_items").delete().eq("user_id", client.user_id).execute()
    yield
    client.table("cart_items").delete().eq("user_id", client.user_id).execute()


# ---------------------------------------------------------------- helpers
def seats_of(client, course_id: int) -> int:
    row = client.table("courses").select("seats_available").eq("id", course_id).single().execute()
    return int(row.data["seats_available"])


def find_course(client, min_seats: int, max_seats: int = 10_000) -> dict:
    """A published course whose seats_available is in [min_seats, max_seats], or skip."""
    rows = (
        client.table("courses")
        .select("id, title, price, seats_available")
        .eq("is_published", True)
        .gte("seats_available", min_seats)
        .lte("seats_available", max_seats)
        .order("seats_available", desc=True)
        .limit(1)
        .execute()
    ).data
    if not rows:
        pytest.skip(f"No published course with {min_seats}-{max_seats} seats in the test project.")
    return rows[0]


def put_in_cart(client, course_id: int, quantity: int) -> None:
    client.table("cart_items").insert(
        {"user_id": client.user_id, "course_id": course_id, "quantity": quantity}
    ).execute()


def place(client, key: str) -> dict:
    return client.rpc("place_order", {"p_idempotency_key": key}).execute().data


def order_count(client) -> int:
    response = (
        client.table("orders").select("id", count="exact").eq("user_id", client.user_id).execute()
    )
    return int(response.count or 0)


# ---------------------------------------------------------------- US-403
def test_place_order_deducts_seats_creates_items_and_clears_cart(client):
    course = find_course(client, min_seats=2)
    seats_before = seats_of(client, course["id"])
    put_in_cart(client, course["id"], 2)

    result = place(client, str(uuid.uuid4()))

    assert result["already_existed"] is False
    assert result["order_number"].startswith("ORD-")
    assert float(result["total"]) == pytest.approx(float(course["price"]) * 2)
    assert seats_of(client, course["id"]) == seats_before - 2
    items = (
        client.table("order_items")
        .select("course_id, quantity")
        .eq("order_id", result["order_id"])
        .execute()
    ).data
    assert items == [{"course_id": course["id"], "quantity": 2}]
    assert (
        client.table("cart_items").select("course_id").eq("user_id", client.user_id).execute().data
        == []
    )


# ---------------------------------------------------------------- NFR-MNT-05: no oversell
def test_not_enough_seats_fails_and_changes_nothing(client):
    course = find_course(client, min_seats=1, max_seats=4)  # so 5 seats is too many
    seats_before = seats_of(client, course["id"])
    orders_before = order_count(client)
    put_in_cart(client, course["id"], 5)

    with pytest.raises(Exception) as error:
        place(client, str(uuid.uuid4()))

    assert "NOT_ENOUGH_SEATS" in str(error.value)
    assert f"seats_available={seats_before}" in str(
        getattr(error.value, "details", "") or error.value
    )
    # US-403 AC3: the whole order failed, nothing was deducted, the cart is untouched.
    assert seats_of(client, course["id"]) == seats_before
    assert order_count(client) == orders_before
    cart = (
        client.table("cart_items").select("quantity").eq("user_id", client.user_id).execute().data
    )
    assert cart == [{"quantity": 5}]


def test_empty_cart_is_refused(client):
    with pytest.raises(Exception) as error:
        place(client, str(uuid.uuid4()))

    assert "CART_EMPTY" in str(error.value)


# ---------------------------------------------------------------- NFR-DATA-04: double submit
def test_same_idempotency_key_creates_one_order(client):
    course = find_course(client, min_seats=1)
    seats_before = seats_of(client, course["id"])
    orders_before = order_count(client)
    put_in_cart(client, course["id"], 1)
    key = str(uuid.uuid4())

    first = place(client, key)
    second = place(client, key)  # the double click

    assert second["order_id"] == first["order_id"]
    assert second["already_existed"] is True
    assert order_count(client) == orders_before + 1
    assert seats_of(client, course["id"]) == seats_before - 1
