"""Data shapes shared by services, components and pages.

TypedDicts are plain dicts at runtime (exactly what Supabase returns), but they
tell your editor and reviewers which keys to expect. Column names match the
tables in docs/requirements/00 section 6 and supabase/migrations/.

IDs: profiles.id (= the auth user id) is a uuid string; every other id is a
bigint in the database, so an int in Python.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

# ---------------------------------------------------------------- roles
Role = Literal["customer", "staff", "owner"]
ROLES: tuple[Role, ...] = ("customer", "staff", "owner")
SIGNED_IN_ROLES: tuple[Role, ...] = ("customer", "staff", "owner")  # anyone signed in
ADMIN_ROLES: tuple[Role, ...] = ("staff", "owner")
OWNER_ONLY: tuple[Role, ...] = ("owner",)

CourseLevel = Literal["Beginner", "Intermediate", "Advanced"]
COURSE_LEVELS: tuple[CourseLevel, ...] = ("Beginner", "Intermediate", "Advanced")

OrderStatus = Literal["confirmed", "cancelled"]
SortOption = Literal["featured", "newest", "price_asc", "price_desc", "fewest_seats"]
NodeState = Literal["owned", "in_cart", "locked"]

MAX_SEATS_PER_ORDER_LINE = 5  # US-303 / doc 00 Q4


@dataclass
class CurrentUser:
    """The signed-in user, kept in st.session_state. No tokens or passwords here."""

    id: str
    email: str
    display_name: str
    role: Role = "customer"
    xp_total: int = 0
    level: int = 1


@dataclass
class ActionResult:
    """What most "do something" service functions return.

    ok:      True if it worked.
    message: Friendly text you can show the user as-is (never a stack trace).
    data:    Optional extra values, e.g. {"course_id": "..."} after create.
    """

    ok: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------- catalog
class Category(TypedDict):
    id: int
    name: str
    icon: str  # an emoji
    sort_order: int


class CourseModule(TypedDict):
    id: int
    course_id: int
    position: int
    title: str
    description: str


class Course(TypedDict, total=False):
    id: int
    slug: str
    title: str
    summary: str
    description: str
    category_id: int
    category_name: str  # filled by the service from categories
    level: CourseLevel
    duration_hours: float
    price: float
    seats_total: int
    seats_available: int
    instructor_name: str
    outcomes: list[str]
    prerequisites: list[str]
    tags: list[str]
    image_url: str | None
    xp_reward: int
    is_published: bool
    is_featured: bool
    updated_by: str | None  # profile uuid
    created_at: str
    updated_at: str
    modules: list[CourseModule]  # only from get_course
    paths: list[dict[str, Any]]  # [{"path_id": int, "path_name", "position", "course_count"}]


class CoursePage(TypedDict):
    courses: list[Course]
    total: int  # total matches, for "12 results" and pagination


class CourseFilters(TypedDict, total=False):
    category_ids: list[int]
    levels: list[CourseLevel]
    price_min: float
    price_max: float
    duration_min: float
    duration_max: float
    path_id: int | None
    only_available: bool


class LearningPath(TypedDict, total=False):
    id: int
    name: str
    description: str
    bonus_xp: int
    badge_code: str
    courses: list[Course]  # ordered by learning_path_courses.position


class PathNode(TypedDict):
    course_id: int
    slug: str
    title: str
    state: NodeState


# ---------------------------------------------------------------- cart
class CartLine(TypedDict, total=False):
    course_id: int
    slug: str
    title: str
    image_url: str | None
    unit_price: float
    quantity: int
    line_total: float
    xp_reward: int
    seats_available: int
    is_available: bool  # False if unpublished or sold out (US-307)
    problem: str  # friendly reason when not available


class CartSummary(TypedDict):
    item_count: int
    subtotal: float
    total: float
    total_xp: int
    courses_unlocked: int
    modules_unlocked: int


# ---------------------------------------------------------------- orders
class OrderItem(TypedDict):
    course_id: int
    title_snapshot: str
    unit_price: float
    quantity: int


class Order(TypedDict, total=False):
    id: int
    order_number: str  # "ORD-YYYYMMDD-0042"
    user_id: str
    status: OrderStatus
    total: float
    xp_awarded: int
    badges_awarded: list[str]  # badge codes
    created_at: str
    updated_at: str
    item_count: int
    customer_email: str  # admin views only
    items: list[OrderItem]


class PlaceOrderResponse(TypedDict):
    """Exactly what the place_order database function returns (jsonb)."""

    order_id: int
    order_number: str  # "ORD-YYYYMMDD-0042"
    total: float
    xp_awarded: int
    new_level: int  # the level AFTER this order
    level_up: bool  # True if new_level is higher than before
    new_badges: list[str]  # badge codes
    already_existed: bool  # True if this idempotency key was used before


@dataclass
class PlaceOrderOutcome:
    ok: bool
    message: str = ""
    order: PlaceOrderResponse | None = None
    # NOT_SIGNED_IN, CART_EMPTY, COURSE_UNAVAILABLE, NOT_ENOUGH_SEATS, INVALID_REQUEST or UNKNOWN
    error_code: str = ""
    problem_titles: list[str] = field(default_factory=list)


class EmailRecord(TypedDict, total=False):
    id: int
    order_id: int
    user_id: str
    to_email: str
    subject: str
    html_body: str
    file_name: str
    created_at: str


# ---------------------------------------------------------------- profile + gamification
class Profile(TypedDict, total=False):
    id: str  # uuid
    email: str  # read-only copy of the sign-in email
    display_name: str
    avatar: str | None
    interests: list[str]
    role: Role
    xp_total: int
    level: int
    reduce_motion: bool


class LevelProgress(TypedDict):
    level: int
    name: str
    xp_total: int
    level_start_xp: int
    next_level_xp: int | None  # None at the top level
    next_level_name: str | None


class XpEvent(TypedDict):
    id: int
    action: str  # register, complete_profile, purchase_course, complete_path
    points: int
    reference_id: int  # e.g. the course or path id, 0 if none
    created_at: str


class BadgeStatus(TypedDict):
    code: str
    name: str
    description: str
    icon: str  # an emoji
    sort_order: int
    earned: bool
    awarded_at: str | None
    hint: str  # how to unlock it, shown when locked


class PathProgress(TypedDict):
    path: LearningPath
    nodes: list[PathNode]
    owned_count: int
    total_count: int


# ---------------------------------------------------------------- admin
class CourseInput(TypedDict, total=False):
    title: str
    slug: str
    summary: str
    description: str
    category_id: int
    level: CourseLevel
    duration_hours: float
    price: float
    seats_total: int
    instructor_name: str
    outcomes: list[str]
    prerequisites: list[str]
    modules: list[dict[str, str]]  # [{"title", "description"}] in order
    tags: list[str]
    path_positions: list[dict[str, int]]  # [{"path_id": 1, "position": 2}]
    image_url: str | None
    is_featured: bool
    is_published: bool


class DashboardMetrics(TypedDict):
    total_orders: int
    total_revenue: float
    seats_sold: int
    customer_count: int
    orders_per_day: list[dict[str, Any]]  # [{"day": "2026-11-01", "orders": 3}]
    top_courses: list[dict[str, Any]]  # [{"title", "seats_sold"}]
    low_seat_courses: list[Course]


class UserRow(TypedDict):
    id: str  # uuid
    display_name: str
    email: str  # from profiles.email
    role: Role
    created_at: str
