"""Unit tests for app/services/gamification.py (US-601, US-602, US-603, US-604)."""

import pytest

from app.models.domain import CurrentUser
from app.services import auth, gamification, orders
from tests.conftest import CUSTOMER_ID


def sign_in_customer(session_state: dict) -> None:
    session_state[auth.CURRENT_USER_KEY] = CurrentUser(
        id=CUSTOMER_ID, email="customer@example.test", display_name="Casey", role="customer"
    )


# ---------------------------------------------------------------- levels (US-602)
@pytest.mark.parametrize(
    ("xp", "level", "name", "next_xp"),
    [
        (0, 1, "Novice", 150),
        (149, 1, "Novice", 150),
        (150, 2, "Explorer", 400),
        (799, 3, "Practitioner", 800),
        (800, 4, "Expert", 1500),
        (1500, 5, "Master", None),
        (99999, 5, "Master", None),
    ],
)
def test_level_progress_boundaries(xp, level, name, next_xp):
    progress = gamification.get_level_progress(xp)

    assert progress["level"] == level
    assert progress["name"] == name
    assert progress["next_level_xp"] == next_xp


def test_level_progress_top_level_has_no_next_name():
    progress = gamification.get_level_progress(2000)
    assert progress["next_level_name"] is None
    assert progress["level_start_xp"] == 1500


def test_level_progress_negative_xp_is_treated_as_zero():
    progress = gamification.get_level_progress(-10)
    assert progress["xp_total"] == 0
    assert progress["level"] == 1
    assert progress["next_level_name"] == "Explorer"


# ---------------------------------------------------------------- path nodes (US-604)
PATH = {
    "id": 1,
    "name": "Data Analyst Path",
    "courses": [
        {"id": 101, "slug": "python", "title": "Python"},
        {"id": 102, "slug": "sql", "title": "SQL"},
        {"id": 103, "slug": "viz", "title": "Viz"},
    ],
}


def test_build_path_nodes_states_in_order():
    nodes = gamification.build_path_nodes(PATH, owned_course_ids={101}, cart_course_ids={102})

    assert [node["state"] for node in nodes] == ["owned", "in_cart", "locked"]
    assert [node["slug"] for node in nodes] == ["python", "sql", "viz"]


def test_build_path_nodes_owned_wins_over_cart():
    nodes = gamification.build_path_nodes(PATH, owned_course_ids={101}, cart_course_ids={101})
    assert nodes[0]["state"] == "owned"


def test_build_path_nodes_empty_path():
    assert gamification.build_path_nodes({"id": 2, "name": "Empty"}, set(), set()) == []


# ---------------------------------------------------------------- XP history (US-601)
def test_xp_history_newest_first_and_only_mine(session_state, fake_client):
    fake_client.tables["xp_events"] = [
        {"id": 1, "user_id": CUSTOMER_ID, "action": "register", "points": 50,
         "reference_id": 0, "created_at": "2026-11-01T09:00:00+00:00"},
        {"id": 2, "user_id": CUSTOMER_ID, "action": "purchase_course", "points": 100,
         "reference_id": 101, "created_at": "2026-11-02T09:00:00+00:00"},
        {"id": 3, "user_id": "someone-else", "action": "register", "points": 50,
         "reference_id": 0, "created_at": "2026-11-03T09:00:00+00:00"},
    ]  # fmt: skip
    sign_in_customer(session_state)

    events = gamification.list_my_xp_events()

    assert [event["id"] for event in events] == [2, 1]


def test_xp_history_for_guest_is_empty(session_state):
    assert gamification.list_my_xp_events() == []


def test_xp_action_label_known_and_unknown():
    assert gamification.xp_action_label("complete_profile") == "Completed your Learner Passport"
    assert gamification.xp_action_label("something_new") == "Something new"


# ---------------------------------------------------------------- badges (US-603)
BADGES = [
    {"code": "first_step", "name": "First Step", "description": "Registered.", "icon": "👣",
     "hint": "Create an account to unlock", "sort_order": 1},
    {"code": "first_unlock", "name": "First Unlock", "description": "First course.",
     "icon": "🔓", "hint": None, "sort_order": 3},
]  # fmt: skip


def test_badges_show_earned_and_locked_with_hint(session_state, fake_client):
    fake_client.tables["badges"] = [dict(badge) for badge in BADGES]
    fake_client.tables["user_badges"] = [
        {"user_id": CUSTOMER_ID, "badge_code": "first_step", "awarded_at": "2026-11-01"},
        {"user_id": "someone-else", "badge_code": "first_unlock", "awarded_at": "2026-11-01"},
    ]
    sign_in_customer(session_state)

    badges = gamification.list_badges_with_status()

    assert [(b["code"], b["earned"]) for b in badges] == [
        ("first_step", True),
        ("first_unlock", False),
    ]
    assert badges[1]["hint"] == gamification.DEFAULT_BADGE_HINT  # missing hint gets a default


def test_badges_for_guest_are_all_locked(session_state, fake_client):
    fake_client.tables["badges"] = [dict(badge) for badge in BADGES]
    assert not any(badge["earned"] for badge in gamification.list_badges_with_status())


# ---------------------------------------------------------------- path progress (US-504)
def test_path_progress_counts_owned_courses(session_state, monkeypatch):
    sign_in_customer(session_state)
    monkeypatch.setattr(orders, "get_owned_course_ids", lambda user_id: {101})

    progress = gamification.get_path_progress()

    assert len(progress) == 1
    assert progress[0]["owned_count"] == 1
    assert progress[0]["total_count"] == 2
    assert [node["course_id"] for node in progress[0]["nodes"]] == [101, 102]


def test_path_progress_when_owned_service_not_ready(session_state, monkeypatch):
    sign_in_customer(session_state)

    def not_ready(user_id):
        raise NotImplementedError

    monkeypatch.setattr(orders, "get_owned_course_ids", not_ready)
    progress = gamification.get_path_progress()
    assert progress[0]["owned_count"] == 0


def test_owned_courses_list(session_state, monkeypatch):
    sign_in_customer(session_state)
    monkeypatch.setattr(orders, "get_owned_course_ids", lambda user_id: {102, 101})

    titles = [course["title"] for course in gamification.list_my_owned_courses()]

    assert titles == ["Python for Data Beginners", "SQL for Analysts"]


def test_owned_courses_for_guest_is_empty(session_state):
    assert gamification.list_my_owned_courses() == []
