"""Unit tests for app/services/email_outbox.py (US-406, NFR-REL-02, NFR-SEC-15)."""

import re

import pytest

from app.models.domain import CurrentUser
from app.services import email_outbox, orders
from app.services.auth import CURRENT_USER_KEY
from tests.conftest import CUSTOMER_ID

ORDER = {
    "id": 1,
    "order_number": "ORD-20261101-0001",
    "status": "confirmed",
    "total": 98.0,
    "xp_awarded": 100,
    "created_at": "2026-11-01T10:00:00+00:00",
    "items": [
        {
            "course_id": 101,
            "title_snapshot": "Python <b>for</b> Data",
            "unit_price": 49.0,
            "quantity": 2,
        }
    ],
}


@pytest.fixture
def customer(session_state, tmp_path, monkeypatch) -> dict:
    """Signed-in customer; outbox files go to a temporary folder."""
    session_state[CURRENT_USER_KEY] = CurrentUser(
        id=CUSTOMER_ID, email="customer@example.test", display_name="Casey"
    )
    monkeypatch.setattr(email_outbox, "OUTBOX_PATH", tmp_path / "outbox")
    return session_state


# ---------------------------------------------------------------- build (pure)
def test_build_email_has_required_parts():
    email = email_outbox.build_confirmation_email(ORDER, "casey@example.test", "Casey")

    assert email["subject"] == "Your order ORD-20261101-0001 is confirmed"
    assert re.fullmatch(r"order_ORD-20261101-0001_\d{14}\.html", email["file_name"])
    body = email["html_body"]
    for text in (
        "casey@example.test",
        "Hi Casey",
        "ORD-20261101-0001",
        "1 Nov 2026",
        "$98.00",
        "+100 XP",
        "This is a demo store",
    ):
        assert text in body
    assert ">2<" in body  # quantity


def test_build_email_escapes_user_and_database_text():
    email = email_outbox.build_confirmation_email(ORDER, "casey@example.test", "<script>x</script>")

    assert "<script>" not in email["html_body"]
    assert "&lt;script&gt;" in email["html_body"]
    assert "Python &lt;b&gt;for&lt;/b&gt; Data" in email["html_body"]


def test_build_email_file_name_is_safe_even_with_odd_order_number():
    odd = dict(ORDER, order_number="../../etc/passwd")

    file_name = email_outbox.build_confirmation_email(odd, "a@b.co", "A")["file_name"]

    assert re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", file_name)
    assert "/" not in file_name


# ---------------------------------------------------------------- save
def test_save_writes_file_and_table_row(customer, fake_client):
    result = email_outbox.save_confirmation_email(1)

    assert result.ok and result.data["file_written"]
    row = fake_client.tables["email_outbox"][0]
    assert row["order_id"] == 1 and row["user_id"] == CUSTOMER_ID
    assert (email_outbox.OUTBOX_PATH / row["file_name"]).read_text(encoding="utf-8") == row[
        "html_body"
    ]


def test_save_still_ok_when_file_write_fails(customer, fake_client, monkeypatch):
    monkeypatch.setattr(email_outbox, "_write_file", lambda _email: False)

    result = email_outbox.save_confirmation_email(1)

    assert result.ok  # US-406 AC5: the order must not fail
    assert not result.data["file_written"]
    assert len(fake_client.tables["email_outbox"]) == 1


def test_save_never_raises_when_database_fails(customer, fake_client):
    fake_client.table = lambda _name: (_ for _ in ()).throw(ConnectionError("offline"))

    result = email_outbox.save_confirmation_email(1)

    assert not result.ok
    assert "offline" not in result.message


def test_save_twice_keeps_one_email(customer, fake_client):
    email_outbox.save_confirmation_email(1)
    email_outbox.save_confirmation_email(1)

    assert len(fake_client.tables["email_outbox"]) == 1


def test_save_for_guest_or_missing_order(session_state, customer, monkeypatch):
    monkeypatch.setattr(orders, "get_order", lambda _order_id: None)
    assert not email_outbox.save_confirmation_email(999).ok

    session_state.pop(CURRENT_USER_KEY)
    assert not email_outbox.save_confirmation_email(1).ok


# ---------------------------------------------------------------- read
def test_get_email_for_order(customer, fake_client):
    assert email_outbox.get_email_for_order(1) is None
    email_outbox.save_confirmation_email(1)

    assert (
        email_outbox.get_email_for_order(1)["subject"]
        == "Your order ORD-20261101-0001 is confirmed"
    )


# ---------------------------------------------------------------- review fixes
class UniqueViolation(Exception):
    code = "23505"


def test_save_treats_unique_violation_as_already_saved(customer, fake_client, monkeypatch):
    original_table = fake_client.table

    def table(name):
        query = original_table(name)
        if name == "email_outbox":
            query.insert = lambda _row: (_ for _ in ()).throw(UniqueViolation("duplicate key"))
        return query

    monkeypatch.setattr(fake_client, "table", table)

    result = email_outbox.save_confirmation_email(1)

    assert result.ok
    assert result.message == "Confirmation email saved."


def test_get_email_for_order_returns_oldest_row(customer, fake_client):
    fake_client.tables["email_outbox"].extend(
        [
            {"id": 7, "order_id": 1, "subject": "Real one", "html_body": "<p>ok</p>"},
            {"id": 9, "order_id": 1, "subject": "Added later", "html_body": "<p>x</p>"},
        ]
    )

    assert email_outbox.get_email_for_order(1)["subject"] == "Real one"


def test_safe_preview_html_makes_links_and_forms_inert():
    stored = (
        '<p style="color:red">Hi <a href="https://evil.test">click</a></p>'
        '<form action="https://evil.test"><input name="pw"><button>Go</button></form>'
        "<script>alert(1)</script><img src=x onerror=alert(1)>"
        "<table><tr><td>A &amp; B</td></tr></table>"
    )

    preview = email_outbox.safe_preview_html(stored)

    assert preview == "<p>Hi click</p>Go<table><tr><td>A &amp; B</td></tr></table>"
    for bad in ("href", "action", "<form", "<a", "<script", "<img", "style=", "onerror"):
        assert bad not in preview


def test_safe_preview_html_keeps_the_real_email_readable():
    body = email_outbox.build_confirmation_email(ORDER, "casey@example.test", "Casey")["html_body"]

    preview = email_outbox.safe_preview_html(body)

    assert "Hi Casey" in preview and "ORD-20261101-0001" in preview
    assert "Python &lt;b&gt;for&lt;/b&gt; Data" in preview  # still escaped
    assert "style" not in preview
