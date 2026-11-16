"""Shared test setup: a FAKE Supabase client and sample data.

Why a fake? Unit tests must run anywhere (your laptop, GitHub Actions) without
internet, keys or a real database. The fake stores tables as Python lists and
understands the query calls our services use:

    client.table("courses").select("*").eq("is_published", True).order("title").execute()

How to use it in a test:

    def test_something(fake_client, session_state):
        ...  # session_state already holds fake_client, so get_client() returns it

If your service uses a query method the fake does not know yet, add it to
FakeQuery below (keep it simple) in your story PR.
"""

import copy
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
import streamlit as st

from app.services.supabase_client import CLIENT_SESSION_KEY

# ---------------------------------------------------------------- sample data
CUSTOMER_ID = "11111111-1111-1111-1111-111111111111"
STAFF_ID = "22222222-2222-2222-2222-222222222222"
OWNER_ID = "33333333-3333-3333-3333-333333333333"
DEMO_PASSWORD = "Demo1234pass"  # fake password, only for these tests

SAMPLE_DATA: dict[str, list[dict[str, Any]]] = {
    "categories": [
        {"id": 1, "name": "Artificial Intelligence", "icon": "🤖", "sort_order": 1},
        {"id": 2, "name": "Data Analytics", "icon": "📊", "sort_order": 2},
    ],
    "courses": [
        {
            "id": 101,
            "slug": "python-for-data-beginners",
            "title": "Python for Data Beginners",
            "summary": "Start coding with data.",
            "description": "Variables, lists, and pandas basics.",
            "category_id": 2,
            "level": "Beginner",
            "duration_hours": 6,
            "price": 49.00,
            "seats_total": 30,
            "seats_available": 22,
            "instructor_name": "Ada Lumen",
            "tags": ["python", "pandas"],
            "image_url": None,
            "xp_reward": 100,
            "is_published": True,
            "is_featured": True,
        },
        {
            "id": 102,
            "slug": "sql-for-analysts",
            "title": "SQL for Analysts",
            "summary": "Ask questions of your data.",
            "description": "SELECT, JOIN, GROUP BY.",
            "category_id": 2,
            "level": "Intermediate",
            "duration_hours": 8,
            "price": 79.00,
            "seats_total": 30,
            "seats_available": 3,
            "instructor_name": "Bo Query",
            "tags": ["sql"],
            "image_url": None,
            "xp_reward": 100,
            "is_published": True,
            "is_featured": False,
        },
        {
            "id": 103,
            "slug": "prompt-engineering-fundamentals",
            "title": "Prompt Engineering Fundamentals",
            "summary": "Talk to AI clearly.",
            "description": "Patterns for clear prompts.",
            "category_id": 1,
            "level": "Beginner",
            "duration_hours": 4,
            "price": 39.00,
            "seats_total": 20,
            "seats_available": 0,
            "instructor_name": "Cy Token",
            "tags": ["ai"],
            "image_url": None,
            "xp_reward": 100,
            "is_published": True,
            "is_featured": True,
        },
        {
            "id": 104,
            "slug": "neural-networks-draft",
            "title": "Intro to Neural Networks",
            "summary": "Draft course.",
            "description": "Not published yet.",
            "category_id": 1,
            "level": "Advanced",
            "duration_hours": 10,
            "price": 129.00,
            "seats_total": 25,
            "seats_available": 25,
            "instructor_name": "Dee Layer",
            "tags": ["ai"],
            "image_url": None,
            "xp_reward": 100,
            "is_published": False,
            "is_featured": False,
        },
    ],
    "learning_paths": [
        {
            "id": 1,
            "name": "Data Analyst Path",
            "description": "From Python to SQL.",
            "bonus_xp": 250,
            "badge_code": "path_master_data_analyst",
        },
    ],
    "learning_path_courses": [
        {"path_id": 1, "course_id": 101, "position": 1},
        {"path_id": 1, "course_id": 102, "position": 2},
    ],
    "profiles": [
        {
            "id": CUSTOMER_ID,
            "email": "customer@example.test",
            "display_name": "Casey Customer",
            "role": "customer",
            "xp_total": 150,
            "level": 2,
            "avatar": "rocket",
            "interests": [],
            "reduce_motion": False,
        },
        {
            "id": STAFF_ID,
            "email": "staff@example.test",
            "display_name": "Sam Staff",
            "role": "staff",
            "xp_total": 0,
            "level": 1,
            "avatar": None,
            "interests": [],
            "reduce_motion": False,
        },
        {
            "id": OWNER_ID,
            "email": "owner@example.test",
            "display_name": "Olive Owner",
            "role": "owner",
            "xp_total": 0,
            "level": 1,
            "avatar": None,
            "interests": [],
            "reduce_motion": False,
        },
    ],
    "cart_items": [],
    "orders": [
        {
            "id": 1,
            "order_number": "ORD-20261101-0001",
            "user_id": CUSTOMER_ID,
            "status": "confirmed",
            "total": 49.00,
            "idempotency_key": "9b2f7c1e-0000-4000-8000-000000000001",
            "xp_awarded": 100,
            "badges_awarded": ["first_unlock"],
            "created_at": "2026-11-01T10:00:00+00:00",
        },
    ],
    "order_items": [
        {
            "order_id": 1,
            "course_id": 101,
            "title_snapshot": "Python for Data Beginners",
            "unit_price": 49.00,
            "quantity": 1,
        },
    ],
    "email_outbox": [],
    "xp_events": [],
    "badges": [],
    "user_badges": [],
    "audit_log": [],
}

AUTH_USERS = {
    "customer@example.test": {"id": CUSTOMER_ID, "password": DEMO_PASSWORD},
    "staff@example.test": {"id": STAFF_ID, "password": DEMO_PASSWORD},
    "owner@example.test": {"id": OWNER_ID, "password": DEMO_PASSWORD},
}


# ---------------------------------------------------------------- fake client
class FakeAuthError(Exception):
    """Looks like supabase_auth.errors.AuthApiError (has a .code)."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


class FakeQuery:
    """A tiny, chainable stand-in for the Supabase query builder."""

    def __init__(self, client: "FakeSupabaseClient", table_name: str) -> None:
        self.client = client
        self.table_name = table_name
        self.filters: list = []  # functions row -> bool
        self.action = "select"
        self.payload: Any = None
        self.order_by: list[tuple[str, bool]] = []
        self.row_limit: int | None = None
        self.row_offset = 0
        self.single_row = False

    # --- what to do
    def select(self, *_columns: str, count: str | None = None) -> "FakeQuery":
        return self

    def insert(self, rows: dict | list[dict]) -> "FakeQuery":
        self.action, self.payload = "insert", rows
        return self

    def upsert(self, rows: dict | list[dict], **_options: Any) -> "FakeQuery":
        self.action, self.payload = "upsert", rows
        return self

    def update(self, values: dict) -> "FakeQuery":
        self.action, self.payload = "update", values
        return self

    def delete(self) -> "FakeQuery":
        self.action = "delete"
        return self

    # --- filters
    def eq(self, column: str, value: Any) -> "FakeQuery":
        self.filters.append(lambda row: row.get(column) == value)
        return self

    def neq(self, column: str, value: Any) -> "FakeQuery":
        self.filters.append(lambda row: row.get(column) != value)
        return self

    def in_(self, column: str, values: list) -> "FakeQuery":
        self.filters.append(lambda row: row.get(column) in values)
        return self

    def gt(self, column: str, value: Any) -> "FakeQuery":
        self.filters.append(lambda row: row.get(column) is not None and row.get(column) > value)
        return self

    def gte(self, column: str, value: Any) -> "FakeQuery":
        self.filters.append(lambda row: row.get(column) is not None and row.get(column) >= value)
        return self

    def lt(self, column: str, value: Any) -> "FakeQuery":
        self.filters.append(lambda row: row.get(column) is not None and row.get(column) < value)
        return self

    def lte(self, column: str, value: Any) -> "FakeQuery":
        self.filters.append(lambda row: row.get(column) is not None and row.get(column) <= value)
        return self

    def ilike(self, column: str, pattern: str) -> "FakeQuery":
        needle = pattern.strip("%").lower()
        self.filters.append(lambda row: needle in str(row.get(column, "")).lower())
        return self

    # --- shape of the result
    def order(self, column: str, desc: bool = False) -> "FakeQuery":
        self.order_by.append((column, desc))
        return self

    def limit(self, count: int) -> "FakeQuery":
        self.row_limit = count
        return self

    def range(self, start: int, end: int) -> "FakeQuery":
        self.row_offset, self.row_limit = start, end - start + 1
        return self

    def single(self) -> "FakeQuery":
        self.single_row = True
        return self

    maybe_single = single

    # --- run it
    def execute(self) -> SimpleNamespace:
        rows = self.client.tables.setdefault(self.table_name, [])
        matches = [row for row in rows if all(check(row) for check in self.filters)]
        if self.action in ("insert", "upsert"):
            new_rows = self.payload if isinstance(self.payload, list) else [self.payload]
            rows.extend(copy.deepcopy(new_rows))
            return SimpleNamespace(data=copy.deepcopy(new_rows), count=len(new_rows))
        if self.action == "update":
            for row in matches:
                row.update(self.payload)
            return SimpleNamespace(data=copy.deepcopy(matches), count=len(matches))
        if self.action == "delete":
            self.client.tables[self.table_name] = [row for row in rows if row not in matches]
            return SimpleNamespace(data=copy.deepcopy(matches), count=len(matches))
        return self._select_result(matches)

    def _select_result(self, matches: list[dict]) -> SimpleNamespace:
        for column, desc in reversed(self.order_by):
            matches = sorted(
                matches, key=lambda row: (row.get(column) is None, row.get(column)), reverse=desc
            )
        total = len(matches)
        end = None if self.row_limit is None else self.row_offset + self.row_limit
        matches = copy.deepcopy(matches[self.row_offset : end])
        if self.single_row:
            return SimpleNamespace(data=matches[0] if matches else None, count=total)
        return SimpleNamespace(data=matches, count=total)


class FakeRpc:
    def __init__(self, client: "FakeSupabaseClient", name: str, params: dict) -> None:
        self.client, self.name, self.params = client, name, params

    def execute(self) -> SimpleNamespace:
        self.client.rpc_calls.append((self.name, self.params))
        result = self.client.rpc_results.get(self.name)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(data=result)


class FakeAuth:
    """Fake email + password auth. Signing up also creates the profile row,
    like the real database trigger does."""

    def __init__(self, client: "FakeSupabaseClient") -> None:
        self.client = client
        self.users = copy.deepcopy(AUTH_USERS)
        self.signed_in_user_id: str | None = None

    def _response(self, email: str) -> SimpleNamespace:
        record = self.users[email]
        self.signed_in_user_id = record["id"]
        user = SimpleNamespace(
            id=record["id"], email=email, user_metadata=record.get("metadata", {})
        )
        session = SimpleNamespace(
            access_token="fake-access-token",
            refresh_token="fake-refresh-token",
            expires_at=4102444800,
        )
        return SimpleNamespace(user=user, session=session)

    def sign_in_with_password(self, credentials: dict) -> SimpleNamespace:
        record = self.users.get(credentials["email"])
        if record is None or record["password"] != credentials["password"]:
            raise FakeAuthError("Invalid login credentials", code="invalid_credentials")
        return self._response(credentials["email"])

    def sign_up(self, credentials: dict) -> SimpleNamespace:
        email = credentials["email"]
        if email in self.users:
            raise FakeAuthError("User already registered", code="user_already_exists")
        metadata = credentials.get("options", {}).get("data", {})
        user_id = str(uuid.uuid4())
        self.users[email] = {
            "id": user_id,
            "password": credentials["password"],
            "metadata": metadata,
        }
        self.client.tables["profiles"].append(
            {
                "id": user_id,
                "email": email,
                "display_name": metadata.get("display_name", ""),
                "role": "customer",
                "xp_total": 50,
                "level": 1,
            }  # the real trigger also gives +50 XP
        )
        return self._response(email)

    def sign_out(self) -> None:
        self.signed_in_user_id = None


class FakeStorageBucket:
    def __init__(self, client: "FakeSupabaseClient", bucket: str) -> None:
        self.client, self.bucket = client, bucket

    def upload(self, path: str, file: bytes, file_options: dict | None = None) -> SimpleNamespace:
        self.client.uploaded_files[f"{self.bucket}/{path}"] = file
        return SimpleNamespace(path=path)

    def get_public_url(self, path: str) -> str:
        return f"https://fake.supabase.test/storage/v1/object/public/{self.bucket}/{path}"


class FakeSupabaseClient:
    def __init__(self, data: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = data
        self.auth = FakeAuth(self)
        self.storage = SimpleNamespace(from_=lambda bucket: FakeStorageBucket(self, bucket))
        self.rpc_results: dict[str, Any] = {}  # set per test, e.g. {"place_order": {...}}
        self.rpc_calls: list[tuple[str, dict]] = []
        self.uploaded_files: dict[str, bytes] = {}

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)

    from_ = table

    def rpc(self, name: str, params: dict | None = None) -> FakeRpc:
        return FakeRpc(self, name, params or {})


# ---------------------------------------------------------------- fixtures
@pytest.fixture
def sample_data() -> dict[str, list[dict[str, Any]]]:
    """A fresh copy of the sample data for each test (tests can't affect each other)."""
    return copy.deepcopy(SAMPLE_DATA)


@pytest.fixture
def fake_client(sample_data: dict) -> FakeSupabaseClient:
    return FakeSupabaseClient(sample_data)


@pytest.fixture
def session_state(monkeypatch: pytest.MonkeyPatch, fake_client: FakeSupabaseClient) -> dict:
    """Replace st.session_state with a plain dict that already holds the fake client.

    Services use st.session_state["key"] style, which a dict supports, so plain
    pytest (without a running Streamlit app) can test them.
    """
    state: dict[str, Any] = {CLIENT_SESSION_KEY: fake_client}
    monkeypatch.setattr(st, "session_state", state)
    return state
