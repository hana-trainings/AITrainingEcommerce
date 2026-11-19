"""AppTest tests for the Storefront pages: Home, Courses, Course detail, Learning paths,
and the header (U1-03 to U1-18).

All four pages are PUBLIC, so the "wrong role" check is that guests see no
owned states and no drafts, while staff may preview a draft (not for sale).
Guests DO see "In cart" for courses in their session cart.
Other areas' services (cart, orders, gamification) are replaced with simple
stand-ins so these tests only check the Storefront.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.components import header
from app.models.domain import ActionResult, CurrentUser
from app.services import cart, gamification, orders
from app.services.auth import CURRENT_USER_KEY
from app.services.supabase_client import CLIENT_SESSION_KEY
from tests.conftest import CUSTOMER_ID, STAFF_ID

APP_FILE = str(Path(__file__).resolve().parents[2] / "app" / "streamlit_app.py")
HOME = "views/home.py"
COURSES = "views/courses.py"
DETAIL = "views/course_detail.py"
PATHS = "views/learning_paths.py"

MODULES = [
    {"id": 1, "course_id": 102, "position": 1, "title": "Select basics", "description": "Rows."},
    {"id": 2, "course_id": 102, "position": 2, "title": "Joins", "description": "Secret."},
]


@pytest.fixture
def services(monkeypatch):
    """Stand-ins for the cart, orders and gamification services. Tests can change them."""
    calls = {"added": []}
    state = {"owned": set(), "cart": [], "count": 0}

    def add_item(course_id, quantity=1):
        calls["added"].append(course_id)
        return ActionResult(ok=True, message="Added to your cart.")

    monkeypatch.setattr(cart, "add_item", add_item)
    monkeypatch.setattr(
        cart, "get_cart_course_ids", lambda: {line["course_id"] for line in state["cart"]}
    )
    monkeypatch.setattr(cart, "get_item_count", lambda: state["count"])
    monkeypatch.setattr(orders, "get_owned_course_ids", lambda user_id: state["owned"])
    monkeypatch.setattr(
        gamification,
        "get_level_progress",
        lambda xp: {
            "level": 2,
            "name": "Explorer",
            "xp_total": xp,
            "level_start_xp": 150,
            "next_level_xp": 400,
            "next_level_name": "Practitioner",
        },
    )
    return {"calls": calls, "state": state}


@pytest.fixture
def app(fake_client, services) -> AppTest:
    fake_client.tables["course_modules"] = [dict(module) for module in MODULES]
    at = AppTest.from_file(APP_FILE, default_timeout=30)
    at.secrets["SUPABASE_URL"] = "https://example.supabase.co"
    at.secrets["SUPABASE_PUBLISHABLE_KEY"] = "sb_publishable_test"
    at.session_state[CLIENT_SESSION_KEY] = fake_client
    return at


def sign_in_as(at: AppTest, user_id: str, role: str, xp_total: int = 0) -> None:
    at.session_state[CURRENT_USER_KEY] = CurrentUser(
        id=user_id,
        email=f"{role}@example.test",
        display_name=role.title(),
        role=role,
        xp_total=xp_total,
    )


def open_page(at: AppTest, page: str, course: str | None = None) -> AppTest:
    """Open a page. Home is the default page, so it needs no switch.

    Note: after AppTest.switch_page() AppTest only keeps the PAGE's elements, not
    the header drawn by streamlit_app.py before it, so header checks use Home.
    """
    at.run()
    if course is not None:
        at.query_params["course"] = course
    if page != HOME:
        at.switch_page(page).run()
    assert not at.exception
    return at


def all_text(at: AppTest) -> str:
    parts = [
        element.value
        for element in (
            *at.title,
            *at.header,
            *at.subheader,
            *at.markdown,
            *at.info,
            *at.warning,
            *at.success,
            *at.error,
            *at.caption,
        )
    ]
    parts += [str(link.proto.label) for link in at.get("page_link")]
    parts += [str(bar.proto.text) for bar in at.get("progress")]
    # The seat meter draws its "8 of 30 seats left" label as HTML (seat_meter.py).
    parts += [str(block.proto.body) for block in at.get("html")]
    parts += [button.label for button in at.button]
    return " ".join(str(part) for part in parts)


def card_titles(at: AppTest) -> list[str]:
    return [link.proto.label for link in at.get("page_link") if link.proto.label.startswith("**")]


# ---------------------------------------------------------------- Courses (US-101 to US-105)
def test_courses_page_lists_published_courses_for_guest(app):
    open_page(app, COURSES)

    text = all_text(app)
    assert "3 courses" in text
    assert "Intro to Neural Networks" not in text  # draft hidden (US-101 AC1)
    assert "22 of 30 seats left" in text  # seat meter on the card (AC2)
    sold_out = [button for button in app.button if button.label == "Sold out"]
    assert sold_out and sold_out[0].disabled  # AC3


def test_keyword_search_shows_count_and_keeps_the_term(app):
    open_page(app, COURSES)
    app.text_input(key="catalog_keyword_box").input("  sql ")
    app.button[0].click().run()  # the form's Search button

    assert not app.exception
    assert "1 result for 'sql'" in all_text(app)
    assert app.text_input(key="catalog_keyword_box").value == "  sql "


def test_no_results_shows_help_and_clear_filters_resets(app):
    open_page(app, COURSES)
    app.text_input(key="catalog_keyword_box").input("underwater basket weaving")
    app.button[0].click().run()

    text = all_text(app)
    assert "No courses match your search" in text
    assert "You might like these" in text  # suggested courses (US-105)
    assert len(card_titles(app)) == 3

    app.button(key="no_results_clear").click().run()
    assert "3 courses" in all_text(app)
    assert app.text_input(key="catalog_keyword_box").value == ""


def test_filters_show_chips_and_chips_can_be_removed(app):
    open_page(app, COURSES)
    app.toggle(key="catalog_only_available").set_value(True).run()

    assert "2 courses" in all_text(app)
    chip = app.button(key="chip_catalog_only_available")
    assert chip.label == "Only available"
    chip.click().run()
    assert "3 courses" in all_text(app)


def test_sort_by_price(app):
    open_page(app, COURSES)
    app.selectbox(key="catalog_sort").select("price_desc").run()

    assert not app.exception
    assert card_titles(app)[0] == "**SQL for Analysts**"


def test_add_to_cart_from_card_calls_the_cart(app, services):
    open_page(app, COURSES)
    app.button(key="results_add_101").click().run()

    assert not app.exception
    assert services["calls"]["added"] == [101]


def test_add_to_cart_refused_shows_the_reason(app, monkeypatch):
    monkeypatch.setattr(
        cart, "add_item", lambda course_id, quantity=1: ActionResult(ok=False, message="Sold out.")
    )
    open_page(app, DETAIL, course="python-for-data-beginners")
    app.button(key="detail_add").click().run()

    assert not app.exception
    assert "Sold out." in all_text(app)


def test_add_to_cart_error_shows_generic_message(app, monkeypatch):
    def broken(course_id, quantity=1):
        raise RuntimeError("database down")

    monkeypatch.setattr(cart, "add_item", broken)
    open_page(app, DETAIL, course="python-for-data-beginners")
    app.button(key="detail_add").click().run()

    assert "Something went wrong, please try again." in all_text(app)
    assert "database down" not in all_text(app)  # no technical details (NFR-SEC-17)


def test_add_to_cart_on_home_queues_toast_for_the_rerun(app, services):
    open_page(app, HOME)
    services["state"]["count"] = 1  # what the cart will report after adding
    app.button(key="featured_add_101").click().run()

    assert not app.exception
    assert services["calls"]["added"] == [101]
    # The toast is queued with flash(); the header shows it on the st.rerun()
    # together with the new cart count, and removes it from the queue.
    assert [toast.value for toast in app.toast] == ["Added to your cart."]
    assert "flash_message" not in app.session_state


# ---------------------------------------------------------------- Course detail (US-201 to US-205)
def test_course_detail_for_guest_shows_details_and_locked_modules(app):
    open_page(app, DETAIL, course="sql-for-analysts")

    text = all_text(app)
    assert "SQL for Analysts" in text
    assert "Instructor: Bo Query" in text
    assert "3 of 30 seats left" in text and "Few seats left" in text  # US-203
    assert "Course 2 of 2 in Data Analyst Path" in text  # US-201 AC3
    assert "Rows" in text  # module 1 description is visible (US-202 AC1)
    assert "Secret" not in text  # module 2 description is locked (AC2)
    assert "Unlock with this course" in text
    assert "Related courses" in text  # US-205


def test_course_detail_owned_course_unlocks_all_modules(app, services):
    sign_in_as(app, CUSTOMER_ID, "customer")
    services["state"]["owned"] = {102}
    open_page(app, DETAIL, course="sql-for-analysts")

    text = all_text(app)
    assert "All modules are unlocked" in text  # US-202 AC3
    assert "Secret" in text
    with pytest.raises(KeyError):
        app.button(key="detail_add")  # no "Add to cart" for an owned course


def test_course_detail_add_to_cart(app, services):
    open_page(app, DETAIL, course="python-for-data-beginners")
    app.button(key="detail_add").click().run()

    assert services["calls"]["added"] == [101]


def test_course_detail_in_cart_state(app, services):
    sign_in_as(app, CUSTOMER_ID, "customer")
    services["state"]["cart"] = [{"course_id": 101}]
    open_page(app, DETAIL, course="python-for-data-beginners")

    assert "In cart · View cart" in all_text(app)


def test_sold_out_detail_has_disabled_button(app):
    open_page(app, DETAIL, course="prompt-engineering-fundamentals")

    sold_out = [button for button in app.button if button.label == "Sold out"]
    assert sold_out[0].disabled


def test_draft_course_is_not_found_for_guest_and_customer(app):
    open_page(app, DETAIL, course="neural-networks-draft")
    assert "Course not found" in all_text(app)

    sign_in_as(app, CUSTOMER_ID, "customer")
    open_page(app, DETAIL, course="neural-networks-draft")
    assert "Course not found" in all_text(app)


def test_staff_can_preview_a_draft(app):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, DETAIL, course="neural-networks-draft")

    assert "Draft preview" in all_text(app)


def test_missing_course_parameter_shows_not_found(app):
    open_page(app, DETAIL)
    assert "Course not found" in all_text(app)


# ---------------------------------------------------------------- Home (US-106)
def test_home_for_guest_shows_hero_featured_and_almost_full(app):
    open_page(app, HOME)

    text = all_text(app)
    assert "Unlock your AI & Data skills" in text
    assert "Featured courses" in text
    assert "Almost full" in text  # SQL really has 3 seats left
    assert "Sign up to start earning XP" in text  # header hint for guests


def test_home_hides_almost_full_when_no_course_is_nearly_full(app, fake_client):
    for course in fake_client.tables["courses"]:
        course["seats_available"] = course["seats_total"]
    open_page(app, HOME)

    assert "Almost full" not in all_text(app)  # never fake scarcity (US-606)


def test_home_signed_in_shows_welcome_and_next_in_path(app, services):
    sign_in_as(app, CUSTOMER_ID, "customer", xp_total=150)
    services["state"]["owned"] = {101}
    open_page(app, HOME)

    text = all_text(app)
    assert "Welcome back, Customer" in text
    assert "Next in your path" in text
    assert "SQL for Analysts" in text  # the next not-owned step of the started path


def test_page_shows_store_unavailable_when_database_fails(app, fake_client):
    def broken_table(_name):
        raise ConnectionError("network down")

    fake_client.table = broken_table
    open_page(app, COURSES)

    assert "temporarily unavailable" in all_text(app)


# ---------------------------------------------------------------- Learning paths (US-604)
def test_learning_paths_page_for_guest(app):
    open_page(app, PATHS)

    text = all_text(app)
    assert "Data Analyst Path" in text
    assert "0 of 2 unlocked · +250 XP bonus" in text  # AC2
    # Each step shows its position and the full course title (never cut off).
    assert "Step 1 of 2" in text and "Python for Data Beginners" in text
    assert "View course" in text  # nodes link to the course (AC3)
    assert "Total $128.00" in text


def test_learning_paths_page_uses_owned_and_cart_states(app, services, monkeypatch):
    sign_in_as(app, CUSTOMER_ID, "customer")
    services["state"]["owned"] = {101}
    services["state"]["cart"] = [{"course_id": 102}]
    seen = {}

    def build_path_nodes(path, owned_ids, cart_ids):
        seen["args"] = (owned_ids, cart_ids)
        states = {101: "owned", 102: "in_cart"}
        return [
            {"course_id": c["id"], "slug": c["slug"], "title": c["title"], "state": states[c["id"]]}
            for c in path["courses"]
        ]

    monkeypatch.setattr(gamification, "build_path_nodes", build_path_nodes)
    open_page(app, PATHS)

    assert seen["args"] == ({101}, {102})
    assert "1 of 2 unlocked" in all_text(app)


# ---------------------------------------------------------------- Header (US-602, US-301 AC3)
def test_header_shows_level_chip_xp_bar_and_cart_count(app, services):
    sign_in_as(app, CUSTOMER_ID, "customer", xp_total=200)
    services["state"]["count"] = 2
    open_page(app, HOME)

    text = all_text(app)
    assert "Cart (2)" in text
    assert "200 / 400 XP" in text  # XP bar to the next level (US-602 AC1)
    badges = " ".join(str(element.value) for element in app.markdown)
    assert "Level 2 · Explorer" in badges


def test_header_survives_broken_services(app, monkeypatch):
    def broken(*_args):
        raise RuntimeError("service down")

    monkeypatch.setattr(cart, "get_item_count", broken)
    monkeypatch.setattr(gamification, "get_level_progress", broken)
    sign_in_as(app, CUSTOMER_ID, "customer")
    open_page(app, HOME)

    assert "Cart (0)" in all_text(app)
    assert "Welcome back, Customer" in all_text(app)  # the page itself still works


def test_header_runs_on_a_non_home_page(app, services, monkeypatch):
    """The header is drawn by streamlit_app.py on EVERY page, not only Home.

    AppTest keeps only the page's own elements after switching pages (the real
    app shows the header; checked with the running app), so this test spies on
    render_header and on the cart count it draws.
    """
    real_render_header = header.render_header
    seen = {"users": [], "labels": []}

    def spy_render_header(user, **options):
        seen["users"].append(user)
        real_render_header(user, **options)

    real_cart_label = header.cart_label
    monkeypatch.setattr(header, "render_header", spy_render_header)
    monkeypatch.setattr(
        header, "cart_label", lambda count: seen["labels"].append(count) or real_cart_label(count)
    )
    sign_in_as(app, CUSTOMER_ID, "customer")
    services["state"]["count"] = 2
    open_page(app, COURSES)

    assert app.title[0].value == "Courses"
    assert seen["users"][-1].id == CUSTOMER_ID  # header drawn on the Courses run
    assert seen["labels"][-1] == 2  # with the real cart count


# ---------------------------------------------------------------- review fixes
def test_guest_sees_in_cart_state_and_cannot_add_twice(app, services):
    services["state"]["cart"] = [{"course_id": 101}]  # the guest's session cart
    open_page(app, COURSES)

    assert "In cart · View cart" in all_text(app)
    with pytest.raises(KeyError):
        app.button(key="results_add_101")  # no second silent "Add to cart"
    assert app.button(key="results_add_102")  # other courses can still be added


def test_guest_in_cart_state_on_detail_page(app, services):
    services["state"]["cart"] = [{"course_id": 101}]
    open_page(app, DETAIL, course="python-for-data-beginners")

    assert "In cart · View cart" in all_text(app)
    with pytest.raises(KeyError):
        app.button(key="detail_add")


def test_page_past_the_end_jumps_back_to_last_page(app):
    open_page(app, COURSES)
    app.session_state["catalog_page"] = 5  # e.g. courses were unpublished meanwhile
    app.run()

    assert not app.exception
    assert len(card_titles(app)) == 3  # page 1 of 1, not an empty grid
    assert app.session_state["catalog_page"] == 1


def test_staff_draft_preview_is_not_for_sale(app):
    sign_in_as(app, STAFF_ID, "staff")
    open_page(app, DETAIL, course="neural-networks-draft")

    draft_button = app.button(key="detail_draft")
    assert draft_button.label == "Draft: not for sale"
    assert draft_button.disabled
    with pytest.raises(KeyError):
        app.button(key="detail_add")


def test_learning_path_shows_real_badge_name(app, fake_client):
    fake_client.tables["badges"] = [
        {"code": "path_master_data_analyst", "name": "Data Detective", "description": "d"}
    ]
    open_page(app, PATHS)

    assert "Badge: Data Detective" in " ".join(str(m.value) for m in app.markdown)


def test_learning_path_without_badge_shows_no_badge(app, fake_client):
    fake_client.tables["learning_paths"][0]["badge_code"] = None
    open_page(app, PATHS)

    assert "Badge:" not in " ".join(str(m.value) for m in app.markdown)
