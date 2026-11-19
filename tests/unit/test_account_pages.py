"""AppTest tests for the account and admin pages (U3 track): register, sign-in expiry
message, Learner Passport, admin dashboard, courses, course form, categories &
paths, and staff management.

Each page is rendered for the right role, and the wrong role is denied.
orders.get_owned_course_ids (another track) is replaced by a simple fake.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.models.domain import CurrentUser
from app.services import auth, orders
from app.services.auth import CURRENT_USER_KEY
from app.services.supabase_client import CLIENT_SESSION_KEY
from tests.conftest import CUSTOMER_ID, OWNER_ID, STAFF_ID

APP_FILE = str(Path(__file__).resolve().parents[2] / "app" / "streamlit_app.py")


@pytest.fixture(autouse=True)
def other_tracks(monkeypatch):
    monkeypatch.setattr(orders, "get_owned_course_ids", lambda user_id: {101})


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
            *at.title, *at.subheader, *at.markdown, *at.info, *at.error,
            *at.warning, *at.success, *at.caption,
        )
    ]  # fmt: skip
    return " ".join(str(part) for part in parts)


def denied(at: AppTest) -> bool:
    return "You don't have access" in all_text(at)


# ---------------------------------------------------------------- register (US-501)
def test_register_page_shows_fields_reward_and_privacy_hint(app):
    open_page(app, "views/register.py")

    assert not app.exception
    assert [box.label for box in app.text_input] == [
        "Display name", "Email", "Password", "Confirm password",
    ]  # fmt: skip
    text = all_text(app)
    assert "+ 50 XP" in text
    assert "test or training email" in text


def test_register_shows_inline_errors(app):
    open_page(app, "views/register.py")
    app.text_input[0].input("Newbie")
    app.text_input[1].input("not-an-email")
    app.text_input[2].input("Abcdefg1")
    app.text_input[3].input("Different1")
    app.button[0].click().run()

    assert not app.exception
    errors = [box.value for box in app.error]
    assert "Enter a valid email address." in errors
    assert "The passwords do not match." in errors
    assert CURRENT_USER_KEY not in app.session_state


def test_register_success_signs_in_as_customer(app):
    open_page(app, "views/register.py")
    app.text_input[0].input("Newbie")
    app.text_input[1].input("newbie@example.test")
    app.text_input[2].input("Abcdefg1")
    app.text_input[3].input("Abcdefg1")
    app.button[0].click().run()

    assert not app.exception
    user = app.session_state[CURRENT_USER_KEY]
    assert (user.display_name, user.role) == ("Newbie", "customer")


def test_register_duplicate_email_is_generic(app):
    open_page(app, "views/register.py")
    app.text_input[0].input("Someone")
    app.text_input[1].input("customer@example.test")
    app.text_input[2].input("Abcdefg1")
    app.text_input[3].input("Abcdefg1")
    app.button[0].click().run()

    assert auth.DUPLICATE_EMAIL_ERROR in [box.value for box in app.error]


def test_register_waiting_for_email_confirmation_is_info_not_error(app, fake_client, monkeypatch):
    # "Confirm email" ON in Supabase: the account is created but there is no session yet.
    real_sign_up = fake_client.auth.sign_up

    def sign_up_without_session(credentials):
        response = real_sign_up(credentials)
        response.session = None
        return response

    monkeypatch.setattr(fake_client.auth, "sign_up", sign_up_without_session)
    open_page(app, "views/register.py")
    app.text_input[0].input("Newbie")
    app.text_input[1].input("newbie@example.test")
    app.text_input[2].input("Abcdefg1")
    app.text_input[3].input("Abcdefg1")
    app.button[0].click().run()

    assert not app.exception
    assert auth.CONFIRM_EMAIL_MESSAGE in [box.value for box in app.info]
    assert auth.CONFIRM_EMAIL_MESSAGE not in [box.value for box in app.error]


def test_sign_in_page_explains_expired_session(app):
    app.session_state[auth.SESSION_EXPIRED_KEY] = True
    open_page(app, "views/sign_in.py")

    assert auth.SESSION_EXPIRED_MESSAGE in [box.value for box in app.warning]


# ---------------------------------------------------------------- passport (US-504, 601, 603)
def test_passport_guest_is_asked_to_sign_in(app):
    open_page(app, "views/passport.py")
    assert "Please sign in" in all_text(app)


def test_passport_shows_profile_badges_paths_and_courses(app, fake_client):
    fake_client.tables["badges"] = [
        {"code": "first_step", "name": "First Step", "description": "Registered.",
         "icon": "👣", "hint": "Create an account to unlock", "sort_order": 1},
        {"code": "collector", "name": "Collector", "description": "Own 5 courses.",
         "icon": "📚", "hint": "Own 5 different courses to unlock", "sort_order": 5},
    ]  # fmt: skip
    fake_client.tables["user_badges"] = [{"user_id": CUSTOMER_ID, "badge_code": "first_step"}]
    fake_client.tables["xp_events"] = [
        {"id": 1, "user_id": CUSTOMER_ID, "action": "register", "points": 50,
         "reference_id": 0, "created_at": "2026-11-01T09:00:00+00:00"},
    ]  # fmt: skip
    sign_in_as(app, CUSTOMER_ID, "customer")
    open_page(app, "views/passport.py")

    assert not app.exception
    text = all_text(app)
    assert "Casey Customer" in text
    assert "1 of 2 earned" in text
    assert "Own 5 different courses to unlock" in text  # locked badge shows its hint
    assert "1 of 2 unlocked" in text  # path progress
    assert app.toggle[0].label == "Reduce motion"


def test_passport_save_claims_reward(app, fake_client):
    fake_client.rpc_results["claim_profile_completion"] = {
        "xp_awarded": 25, "new_level": 2, "level_up": False, "new_badges": ["identity_set"],
    }  # fmt: skip
    sign_in_as(app, CUSTOMER_ID, "customer")
    open_page(app, "views/passport.py")
    app.get("button_group")[1].set_value(["Data Analytics"])  # interests pills
    save = next(button for button in app.button if button.label == "Save details")
    save.click().run()

    assert not app.exception
    assert ("claim_profile_completion", {}) in fake_client.rpc_calls
    row = next(p for p in fake_client.tables["profiles"] if p["id"] == CUSTOMER_ID)
    assert row["interests"] == ["Data Analytics"]


# ---------------------------------------------------------------- admin access (US-701)
ADMIN_PAGES = [
    "views/admin_dashboard.py",
    "views/admin_courses.py",
    "views/admin_course_form.py",
    "views/admin_categories_paths.py",
    "views/admin_emails.py",
    "views/admin_staff.py",  # keep LAST: owner only (see test_staff_opens_admin_pages)
]


@pytest.mark.parametrize("page", ADMIN_PAGES)
def test_customer_is_denied_every_admin_page(app, page):
    sign_in_as(app, CUSTOMER_ID, "customer")
    open_page(app, page)
    assert not app.exception
    assert denied(app)


@pytest.mark.parametrize("page", ADMIN_PAGES[:-1])
def test_staff_opens_admin_pages(app, page):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, page)
    assert not app.exception
    assert not denied(app)


def test_staff_cannot_open_staff_management(app):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, "views/admin_staff.py")
    assert denied(app)


# ---------------------------------------------------------------- dashboard (US-708)
def test_dashboard_shows_kpis(app):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, "views/admin_dashboard.py")

    labels = {metric.label: metric.value for metric in app.metric}
    assert labels["Total orders"] == "1"
    assert labels["Revenue (demo)"] == "$49.00"
    assert labels["Customers"] == "1"


# ---------------------------------------------------------------- courses (US-702, 705, 706, 710)
def test_course_list_publish_button_works(app, fake_client):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, "views/admin_courses.py")
    assert "4 course(s), including drafts." in all_text(app)

    app.selectbox(key="admin_course_selected").set_value(104).run()
    app.button(key="admin_toggle_publish").click().run()

    assert not app.exception
    draft = next(c for c in fake_client.tables["courses"] if c["id"] == 104)
    assert draft["is_published"] is True


def test_course_list_adjust_seats_error_is_shown(app, fake_client):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, "views/admin_courses.py")
    app.selectbox(key="admin_course_selected").set_value(102).run()
    app.number_input[0].set_value(-10)
    reason = next(box for box in app.text_input if box.label == "Reason")
    reason.input("Smaller room")
    next(b for b in app.button if b.label == "Save seat change").click().run()

    assert not app.exception
    assert any("already sold" in box.value for box in app.error)


def test_delete_is_only_offered_to_owner(app):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, "views/admin_courses.py")
    assert "Delete course" not in [exp.label for exp in app.expander]


def test_owner_sees_delete(app):
    sign_in_as(app, OWNER_ID, "owner")
    open_page(app, "views/admin_courses.py")
    assert "Delete course" in [exp.label for exp in app.expander]


# ---------------------------------------------------------------- course form (US-703, 704)
def test_new_course_form_validates_required_fields(app, fake_client):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, "views/admin_course_form.py")
    assert "New course" in all_text(app)

    before = len(fake_client.tables["courses"])
    next(b for b in app.button if b.label == "Save as draft").click().run()

    assert not app.exception
    assert "Enter a title." in [box.value for box in app.error]
    assert len(fake_client.tables["courses"]) == before


def test_edit_course_form_shows_last_updated_by(app, fake_client):
    course = next(c for c in fake_client.tables["courses"] if c["id"] == 101)
    course["updated_by"], course["updated_at"] = STAFF_ID, "2026-11-10T08:30:00+00:00"
    sign_in_as(app, STAFF_ID, "staff")
    app.query_params["course_id"] = "101"
    open_page(app, "views/admin_course_form.py")

    assert not app.exception
    assert "Last updated by Sam Staff at 2026-11-10 08:30 UTC." in all_text(app)
    assert app.text_input[0].value == "Python for Data Beginners"


def test_edit_unknown_course_is_not_found(app):
    sign_in_as(app, STAFF_ID, "staff")
    app.query_params["course_id"] = "999"
    open_page(app, "views/admin_course_form.py")
    assert "Course not found." in [box.value for box in app.warning]


# ---------------------------------------------------------------- categories & paths (US-711)
def test_categories_page_lists_and_saves(app, fake_client):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, "views/admin_categories_paths.py")
    assert "Data Analyst Path" in all_text(app)

    name = next(box for box in app.text_input if box.label == "Name")
    name.input("Robotics")
    next(b for b in app.button if b.label == "Save category").click().run()

    assert not app.exception
    assert "Robotics" in [c["name"] for c in fake_client.tables["categories"]]


# ---------------------------------------------------------------- staff (US-709)
def test_owner_sees_user_list_and_owner_guard(app):
    sign_in_as(app, OWNER_ID, "owner")
    open_page(app, "views/admin_staff.py")

    assert not app.exception
    app.selectbox(key="staff_user_picker").set_value(OWNER_ID).run()
    assert "managed by the trainer" in all_text(app)
    app.selectbox(key="staff_user_picker").set_value(CUSTOMER_ID).run()
    assert "Make staff" in [button.label for button in app.button]


# ---------------------------------------------------------------- email drafts
def test_staff_reads_email_drafts(app, fake_client):
    fake_client.tables["email_outbox"].append(
        {
            "id": 7,
            "email_type": "welcome",
            "status": "draft",
            "order_id": None,
            "user_id": CUSTOMER_ID,
            "to_email": "customer@example.test",
            "subject": "Welcome to SkillForge Academy",
            "html_body": "<p>Hi Casey, welcome aboard!</p><a href='https://x'>x</a>",
            "file_name": "welcome_x.html",
            "created_at": "2026-11-18T10:00:00+00:00",
        }
    )
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, "views/admin_emails.py")

    assert not app.exception
    assert "Welcome to SkillForge Academy" in all_text(app)
    previews = [element.proto.body for element in app.get("html")]
    assert any("welcome aboard" in body for body in previews)
    assert not any("href" in body for body in previews)  # links in a draft are inert


def test_email_drafts_empty_state(app):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, "views/admin_emails.py")

    assert not app.exception
    assert "No email drafts yet" in all_text(app)
