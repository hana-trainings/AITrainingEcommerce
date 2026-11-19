"""Unit tests for token refresh / session expiry (NFR-AUTH-04, U3-15) and the
guest cart merge on sign-in (US-306) in app/services/auth.py."""

import time
from types import SimpleNamespace

from app.models.domain import ActionResult
from app.services import auth, cart
from tests.conftest import DEMO_PASSWORD


def expire_tokens(session_state: dict) -> None:
    session_state[auth.AUTH_TOKENS_KEY]["expires_at"] = time.time() - 10


def test_refresh_not_needed_while_token_is_fresh(session_state, fake_client):
    auth.sign_in("customer@example.test", DEMO_PASSWORD)
    calls = []
    fake_client.auth.refresh_session = lambda token: calls.append(token)

    assert auth.refresh_session() is True
    assert calls == []  # no network call when the token is still valid


def test_expired_token_is_refreshed(session_state, fake_client):
    auth.sign_in("customer@example.test", DEMO_PASSWORD)
    expire_tokens(session_state)
    new_session = SimpleNamespace(
        access_token="new-access", refresh_token="new-refresh", expires_at=time.time() + 3600
    )
    fake_client.auth.refresh_session = lambda token: SimpleNamespace(session=new_session)

    assert auth.current_user() is not None  # current_user() refreshes on the way
    assert session_state[auth.AUTH_TOKENS_KEY]["access_token"] == "new-access"
    assert session_state[auth.AUTH_TOKENS_KEY]["refresh_token"] == "new-refresh"


def test_failed_refresh_signs_out_with_message(session_state, fake_client):
    auth.sign_in("customer@example.test", DEMO_PASSWORD)
    expire_tokens(session_state)

    def refresh_fails(token):
        raise RuntimeError("refresh token revoked")

    fake_client.auth.refresh_session = refresh_fails

    assert auth.current_user() is None
    assert auth.CURRENT_USER_KEY not in session_state
    assert auth.AUTH_TOKENS_KEY not in session_state
    assert session_state[auth.SESSION_EXPIRED_KEY] is True
    assert auth.SESSION_EXPIRED_MESSAGE in session_state.values()  # queued toast


def test_refresh_for_guest_is_true(session_state):
    assert auth.refresh_session() is True


def test_refresh_returning_no_session_is_a_failure(session_state, fake_client):
    auth.sign_in("customer@example.test", DEMO_PASSWORD)
    expire_tokens(session_state)
    fake_client.auth.refresh_session = lambda token: SimpleNamespace(session=None)

    assert auth.refresh_session() is False


def test_sign_in_merges_guest_cart(session_state, monkeypatch):
    merged = []
    monkeypatch.setattr(
        cart, "merge_guest_cart", lambda user_id: merged.append(user_id) or ActionResult(ok=True)
    )
    result = auth.sign_in("customer@example.test", DEMO_PASSWORD)

    assert result.ok
    assert merged == [auth.current_user().id]


def test_cart_merge_failure_never_blocks_sign_in(session_state, monkeypatch):
    def broken(user_id):
        raise RuntimeError("cart table down")

    monkeypatch.setattr(cart, "merge_guest_cart", broken)

    assert auth.sign_in("customer@example.test", DEMO_PASSWORD).ok
    assert auth.current_user() is not None


def test_reload_current_user_reads_new_xp(session_state, fake_client):
    auth.sign_in("customer@example.test", DEMO_PASSWORD)
    row = next(p for p in fake_client.tables["profiles"] if p["email"] == "customer@example.test")
    row["xp_total"], row["level"] = 175, 2

    user = auth.reload_current_user()

    assert (user.xp_total, user.level) == (175, 2)


# ---------------------------------------------------------------- review fixes
def test_register_merges_guest_cart(session_state, monkeypatch):
    # A guest fills the cart, goes to checkout and creates an account (US-401, US-306).
    merged = []
    monkeypatch.setattr(
        cart, "merge_guest_cart", lambda user_id: merged.append(user_id) or ActionResult(ok=True)
    )
    result = auth.register("New Learner", "new@example.test", "Abcdefg1", "Abcdefg1")

    assert result.ok
    assert merged == [auth.current_user().id]
    assert result.data["cart_warning"] == ""


def test_register_with_real_guest_cart_keeps_courses(session_state, fake_client):
    session_state[cart.GUEST_CART_KEY] = {101: 2}
    result = auth.register("New Learner", "new@example.test", "Abcdefg1", "Abcdefg1")

    assert result.ok
    user_id = auth.current_user().id
    saved = [row for row in fake_client.tables["cart_items"] if row["user_id"] == user_id]
    assert [(row["course_id"], row["quantity"]) for row in saved] == [(101, 2)]


def test_cart_merge_failure_message_is_shown(session_state, monkeypatch):
    failed = ActionResult(ok=False, message="Some courses could not be saved.")
    monkeypatch.setattr(cart, "merge_guest_cart", lambda user_id: failed)

    signed_in = auth.sign_in("customer@example.test", DEMO_PASSWORD)
    assert signed_in.ok
    assert "Some courses could not be saved." in signed_in.message


def test_register_welcome_names_real_rewards(session_state, fake_client):
    original_sign_up = fake_client.auth.sign_up

    def sign_up_with_badge(credentials):
        response = original_sign_up(credentials)  # the fake trigger gives +50 XP
        fake_client.tables["user_badges"].append(
            {"user_id": response.user.id, "badge_code": "first_step"}
        )
        return response

    fake_client.auth.sign_up = sign_up_with_badge
    result = auth.register("New Learner", "new@example.test", "Abcdefg1", "Abcdefg1")

    assert "First Step badge" in result.message
    assert "+50 XP" in result.message


def test_sign_out_is_local_only(session_state, fake_client):
    # "global" would sign out every student sharing the same demo account.
    auth.sign_in("customer@example.test", DEMO_PASSWORD)
    auth.sign_out()
    assert fake_client.auth.sign_out_options == {"scope": "local"}


def test_welcome_message_escapes_markdown(session_state, fake_client):
    row = next(p for p in fake_client.tables["profiles"] if p["email"] == "customer@example.test")
    row["display_name"] = "*bold*"
    result = auth.sign_in("customer@example.test", DEMO_PASSWORD)
    assert r"\*bold\*" in result.message
