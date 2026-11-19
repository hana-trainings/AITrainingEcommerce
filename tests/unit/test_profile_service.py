"""Unit tests for app/services/profile.py (US-504, US-601 AC2, US-605)."""

from app.models.domain import CurrentUser
from app.services import auth, profile
from tests.conftest import CUSTOMER_ID, FakeAuthError


def sign_in_customer(session_state: dict) -> None:
    session_state[auth.CURRENT_USER_KEY] = CurrentUser(
        id=CUSTOMER_ID, email="customer@example.test", display_name="Casey", role="customer"
    )


def my_row(fake_client) -> dict:
    return next(row for row in fake_client.tables["profiles"] if row["id"] == CUSTOMER_ID)


def test_get_my_profile_returns_own_row(session_state):
    sign_in_customer(session_state)
    my_profile = profile.get_my_profile()
    assert my_profile["display_name"] == "Casey Customer"
    assert my_profile["interests"] == []


def test_get_my_profile_for_guest_is_none(session_state):
    assert profile.get_my_profile() is None


def test_update_profile_saves_and_claims_reward(session_state, fake_client):
    sign_in_customer(session_state)
    fake_client.rpc_results["claim_profile_completion"] = {
        "xp_awarded": 25, "new_level": 2, "level_up": False, "new_badges": ["identity_set"],
    }  # fmt: skip

    result = profile.update_profile("  Casey C  ", "bolt", ["Data Analytics"])

    assert result.ok
    assert result.data["xp_awarded"] == 25
    assert result.data["new_badges"] == ["identity_set"]
    row = my_row(fake_client)
    assert (row["display_name"], row["avatar"], row["interests"]) == (
        "Casey C", "bolt", ["Data Analytics"],
    )  # fmt: skip
    assert ("claim_profile_completion", {}) in fake_client.rpc_calls
    assert auth.current_user().display_name == "Casey C"


def test_update_profile_rejects_photo_or_unknown_avatar_and_too_many_interests(
    session_state, fake_client
):
    sign_in_customer(session_state)

    result = profile.update_profile(
        "Casey", "https://example.test/me.jpg", list(profile.INTEREST_CHOICES)
    )

    assert not result.ok
    assert set(result.data["errors"]) == {"avatar", "interests"}
    assert my_row(fake_client)["avatar"] == "rocket"  # nothing saved
    assert fake_client.rpc_calls == []


def test_update_profile_needs_at_least_one_preset_interest(session_state):
    sign_in_customer(session_state)
    no_interests = profile.update_profile("Casey", "bolt", [])
    free_text = profile.update_profile("Casey", "bolt", ["Cooking"])  # not a preset choice

    assert "interests" in no_interests.data["errors"]
    assert "interests" in free_text.data["errors"]


def test_update_profile_guest_is_refused(session_state):
    assert not profile.update_profile("Casey", "bolt", ["Data Analytics"]).ok


def test_claim_when_already_claimed_gives_no_message(session_state, fake_client):
    sign_in_customer(session_state)
    fake_client.rpc_results["claim_profile_completion"] = {
        "xp_awarded": 0, "new_level": 2, "level_up": False, "new_badges": [],
    }  # fmt: skip
    result = profile.claim_profile_completion()
    assert result.ok
    assert result.message == ""


def test_claim_incomplete_profile_maps_error(session_state, fake_client):
    sign_in_customer(session_state)
    fake_client.rpc_results["claim_profile_completion"] = FakeAuthError(
        "PROFILE_INCOMPLETE: choose an avatar and 1 to 3 interests", code="P0001"
    )
    result = profile.claim_profile_completion()
    assert not result.ok
    assert result.message == profile.PROFILE_INCOMPLETE


def test_reduce_motion_round_trip(session_state, fake_client):
    sign_in_customer(session_state)
    assert profile.get_reduce_motion() is False

    assert profile.set_reduce_motion(True).ok

    assert my_row(fake_client)["reduce_motion"] is True
    assert profile.get_reduce_motion() is True


def test_reduce_motion_guest_defaults_to_false(session_state):
    assert profile.get_reduce_motion() is False
    assert not profile.set_reduce_motion(True).ok
