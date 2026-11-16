"""Example unit tests for a service: app/services/auth.py (US-501, US-502, US-503, US-701).

They use the fake Supabase client from tests/conftest.py, so no internet or keys
are needed. Copy this style for your own service tests.
"""

import logging

from app.services import auth
from tests.conftest import CUSTOMER_ID, DEMO_PASSWORD, STAFF_ID


def test_sign_in_success_remembers_user_and_role(session_state):
    result = auth.sign_in("staff@example.test", DEMO_PASSWORD)

    assert result.ok
    user = auth.current_user()
    assert user is not None
    assert user.id == STAFF_ID
    assert user.role == "staff"
    assert session_state[auth.AUTH_TOKENS_KEY]["access_token"] == "fake-access-token"


def test_sign_in_wrong_password_gives_generic_message(session_state):
    result = auth.sign_in("customer@example.test", "WrongPass1")

    assert not result.ok
    assert result.message == auth.GENERIC_SIGN_IN_ERROR
    assert auth.current_user() is None


def test_unknown_email_gets_the_same_message_as_wrong_password(session_state):
    # Same text, so nobody can find out which emails are registered (NFR-AUTH-07).
    unknown = auth.sign_in("nobody@example.test", DEMO_PASSWORD)
    wrong = auth.sign_in("customer@example.test", "WrongPass1")
    assert unknown.message == wrong.message


def test_sign_in_never_logs_email_password_or_token(session_state, caplog):
    caplog.set_level(logging.INFO)
    auth.sign_in("customer@example.test", DEMO_PASSWORD)
    auth.sign_in("customer@example.test", "WrongPass1")

    assert "customer@example.test" not in caplog.text
    assert DEMO_PASSWORD not in caplog.text
    assert "fake-access-token" not in caplog.text


def test_sign_out_clears_the_whole_session(session_state):
    auth.sign_in("customer@example.test", DEMO_PASSWORD)
    session_state["guest_cart"] = {101: 1}

    auth.sign_out()

    assert auth.current_user() is None
    assert session_state == {}


def test_require_role_reads_the_role_fresh_from_the_database(session_state, fake_client):
    auth.sign_in("customer@example.test", DEMO_PASSWORD)
    assert auth.require_role("staff", "owner") is None

    # The owner promotes this customer while they are signed in (NFR-SEC-10).
    profile = next(p for p in fake_client.tables["profiles"] if p["id"] == CUSTOMER_ID)
    profile["role"] = "staff"

    user = auth.require_role("staff", "owner")
    assert user is not None
    assert user.role == "staff"


def test_require_role_for_guest_is_none(session_state):
    assert auth.require_role("customer", "staff", "owner") is None


def test_register_creates_customer_and_signs_in(session_state):
    result = auth.register("New Learner", "new@example.test", "Abcdefg1", "Abcdefg1")

    assert result.ok
    user = auth.current_user()
    assert user.display_name == "New Learner"
    assert user.role == "customer"


def test_register_duplicate_email(session_state):
    result = auth.register("Someone", "customer@example.test", "Abcdefg1", "Abcdefg1")

    assert not result.ok
    assert result.message == auth.DUPLICATE_EMAIL_ERROR


def test_register_shows_field_errors(session_state):
    result = auth.register("", "not-an-email", "short", "short")

    assert not result.ok
    assert set(result.data["errors"]) == {"display_name", "email", "password"}


def test_password_rules():
    assert auth.validate_password("abc12345") == []
    assert auth.validate_password("abcdefgh")  # no number
    assert auth.validate_password("12345678")  # no letter
    assert auth.validate_password("a1")  # too short
