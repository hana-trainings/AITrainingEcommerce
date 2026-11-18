"""Unit tests for app/services/admin.py (Epic E7: US-702 to US-711, U3 track).

The shared fake client does not invent ids on insert (a real database does), so
the `auto_ids` fixture below adds that for the tables with an identity id.
"""

import pytest

from app.models.domain import CourseInput, CurrentUser
from app.services import admin, auth
from tests.conftest import CUSTOMER_ID, OWNER_ID, STAFF_ID, FakeAuthError

IDENTITY_TABLES = {"courses", "categories", "learning_paths", "course_modules", "orders"}

# Smallest valid 1x1 image headers (enough for the type check, never really decoded).
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 20
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 20


def query_class(fake_client) -> type:
    """The FakeQuery class the fixture really uses (pytest may load conftest.py under
    another module name than tests.conftest, so we don't import the class directly)."""
    return type(fake_client.table("courses"))


@pytest.fixture(autouse=True)
def auto_ids(monkeypatch, fake_client):
    """Give inserted rows an id, like Postgres "generated always as identity"."""
    fake_query = query_class(fake_client)
    original = fake_query.execute

    def execute_with_ids(self):
        if self.action == "insert" and self.table_name in IDENTITY_TABLES:
            rows = self.payload if isinstance(self.payload, list) else [self.payload]
            existing = self.client.tables.setdefault(self.table_name, [])
            next_id = max([row.get("id", 0) for row in existing] + [0]) + 1
            for row in rows:
                if "id" not in row:
                    row["id"] = next_id
                    next_id += 1
        return original(self)

    monkeypatch.setattr(fake_query, "execute", execute_with_ids)


def rpc_params(fake_client, name: str) -> dict:
    """Parameters of the last call to the database function `name`."""
    return [params for called, params in fake_client.rpc_calls if called == name][-1]


def sign_in_as(session_state: dict, user_id: str, role: str) -> None:
    session_state[auth.CURRENT_USER_KEY] = CurrentUser(
        id=user_id, email=f"{role}@example.test", display_name=role.title(), role=role
    )


@pytest.fixture
def staff(session_state):
    sign_in_as(session_state, STAFF_ID, "staff")
    return session_state


@pytest.fixture
def owner(session_state):
    sign_in_as(session_state, OWNER_ID, "owner")
    return session_state


@pytest.fixture
def customer(session_state):
    sign_in_as(session_state, CUSTOMER_ID, "customer")
    return session_state


def course_input(**changes) -> CourseInput:
    data = CourseInput(
        title="Data Ethics for Teens",
        slug="",
        summary="Think about fairness in data.",
        description="Bias, privacy and fairness, with friendly examples.",
        category_id=2,
        level="Beginner",
        duration_hours=3,
        price=29,
        seats_total=25,
        instructor_name="Ada Lumen",
        outcomes=["Spot bias", " "],
        prerequisites=[],
        modules=[{"title": "What is bias?", "description": "Examples"}, {"title": "Privacy"}],
        tags=["Ethics"],
        path_positions=[{"path_id": 1, "position": 3}],
        is_featured=False,
    )
    data.update(changes)  # type: ignore[typeddict-item]
    return data


def course_row(fake_client, course_id: int) -> dict:
    return next(row for row in fake_client.tables["courses"] if row["id"] == course_id)


# ---------------------------------------------------------------- US-702 list
def test_list_courses_includes_drafts_and_category_names(staff):
    courses = admin.list_courses()
    assert {course["id"] for course in courses} == {101, 102, 103, 104}
    draft = next(course for course in courses if course["id"] == 104)
    assert draft["category_name"] == "Artificial Intelligence"


def test_list_courses_filters(staff):
    assert [c["id"] for c in admin.list_courses(published=False)] == [104]
    assert {c["id"] for c in admin.list_courses(category_id=1)} == {103, 104}
    assert [c["id"] for c in admin.list_courses(search="sql")] == [102]


def test_list_courses_no_match_is_empty(staff):
    assert admin.list_courses(search="underwater basket weaving") == []


# ---------------------------------------------------------------- US-703 validate + create
def test_validate_course_input_accepts_valid_data():
    assert admin.validate_course_input(course_input()) == {}


def test_validate_course_input_reports_each_field():
    errors = admin.validate_course_input(
        course_input(
            title="",
            summary="x" * 201,
            description="",
            category_id=None,
            level="Expert",
            duration_hours=0,
            price=10000,
            seats_total=0,
        )
    )
    assert set(errors) >= {
        "title", "summary", "description", "category_id", "level",
        "duration_hours", "price", "seats_total",
    }  # fmt: skip


def test_validate_course_input_edges():
    assert admin.validate_course_input(course_input(price=0, seats_total=10000)) == {}
    assert "price" in admin.validate_course_input(course_input(price=-0.01))
    assert "seats_total" in admin.validate_course_input(course_input(seats_total=2.5))
    assert "slug" in admin.validate_course_input(course_input(slug="Bad Slug!"))
    assert "summary" not in admin.validate_course_input(course_input(summary="x" * 200))


def test_slugify():
    assert admin.slugify("SQL for Analysts!") == "sql-for-analysts"
    assert admin.slugify("  --AI & You--  ") == "ai-you"


def test_create_course_sets_seats_available_and_draft(staff, fake_client):
    result = admin.create_course(course_input())

    assert result.ok, result.message
    row = course_row(fake_client, result.data["course_id"])
    assert row["slug"] == "data-ethics-for-teens"
    assert row["seats_available"] == row["seats_total"] == 25  # US-703 AC5
    assert row["is_published"] is False  # AC4
    assert row["outcomes"] == ["Spot bias"]
    assert row["tags"] == ["ethics"]
    # Modules and path steps are saved by ONE database function (migration 0025).
    assert rpc_params(fake_client, "admin_replace_course_children") == {
        "p_course_id": row["id"],
        "p_modules": [
            {"title": "What is bias?", "description": "Examples"},
            {"title": "Privacy", "description": ""},
        ],
        "p_path_positions": [{"path_id": 1, "position": 3}],
    }


def test_create_course_duplicate_slug_is_refused(staff, fake_client):
    before = len(fake_client.tables["courses"])
    result = admin.create_course(course_input(slug="sql-for-analysts"))

    assert not result.ok
    assert result.data["errors"]["slug"] == admin.SLUG_TAKEN
    assert len(fake_client.tables["courses"]) == before


def test_create_course_validates_on_the_server(staff, fake_client):
    result = admin.create_course(course_input(price=50000))
    assert not result.ok
    assert "price" in result.data["errors"]


def test_create_course_customer_is_refused(customer, fake_client):
    before = len(fake_client.tables["courses"])
    assert admin.create_course(course_input()).message == admin.STAFF_ONLY
    assert len(fake_client.tables["courses"]) == before


# ---------------------------------------------------------------- US-705 publish
def test_publish_and_unpublish(staff, fake_client):
    assert admin.set_published(104, True).ok
    assert course_row(fake_client, 104)["is_published"] is True
    assert admin.set_published(104, False).ok
    assert course_row(fake_client, 104)["is_published"] is False


def test_publish_unknown_course(staff):
    result = admin.set_published(999, True)
    assert not result.ok
    assert result.message == admin.NOT_FOUND


def test_publish_does_not_touch_orders(staff, fake_client):
    orders_before = [dict(order) for order in fake_client.tables["orders"]]
    admin.set_published(101, False)
    assert fake_client.tables["orders"] == orders_before  # US-705 AC2


def test_publish_customer_is_refused(customer, fake_client):
    assert not admin.set_published(104, True).ok
    assert course_row(fake_client, 104)["is_published"] is False


# ---------------------------------------------------------------- US-706 seats
def test_adjust_seats_adds_seats_and_writes_reason(staff, fake_client):
    result = admin.adjust_seats(101, 5, "Bigger room")

    assert result.ok, result.message
    row = course_row(fake_client, 101)
    assert (row["seats_total"], row["seats_available"]) == (35, 27)
    name, params = fake_client.rpc_calls[-1]
    assert name == "write_audit_log"
    assert params["p_after"]["reason"] == "Bigger room"
    assert params["p_entity_id"] == "101"


def test_adjust_seats_cannot_remove_sold_seats(staff, fake_client):
    # Course 102: 30 total, 3 available, so 27 are sold.
    result = admin.adjust_seats(102, -4, "Smaller room")

    assert not result.ok
    assert "27" in result.message
    assert course_row(fake_client, 102)["seats_available"] == 3


def test_adjust_seats_can_remove_exactly_the_available_seats(staff, fake_client):
    assert admin.adjust_seats(102, -3, "Close sales").ok
    row = course_row(fake_client, 102)
    assert (row["seats_total"], row["seats_available"]) == (27, 0)


def test_adjust_seats_needs_a_reason_and_a_change(staff):
    assert admin.adjust_seats(101, 5, "   ").message == "Enter a reason for the change."
    assert not admin.adjust_seats(101, 0, "Nothing").ok


def test_adjust_seats_above_maximum(staff):
    assert not admin.adjust_seats(101, 10000, "Stadium").ok


def test_check_seat_change_is_pure():
    assert admin.check_seat_change(30, 3, -3) == ""
    assert admin.check_seat_change(30, 3, -4) != ""
    assert admin.check_seat_change(1, 1, -1) != ""  # at least 1 seat in total


def test_audit_failure_does_not_undo_the_seat_change(staff, fake_client):
    fake_client.rpc_results["write_audit_log"] = FakeAuthError("NOT_ALLOWED", code="P0001")
    assert admin.adjust_seats(101, 1, "Extra seat").ok


# ---------------------------------------------------------------- US-710 delete
def test_owner_deletes_course_without_orders(owner, fake_client):
    result = admin.delete_course(104, "Intro to Neural Networks")
    assert result.ok
    assert all(row["id"] != 104 for row in fake_client.tables["courses"])


def test_delete_course_with_orders_suggests_unpublish(owner, fake_client):
    result = admin.delete_course(101, "Python for Data Beginners")
    assert not result.ok
    assert "Unpublish" in result.message
    assert any(row["id"] == 101 for row in fake_client.tables["courses"])


def test_delete_course_title_must_match(owner, fake_client):
    result = admin.delete_course(104, "intro to neural networks")
    assert not result.ok
    assert "does not match" in result.message


def test_staff_cannot_delete(staff, fake_client):
    result = admin.delete_course(104, "Intro to Neural Networks")
    assert not result.ok
    assert any(row["id"] == 104 for row in fake_client.tables["courses"])


def test_delete_foreign_key_error_is_explained(owner, fake_client, monkeypatch):
    original = query_class(fake_client).execute

    def fk_error(self):
        if self.action == "delete" and self.table_name == "courses":
            raise FakeAuthError("violates foreign key constraint", code="23503")
        return original(self)

    monkeypatch.setattr(query_class(fake_client), "execute", fk_error)
    assert admin.delete_course(104, "Intro to Neural Networks").message == admin.HAS_ORDERS


# ---------------------------------------------------------------- US-704 edit + image
def test_get_course_for_edit_includes_modules_and_paths(staff, fake_client):
    fake_client.tables["course_modules"] = [
        {"id": 2, "course_id": 101, "position": 2, "title": "Pandas", "description": ""},
        {"id": 1, "course_id": 101, "position": 1, "title": "Variables", "description": ""},
    ]
    course = admin.get_course_for_edit(101)

    assert [m["title"] for m in course["modules"]] == ["Variables", "Pandas"]
    assert course["paths"] == [
        {"path_id": 1, "path_name": "Data Analyst Path", "position": 1, "course_count": 2}
    ]


def test_get_course_for_edit_unknown(staff):
    assert admin.get_course_for_edit(999) is None


def test_update_course_saves_fields_and_keeps_sold_seats(staff, fake_client):
    data = course_input(
        title="SQL for Analysts", slug="sql-for-analysts", seats_total=40, path_positions=[]
    )
    result = admin.update_course(102, data)

    assert result.ok, result.message
    row = course_row(fake_client, 102)
    assert row["summary"] == "Think about fairness in data."
    assert (row["seats_total"], row["seats_available"]) == (40, 13)  # 27 sold stay sold


def test_update_course_cannot_drop_total_below_sold(staff, fake_client):
    data = course_input(title="SQL for Analysts", slug="sql-for-analysts", seats_total=20)
    result = admin.update_course(102, data)

    assert not result.ok
    assert "seats_total" in result.data["errors"]
    assert course_row(fake_client, 102)["summary"] == "Ask questions of your data."


def test_update_course_slug_of_another_course(staff):
    result = admin.update_course(101, course_input(slug="sql-for-analysts", seats_total=30))
    assert not result.ok
    assert result.data["errors"]["slug"] == admin.SLUG_TAKEN


def test_get_editor_name(staff):
    assert admin.get_editor_name(STAFF_ID) == "Sam Staff"
    assert admin.get_editor_name(None) == ""


@pytest.mark.parametrize(
    ("data", "content_type"),
    [(PNG_BYTES, "image/png"), (JPEG_BYTES, "image/jpeg"), (WEBP_BYTES, "image/webp")],
)
def test_upload_image_uses_random_name(staff, fake_client, data, content_type):
    result = admin.upload_course_image(data, content_type)

    assert result.ok
    (stored_path,) = fake_client.uploaded_files
    assert stored_path.startswith("course-images/")
    assert len(stored_path.split("/")[1].split(".")[0]) == 32  # uuid4 hex, not the user's name
    assert result.data["image_url"].endswith(stored_path.split("/")[1])


def test_upload_image_too_big(staff, fake_client):
    big = PNG_BYTES + b"\x00" * admin.MAX_IMAGE_BYTES
    assert "2 MB" in admin.upload_course_image(big, "image/png").message
    assert fake_client.uploaded_files == {}


def test_upload_image_wrong_type_or_fake_content(staff, fake_client):
    assert not admin.upload_course_image(b"GIF89a....", "image/gif").ok
    assert not admin.upload_course_image(b"just some text", "image/png").ok
    assert not admin.upload_course_image(b"", "image/png").ok
    assert fake_client.uploaded_files == {}


def test_upload_image_customer_refused(customer, fake_client):
    assert not admin.upload_course_image(PNG_BYTES, "image/png").ok


# ---------------------------------------------------------------- US-709 staff
def test_owner_lists_users(owner):
    users = admin.list_users()
    assert {row["id"] for row in users} == {CUSTOMER_ID, STAFF_ID, OWNER_ID}


def test_staff_gets_no_user_list(staff):
    assert admin.list_users() == []


def test_owner_promotes_customer_to_staff(owner, fake_client):
    result = admin.change_user_role(CUSTOMER_ID, "staff")
    assert result.ok
    row = next(p for p in fake_client.tables["profiles"] if p["id"] == CUSTOMER_ID)
    assert row["role"] == "staff"


def test_owner_cannot_make_another_owner_or_change_self(owner, fake_client):
    assert not admin.change_user_role(STAFF_ID, "owner").ok
    assert admin.change_user_role(OWNER_ID, "customer").message == admin.OWN_ROLE_MESSAGE


def test_staff_cannot_change_roles(staff, fake_client):
    result = admin.change_user_role(CUSTOMER_ID, "staff")
    assert not result.ok
    row = next(p for p in fake_client.tables["profiles"] if p["id"] == CUSTOMER_ID)
    assert row["role"] == "customer"


@pytest.mark.parametrize("code", ["LAST_OWNER", "NOT_ALLOWED"])
def test_database_role_errors_are_friendly(owner, fake_client, monkeypatch, code):
    original = query_class(fake_client).execute

    def db_error(self):
        if self.action == "update" and self.table_name == "profiles":
            raise FakeAuthError(f"{code}: blocked by the database", code="P0001")
        return original(self)

    monkeypatch.setattr(query_class(fake_client), "execute", db_error)
    assert admin.change_user_role(STAFF_ID, "customer").message == admin.ROLE_ERRORS[code]


# ---------------------------------------------------------------- US-708 dashboard
def test_dashboard_metrics(staff, fake_client):
    fake_client.tables["orders"].append(
        {"id": 2, "order_number": "ORD-2", "user_id": CUSTOMER_ID, "status": "cancelled",
         "total": 79.0, "created_at": "2026-11-02T10:00:00+00:00"}
    )  # fmt: skip
    fake_client.tables["order_items"].append(
        {"order_id": 2, "course_id": 102, "title_snapshot": "SQL", "unit_price": 79, "quantity": 1}
    )
    metrics = admin.get_dashboard_metrics()

    assert metrics["total_orders"] == 1  # cancelled orders don't count
    assert metrics["total_revenue"] == 49.0
    assert metrics["seats_sold"] == 1
    assert metrics["customer_count"] == 1
    assert len(metrics["orders_per_day"]) == admin.DASHBOARD_DAYS
    assert metrics["top_courses"] == [{"title": "Python for Data Beginners", "seats_sold": 1}]
    # 103 is sold out, 102 has 3 seats; the draft 104 is not listed.
    assert [c["id"] for c in metrics["low_seat_courses"]] == [103, 102]


def test_dashboard_with_no_orders(staff, fake_client):
    fake_client.tables["orders"] = []
    metrics = admin.get_dashboard_metrics()
    assert (metrics["total_orders"], metrics["seats_sold"], metrics["top_courses"]) == (0, 0, [])
    assert all(day["orders"] == 0 for day in metrics["orders_per_day"])


def test_is_low_seats():
    assert admin.is_low_seats(5, 100)
    assert admin.is_low_seats(10, 100)
    assert not admin.is_low_seats(11, 100)


# ---------------------------------------------------------------- US-707 orders (for U2-18)
def test_list_all_orders_adds_email_and_seat_count(staff):
    orders = admin.list_all_orders()
    assert len(orders) == 1
    assert orders[0]["customer_email"] == "customer@example.test"
    assert orders[0]["item_count"] == 1
    assert "idempotency_key" not in orders[0]


def test_list_all_orders_filters(staff):
    assert admin.list_all_orders(search="CUSTOMER@") != []
    assert admin.list_all_orders(search="ORD-2026") != []
    assert admin.list_all_orders(search="nobody") == []
    assert admin.list_all_orders(status="cancelled") == []
    assert admin.list_all_orders(date_from="2026-11-01", date_to="2026-11-01") != []
    assert admin.list_all_orders(date_from="2026-11-02") == []
    assert admin.list_all_orders(date_to="2026-10-31") == []


def test_list_all_orders_customer_gets_nothing(customer):
    assert admin.list_all_orders() == []


# ---------------------------------------------------------------- US-711 categories + paths
def test_create_and_update_category(staff, fake_client):
    assert admin.save_category("Data Engineering", "🛠️", 3).ok
    new = next(c for c in fake_client.tables["categories"] if c["name"] == "Data Engineering")
    assert admin.save_category("Data Pipelines", "🛠️", 4, new["id"]).ok
    assert new["id"] in {c["id"] for c in fake_client.tables["categories"]}
    renamed = next(c for c in fake_client.tables["categories"] if c["id"] == new["id"])
    assert (renamed["name"], renamed["sort_order"]) == ("Data Pipelines", 4)


def test_category_validation(staff):
    result = admin.save_category("", "", -1)
    assert not result.ok
    assert set(result.data["errors"]) == {"name", "icon", "sort_order"}


def test_category_customer_refused(customer, fake_client):
    before = len(fake_client.tables["categories"])
    assert not admin.save_category("Hacking", "💀", 1).ok
    assert len(fake_client.tables["categories"]) == before


def test_create_path_with_badge_and_ordered_courses(staff, fake_client):
    result = admin.save_path(
        "AI Starter Path", "First steps", [103, 101], "Path Master: AI Starter"
    )

    assert result.ok, result.message
    path_id = result.data["path_id"]
    path = next(p for p in fake_client.tables["learning_paths"] if p["id"] == path_id)
    assert path["badge_code"] == "path_master_ai_starter_path"
    badge = next(b for b in fake_client.tables["badges"] if b["code"] == path["badge_code"])
    assert badge["name"] == "Path Master: AI Starter"
    assert rpc_params(fake_client, "admin_replace_path_courses") == {
        "p_path_id": path_id,
        "p_course_ids": [103, 101],
    }


def test_update_path_replaces_courses_and_renames_badge(staff, fake_client):
    fake_client.tables["badges"] = [{"code": "path_master_data_analyst", "name": "Old"}]
    result = admin.save_path("Data Analyst Path", "", [102], "Data Hero", path_id=1)

    assert result.ok, result.message
    assert rpc_params(fake_client, "admin_replace_path_courses") == {
        "p_path_id": 1,
        "p_course_ids": [102],
    }
    assert fake_client.tables["badges"][0]["name"] == "Data Hero"


def test_path_courses_error_keeps_old_courses_and_explains(staff, fake_client):
    fake_client.rpc_results["admin_replace_path_courses"] = FakeAuthError(
        "DUPLICATE_COURSE: add each course only once", code="P0001"
    )
    result = admin.save_path("Data Analyst Path", "", [102], "Data Hero", path_id=1)

    assert not result.ok
    assert "Add each course only once." in result.message
    links = [link for link in fake_client.tables["learning_path_courses"] if link["path_id"] == 1]
    assert len(links) == 2  # untouched: the database function rolled back


# ---------------------------------------------------------------- review fixes
def test_position_taken_keeps_old_children_and_is_friendly(staff, fake_client):
    fake_client.rpc_results["admin_replace_course_children"] = FakeAuthError(
        "POSITION_TAKEN: Data Analyst Path step 1", code="P0001"
    )
    data = course_input(title="SQL for Analysts", slug="sql-for-analysts", seats_total=30)
    result = admin.update_course(102, data)

    assert result.ok  # the course fields were saved ...
    assert "already taken" in result.message  # ... and the user is told what was not
    assert [
        link for link in fake_client.tables["learning_path_courses"] if link["course_id"] == 102
    ]


def test_update_course_failure_leaves_seats_unchanged(staff, fake_client, monkeypatch):
    original = query_class(fake_client).execute

    def update_fails(self):
        if self.action == "update" and self.table_name == "courses" and "title" in self.payload:
            raise FakeAuthError("check constraint", code="23514")
        return original(self)

    monkeypatch.setattr(query_class(fake_client), "execute", update_fails)
    data = course_input(title="SQL for Analysts", slug="sql-for-analysts", seats_total=40)
    result = admin.update_course(102, data)

    assert not result.ok
    row = course_row(fake_client, 102)
    assert (row["seats_total"], row["seats_available"]) == (30, 3)  # seats saved last


def test_replacing_image_deletes_the_old_upload(staff, fake_client, monkeypatch):
    removed = []
    bucket_class = type(fake_client.storage.from_("course-images"))
    monkeypatch.setattr(
        bucket_class, "remove", lambda self, paths: removed.extend(paths), raising=False
    )
    old_name = "a" * 32 + ".png"
    course_row(fake_client, 102)["image_url"] = (
        f"https://fake.supabase.test/storage/v1/object/public/course-images/{old_name}"
    )
    data = course_input(title="SQL for Analysts", slug="sql-for-analysts", seats_total=30)
    data["image_url"] = None  # "Remove the current image"

    assert admin.update_course(102, data).ok
    assert removed == [old_name]


def test_delete_course_image_ignores_foreign_urls(staff):
    assert admin.delete_course_image("https://example.test/someone-else.png") is False
    assert admin.delete_course_image(None) is False


def test_messages_escape_markdown(owner, fake_client):
    profile = next(p for p in fake_client.tables["profiles"] if p["id"] == CUSTOMER_ID)
    profile["display_name"] = "[click](http://x.test)"
    result = admin.change_user_role(CUSTOMER_ID, "staff")
    assert "[click]" not in result.message
    assert r"\[click\]" in result.message


def test_dashboard_reads_more_than_one_page(staff, fake_client, monkeypatch):
    monkeypatch.setattr(admin, "PAGE_ROWS", 1)  # pretend the server returns 1 row per page
    fake_client.tables["orders"].append(
        {"id": 3, "order_number": "ORD-3", "user_id": CUSTOMER_ID, "status": "confirmed",
         "total": 10.0, "created_at": "2026-11-03T10:00:00+00:00"}
    )  # fmt: skip
    metrics = admin.get_dashboard_metrics()
    assert metrics["total_orders"] == 2
    assert metrics["total_revenue"] == 59.0
    assert len(admin.list_all_orders()) == 2


def test_path_validation(staff):
    result = admin.save_path("", "", [101, 101], "")
    assert set(result.data["errors"]) == {"name", "courses", "badge_name"}


def test_list_categories_and_paths(staff):
    categories, paths = admin.list_categories_and_paths()
    assert [c["sort_order"] for c in categories] == [1, 2]
    assert [course["id"] for course in paths[0]["courses"]] == [101, 102]
