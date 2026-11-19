"""AppTest tests for the buying pages: cart, checkout, confirmation, my orders, admin orders.

Each page is rendered for the right role, and the wrong role is denied.
Other tracks' functions (catalog.next_in_path, profile.get_reduce_motion,
admin.list_all_orders) are replaced by simple fakes so these tests only test our pages.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.models.domain import CurrentUser
from app.services import admin, catalog, orders, profile
from app.services.auth import CURRENT_USER_KEY
from app.services.cart import GUEST_CART_KEY
from app.services.supabase_client import CLIENT_SESSION_KEY
from app.utils.text import escape_markdown
from tests.conftest import CUSTOMER_ID, OWNER_ID, STAFF_ID

APP_FILE = str(Path(__file__).resolve().parents[2] / "app" / "streamlit_app.py")
SUCCESS = {
    "order_id": 1,
    "order_number": "ORD-20261101-0001",
    "total": 49.0,
    "xp_awarded": 100,
    "new_level": 2,
    "level_up": True,
    "new_badges": ["first_unlock"],
    "already_existed": False,
}


class FakeApiError(Exception):
    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.message, self.details = message, details


@pytest.fixture(autouse=True)
def other_tracks(monkeypatch, tmp_path):
    """Stand-ins for functions owned by other tracks, and a temp outbox folder."""
    monkeypatch.setattr(catalog, "next_in_path", lambda owned, limit=3: [])
    monkeypatch.setattr(profile, "get_reduce_motion", lambda: False)
    from app.services import email_outbox

    monkeypatch.setattr(email_outbox, "OUTBOX_PATH", tmp_path / "outbox")


@pytest.fixture
def app(fake_client) -> AppTest:
    at = AppTest.from_file(APP_FILE, default_timeout=30)
    at.secrets["SUPABASE_URL"] = "https://example.supabase.co"
    at.secrets["SUPABASE_PUBLISHABLE_KEY"] = "sb_publishable_test"
    at.session_state[CLIENT_SESSION_KEY] = fake_client
    return at


def sign_in_as(at: AppTest, user_id: str, role: str) -> None:
    at.session_state[CURRENT_USER_KEY] = CurrentUser(
        id=user_id, email=f"{role}@example.test", display_name=role.title(), role=role
    )


def open_page(at: AppTest, page: str) -> AppTest:
    at.run()
    return at.switch_page(page).run()


def all_text(at: AppTest) -> str:
    parts = [
        e.value
        for e in (
            *at.title,
            *at.markdown,
            *at.info,
            *at.error,
            *at.caption,
            *at.warning,
            *at.success,
        )
    ]
    return " ".join(str(part) for part in parts)


def add_cart_row(fake_client, course_id: int, quantity: int = 1) -> None:
    fake_client.tables["cart_items"].append(
        {"user_id": CUSTOMER_ID, "course_id": course_id, "quantity": quantity}
    )


# ---------------------------------------------------------------- cart
def test_empty_cart_shows_empty_state(app):
    open_page(app, "views/cart.py")

    assert not app.exception
    assert "Your cart is empty" in all_text(app)


def test_guest_cart_lists_items_summary_and_sign_in_link(app):
    app.session_state[GUEST_CART_KEY] = {101: 2}
    open_page(app, "views/cart.py")

    assert not app.exception
    text = all_text(app)
    assert "$98.00" in text and "+100 XP" in text
    assert "Unlock preview" in str([box.proto for box in app.success])
    assert app.number_input[0].value == 2


def test_cart_flags_sold_out_line(app):
    app.session_state[GUEST_CART_KEY] = {103: 1}
    open_page(app, "views/cart.py")

    assert "sold out" in all_text(app)
    assert "need your attention" in all_text(app)


def test_cart_change_quantity_and_remove(app, fake_client):
    sign_in_as(app, CUSTOMER_ID, "customer")
    add_cart_row(fake_client, 102)
    open_page(app, "views/cart.py")

    app.number_input[0].set_value(3).run()
    assert fake_client.tables["cart_items"][0]["quantity"] == 3

    app.button(key="cart_remove_102").click().run()
    assert fake_client.tables["cart_items"] == []
    assert "Your cart is empty" in all_text(app)


def test_cart_shows_checkout_problem_message(app):
    app.session_state[GUEST_CART_KEY] = {102: 1}
    app.session_state[orders.CHECKOUT_PROBLEM_KEY] = "Only 1 seat(s) left for SQL for Analysts."
    open_page(app, "views/cart.py")

    # Shown escaped for Markdown (the title comes from the database).
    assert escape_markdown("Only 1 seat(s) left for SQL for Analysts.") in all_text(app)


# ---------------------------------------------------------------- checkout
def test_guest_checkout_asks_to_sign_in_and_remembers_return(app):
    open_page(app, "views/checkout.py")

    assert not app.exception
    assert "Please sign in" in all_text(app)
    assert app.session_state["return_to"] == "views/checkout.py"


def test_checkout_place_order_needs_demo_checkbox(app, fake_client):
    sign_in_as(app, CUSTOMER_ID, "customer")
    add_cart_row(fake_client, 102, 2)
    open_page(app, "views/checkout.py")

    assert not app.exception
    text = all_text(app)
    assert "Demo store: no payment is taken." in text
    assert "customer@example" in text  # shown escaped for Markdown
    assert app.button(key="checkout_place_order").disabled
    app.checkbox(key="checkout_understood").check().run()
    assert not app.button(key="checkout_place_order").disabled


def test_checkout_success_saves_email_and_opens_confirmation(app, fake_client):
    sign_in_as(app, CUSTOMER_ID, "customer")
    add_cart_row(fake_client, 102)
    fake_client.rpc_results["place_order"] = SUCCESS
    open_page(app, "views/checkout.py")
    app.checkbox(key="checkout_understood").check().run()
    first_key = app.session_state[orders.CHECKOUT_KEY_SESSION]

    app.button(key="checkout_place_order").click().run()

    assert not app.exception
    assert fake_client.rpc_calls == [("place_order", {"p_idempotency_key": first_key})]
    assert len(fake_client.tables["email_outbox"]) == 1
    assert "Order confirmed" in all_text(app)


def test_checkout_stock_conflict_returns_to_cart(app, fake_client):
    sign_in_as(app, CUSTOMER_ID, "customer")
    add_cart_row(fake_client, 102, 2)
    fake_client.rpc_results["place_order"] = FakeApiError(
        "NOT_ENOUGH_SEATS: SQL for Analysts", "seats_available=1"
    )
    open_page(app, "views/checkout.py")
    app.checkbox(key="checkout_understood").check().run()

    app.button(key="checkout_place_order").click().run()

    assert not app.exception
    assert escape_markdown("Only 1 seat(s) left for SQL for Analysts") in all_text(app)
    assert "Your cart" in all_text(app)


def test_checkout_blocks_cart_with_problems(app, fake_client):
    sign_in_as(app, CUSTOMER_ID, "customer")
    add_cart_row(fake_client, 103)  # sold out
    open_page(app, "views/checkout.py")

    assert "need your attention" in all_text(app)
    assert len(app.button) == 0 or all(b.key != "checkout_place_order" for b in app.button)


# ---------------------------------------------------------------- confirmation
def test_confirmation_shows_order_and_celebrates_once(app):
    sign_in_as(app, CUSTOMER_ID, "customer")
    app.session_state[orders.CELEBRATION_KEY] = {
        "order_id": 1,
        "level_up": True,
        "new_level": 2,
        "show": True,
    }
    app.query_params["order"] = "1"
    open_page(app, "views/order_confirmation.py")

    assert not app.exception
    text = all_text(app)
    assert r"ORD\-20261101\-0001" in text and "+100 XP" in text  # escaped for Markdown
    assert "level 2" in text
    assert "First Unlock" in text
    assert orders.CELEBRATION_KEY not in app.session_state


def test_confirmation_unknown_order_is_not_found(app):
    sign_in_as(app, CUSTOMER_ID, "customer")
    app.query_params["order"] = "999"
    open_page(app, "views/order_confirmation.py")

    assert not app.exception
    assert "Order not found." in [w.value for w in app.warning]


def test_confirmation_guest_is_asked_to_sign_in(app):
    open_page(app, "views/order_confirmation.py")

    assert "Please sign in" in all_text(app)


# ---------------------------------------------------------------- my orders
def test_my_orders_lists_orders_and_email_preview(app, fake_client):
    sign_in_as(app, CUSTOMER_ID, "customer")
    fake_client.tables["email_outbox"].append(
        {
            "id": 1,
            "order_id": 1,
            "user_id": CUSTOMER_ID,
            "to_email": "customer@example.test",
            "subject": "Your order ORD-20261101-0001 is confirmed",
            "html_body": "<p>Hi</p>",
            "file_name": "order_x.html",
            "created_at": "2026-11-01T10:00:00+00:00",
        }
    )
    open_page(app, "views/my_orders.py")

    assert not app.exception
    assert app.dataframe[0].value["Order"].tolist() == ["ORD-20261101-0001"]
    app.toggle(key="my_orders_email_1").set_value(True).run()
    assert "Subject: Your order ORD" in all_text(app)


def test_my_orders_empty_state(app):
    sign_in_as(app, OWNER_ID, "owner")
    open_page(app, "views/my_orders.py")

    assert "No orders yet" in all_text(app)


def test_my_orders_guest_is_asked_to_sign_in(app):
    open_page(app, "views/my_orders.py")

    assert "Please sign in" in all_text(app)


# ---------------------------------------------------------------- admin orders
@pytest.fixture
def staff_orders(monkeypatch):
    rows = [
        {
            "id": 1,
            "order_number": "ORD-20261101-0001",
            "customer_email": "customer@example.test",
            "created_at": "2026-11-01T10:00:00+00:00",
            "total": 49.0,
            "item_count": 1,
            "status": "confirmed",
        }
    ]
    monkeypatch.setattr(admin, "list_all_orders", lambda **_filters: rows)
    return rows


def test_admin_orders_staff_sees_table_and_can_cancel(app, fake_client, staff_orders):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, "views/admin_orders.py")

    assert not app.exception
    assert app.dataframe[0].value["Customer email"].tolist() == ["customer@example.test"]
    app.button(key="admin_cancel_open").click().run()
    app.button(key="admin_cancel_yes").click().run()

    assert not app.exception
    assert fake_client.tables["orders"][0]["status"] == "cancelled"


def test_admin_orders_customer_is_denied(app, staff_orders):
    sign_in_as(app, CUSTOMER_ID, "customer")
    open_page(app, "views/admin_orders.py")

    assert "You don't have access to this page." in [e.value for e in app.error]
    assert len(app.dataframe) == 0


# ---------------------------------------------------------------- review fixes
def test_confirmation_staff_cannot_see_customer_order(app):
    sign_in_as(app, STAFF_ID, "staff")  # RLS lets staff READ every order
    app.query_params["order"] = "1"  # the customer's order
    open_page(app, "views/order_confirmation.py")

    assert not app.exception
    assert "Order not found." in [w.value for w in app.warning]
    assert "customer@example" not in all_text(app)


def test_confirmation_shows_cancelled_status(app, fake_client):
    sign_in_as(app, CUSTOMER_ID, "customer")
    fake_client.tables["orders"][0]["status"] = "cancelled"
    app.query_params["order"] = "1"
    open_page(app, "views/order_confirmation.py")

    assert "Order cancelled" in all_text(app)
    assert "Thank you" not in all_text(app)


def test_checkout_success_clears_key_and_flag(app, fake_client):
    sign_in_as(app, CUSTOMER_ID, "customer")
    add_cart_row(fake_client, 102)
    fake_client.rpc_results["place_order"] = SUCCESS
    open_page(app, "views/checkout.py")
    app.checkbox(key="checkout_understood").check().run()

    app.button(key="checkout_place_order").click().run()

    assert orders.CHECKOUT_KEY_SESSION not in app.session_state
    assert (
        not app.session_state["checkout_placing"]
        if "checkout_placing" in app.session_state
        else True
    )


def test_checkout_stale_flag_does_not_place_order(app, fake_client):
    """Left the page mid-call earlier: a later visit must not order without a new click."""
    sign_in_as(app, CUSTOMER_ID, "customer")
    add_cart_row(fake_client, 102)
    fake_client.rpc_results["place_order"] = SUCCESS
    app.session_state["checkout_placing"] = True
    open_page(app, "views/checkout.py")

    assert not app.exception
    assert fake_client.rpc_calls == []
    assert "checkout_placing" not in app.session_state
    assert app.button(key="checkout_place_order").disabled  # box not ticked


def test_cart_checkout_problem_is_escaped(app):
    app.session_state[GUEST_CART_KEY] = {102: 1}
    app.session_state[orders.CHECKOUT_PROBLEM_KEY] = (
        "Only 1 seat(s) left for [click](http://x.test)."
    )
    open_page(app, "views/cart.py")

    assert r"\[click\]\(http://x\.test\)" in all_text(app)
