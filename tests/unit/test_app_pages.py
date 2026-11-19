"""Example Streamlit AppTest tests: run the real app in-process, no browser, no keys.

The trick: AppTest lets us set st.secrets and st.session_state BEFORE the run,
so the app finds fake settings and our fake Supabase client (tests/conftest.py)
instead of the real ones.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.models.domain import CurrentUser
from app.services.auth import CURRENT_USER_KEY
from app.services.supabase_client import CLIENT_SESSION_KEY
from tests.conftest import CUSTOMER_ID, DEMO_PASSWORD, STAFF_ID

APP_FILE = str(Path(__file__).resolve().parents[2] / "app" / "streamlit_app.py")


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


def all_text(at: AppTest) -> str:
    parts = [e.value for e in (*at.title, *at.markdown, *at.info, *at.error, *at.caption)]
    return " ".join(str(part) for part in parts)


def test_home_opens_for_guest(app):
    app.run()
    assert not app.exception
    # Home was a "Coming soon" stub in the foundation; US-106 built the real guest hero.
    assert "Unlock your AI & Data skills" in all_text(app)


def test_sign_in_page_renders(app):
    app.run()
    app.switch_page("views/sign_in.py").run()

    assert not app.exception
    assert [box.label for box in app.text_input] == ["Email", "Password"]
    assert "Ask your trainer" in all_text(app)  # US-505


def test_sign_in_with_wrong_password_shows_generic_error(app):
    app.run()
    app.switch_page("views/sign_in.py").run()
    app.text_input[0].input("customer@example.test")
    app.text_input[1].input("WrongPass1")
    app.button[0].click().run()

    assert not app.exception
    assert app.error[0].value == "Email or password is incorrect."


def test_sign_in_with_right_password_signs_in(app):
    app.run()
    app.switch_page("views/sign_in.py").run()
    app.text_input[0].input("customer@example.test")
    app.text_input[1].input(DEMO_PASSWORD)
    app.button[0].click().run()

    assert not app.exception
    assert app.session_state[CURRENT_USER_KEY].id == CUSTOMER_ID


def test_guest_on_admin_page_sees_access_denied(app):
    app.run()
    app.switch_page("views/admin_dashboard.py").run()

    assert not app.exception
    assert "You don't have access" in all_text(app)
    assert "Coming soon" not in all_text(app)  # no page content leaks


def test_customer_on_admin_page_sees_access_denied(app):
    sign_in_as(app, CUSTOMER_ID, "customer")
    app.run()
    app.switch_page("views/admin_dashboard.py").run()

    assert "You don't have access" in all_text(app)


def test_staff_can_open_admin_page_but_not_staff_management(app):
    sign_in_as(app, STAFF_ID, "staff")
    app.run()
    app.switch_page("views/admin_dashboard.py").run()
    # The dashboard is real now (US-701, US-708): staff see it, not the access-denied state.
    assert "Admin dashboard" in all_text(app)
    assert "You don't have access" not in all_text(app)

    app.switch_page("views/admin_staff.py").run()
    assert "You don't have access" in all_text(app)  # owner only (US-709 AC3)


def test_guest_on_checkout_is_asked_to_sign_in(app):
    app.run()
    app.switch_page("views/checkout.py").run()

    assert not app.exception
    assert "Please sign in" in all_text(app)
