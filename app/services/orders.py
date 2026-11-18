"""Checkout and orders (Epic E4).

Placing an order is done ENTIRELY by the database function `place_order`
(one transaction: check seats, create order + items, deduct seats, clear cart,
award XP and badges). The app never calculates prices or XP itself (NFR-SEC-09).
"""

import re
import uuid
from typing import Any

import streamlit as st

from app.models.domain import ADMIN_ROLES, ActionResult, Order, OrderItem, PlaceOrderOutcome
from app.services import auth, catalog
from app.services.supabase_client import get_client
from app.utils.log import get_logger

logger = get_logger(__name__)

# Friendly text for each error code the place_order function can raise.
# The database error message starts with the code, e.g. "NOT_ENOUGH_SEATS: SQL for Analysts".
PLACE_ORDER_ERRORS = {
    "NOT_SIGNED_IN": "Please sign in to place your order.",
    "CART_EMPTY": "Your cart is empty.",
    "INVALID_REQUEST": "Something went wrong, please try again.",
    "COURSE_UNAVAILABLE": "{title} is no longer available. Remove it from your cart to continue.",
    "NOT_ENOUGH_SEATS": "Only {seats} seat(s) left for {title}. Update the quantity to continue.",
}

# Errors the database can raise when an order is cancelled.
CANCEL_ORDER_ERRORS = {
    "NOT_ALLOWED": "Only staff can cancel orders.",
    "ORDER_ALREADY_CANCELLED": "This order is already cancelled.",
}

GENERIC_ORDER_ERROR = "Something went wrong, please try again."
# Set by the checkout page when an order fails because of the cart (US-404 AC2);
# the cart page shows it once at the top.
CHECKOUT_PROBLEM_KEY = "checkout_problem"
# Set by the checkout page after a new order; read once by the confirmation page (US-605).
CELEBRATION_KEY = "order_celebration"

_ORDER_COLUMNS = (
    "id, order_number, user_id, status, total, xp_awarded, badges_awarded, created_at, updated_at"
)
# "NOT_ENOUGH_SEATS: SQL for Analysts" -> code + title
_ERROR_PATTERN = re.compile(r"^\s*([A-Z_]+)\s*(?::\s*(.*))?$", re.DOTALL)
_SEATS_PATTERN = re.compile(r"seats_available=(\d+)")


# ---------------------------------------------------------------- placing an order
def new_idempotency_key() -> str:
    """Return a new random UUID string for ONE checkout attempt.

    Create it once when the checkout page opens and keep it in session state, so a
    double click sends the same key and the database returns the same order
    (NFR-DATA-04). Story US-402 (U2-03).
    """
    return str(uuid.uuid4())


def _error_text(error: Exception) -> tuple[str, str]:
    """(message, detail) from a database error. supabase-py's APIError has both."""
    message = getattr(error, "message", None) or str(error)
    detail = getattr(error, "details", None) or ""
    return str(message), str(detail)


def _outcome_from_error(error: Exception) -> PlaceOrderOutcome:
    """Turn a place_order database error into a friendly outcome (US-404 AC1)."""
    message, detail = _error_text(error)
    match = _ERROR_PATTERN.match(message.splitlines()[0] if message else "")
    code = match.group(1) if match else ""
    if code not in PLACE_ORDER_ERRORS:
        logger.warning("place_order failed: unknown error %s", type(error).__name__)
        return PlaceOrderOutcome(ok=False, message=GENERIC_ORDER_ERROR, error_code="UNKNOWN")

    title = (match.group(2) or "").strip() if match else ""
    titles = [title] if title and code in ("COURSE_UNAVAILABLE", "NOT_ENOUGH_SEATS") else []
    seats_match = _SEATS_PATTERN.search(detail) or _SEATS_PATTERN.search(message)
    seats = int(seats_match.group(1)) if seats_match else 0
    friendly = PLACE_ORDER_ERRORS[code].format(title=title or "A course", seats=seats)
    logger.info("place_order failed: reason=%s", code)  # NFR-LOG-02 (no personal data)
    return PlaceOrderOutcome(ok=False, message=friendly, error_code=code, problem_titles=titles)


def place_order(idempotency_key: str) -> PlaceOrderOutcome:
    """Call RPC place_order with {"p_idempotency_key": idempotency_key} (a uuid string).

    On success: ok=True and `order` = the jsonb result {order_id, order_number
    ("ORD-YYYYMMDD-0042"), total, xp_awarded, new_level (level after the order),
    level_up, new_badges, already_existed}.
    On failure: ok=False, `error_code` is one of NOT_SIGNED_IN, CART_EMPTY,
    COURSE_UNAVAILABLE, NOT_ENOUGH_SEATS, INVALID_REQUEST (parsed from the start
    of the database error message), `problem_titles` lists the course title after
    the colon, and `message` is the friendly text from PLACE_ORDER_ERRORS. For
    NOT_ENOUGH_SEATS the error DETAIL holds "seats_available=<n>" (US-404 AC1). Unknown errors get
    "Something went wrong, please try again." and are logged (NFR-LOG-02).
    Stories US-402 (U2-03), US-403 (U2-08), US-404 (U2-07).
    """
    if auth.current_user() is None:
        return PlaceOrderOutcome(
            ok=False, message=PLACE_ORDER_ERRORS["NOT_SIGNED_IN"], error_code="NOT_SIGNED_IN"
        )
    try:
        uuid.UUID(str(idempotency_key))  # a bad key would only give a confusing DB error
    except ValueError:
        return PlaceOrderOutcome(
            ok=False, message=PLACE_ORDER_ERRORS["INVALID_REQUEST"], error_code="INVALID_REQUEST"
        )
    try:
        response = (
            get_client().rpc("place_order", {"p_idempotency_key": str(idempotency_key)}).execute()
        )
    except Exception as error:
        return _outcome_from_error(error)

    result = response.data
    if not isinstance(result, dict) or "order_id" not in result:
        logger.warning("place_order returned an unexpected result")
        return PlaceOrderOutcome(ok=False, message=GENERIC_ORDER_ERROR, error_code="UNKNOWN")
    logger.info(
        "order placed: order_id=%s already_existed=%s",
        result["order_id"],
        result.get("already_existed"),
    )
    auth.reload_current_user()  # the header shows the new XP and level right away
    catalog.clear_cache()  # seat counts changed, so the storefront must not show cached ones
    return PlaceOrderOutcome(ok=True, message="Your order is confirmed.", order=result)  # type: ignore[arg-type]


# ---------------------------------------------------------------- reading orders
def _to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _items_for(order_ids: list[int]) -> dict[int, list[OrderItem]]:
    """{order_id: [items]} for several orders in ONE query."""
    if not order_ids:
        return {}
    response = (
        get_client()
        .table("order_items")
        .select("order_id, course_id, title_snapshot, unit_price, quantity")
        .in_("order_id", order_ids)
        .execute()
    )
    items: dict[int, list[OrderItem]] = {}
    for row in response.data or []:
        items.setdefault(int(row["order_id"]), []).append(
            OrderItem(
                course_id=int(row["course_id"]),
                title_snapshot=row.get("title_snapshot", ""),
                unit_price=_to_float(row.get("unit_price")),
                quantity=int(row.get("quantity") or 0),
            )
        )
    return items


def _to_order(row: dict, items: list[OrderItem]) -> Order:
    """A database row + its items -> Order (numbers as Python numbers)."""
    return Order(
        id=int(row["id"]),
        order_number=row.get("order_number", ""),
        user_id=row.get("user_id", ""),
        status=row.get("status", "confirmed"),
        total=_to_float(row.get("total")),
        xp_awarded=int(row.get("xp_awarded") or 0),
        badges_awarded=list(row.get("badges_awarded") or []),
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at") or "",
        item_count=sum(item["quantity"] for item in items),
        items=items,
    )


def get_order(order_id: int) -> Order | None:
    """Return one order with "items" (title_snapshot, unit_price, quantity), or None.

    RLS returns only the customer's own orders (staff/owner see all).
    Stories US-405 (U2-05), US-407 AC2 (U2-15), US-707 AC3 (U2-18).
    """
    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return None  # e.g. "?order=abc" in the address bar
    response = (
        get_client().table("orders").select(_ORDER_COLUMNS).eq("id", order_id).limit(1).execute()
    )
    rows = response.data or []
    if not rows:
        return None
    return _to_order(rows[0], _items_for([order_id]).get(order_id, []))


def list_my_orders() -> list[Order]:
    """Return the signed-in customer's orders, newest first, with item_count.

    Story US-407 (U2-15).
    """
    user = auth.current_user()
    if user is None:
        return []
    response = (
        get_client()
        .table("orders")
        .select(_ORDER_COLUMNS)
        .eq("user_id", user.id)  # staff can read every order, but "My orders" is only yours
        .order("created_at", desc=True)
        .execute()
    )
    rows = response.data or []
    items = _items_for([int(row["id"]) for row in rows])
    return [_to_order(row, items.get(int(row["id"]), [])) for row in rows]


def badge_names(codes: list[str]) -> list[str]:
    """Readable badge names for badge codes, e.g. "first_unlock" -> "First Unlock"."""
    if not codes:
        return []
    try:
        rows = (
            get_client()
            .table("badges")
            .select("code, name")
            .in_("code", list(codes))
            .execute()
            .data
        )
        names = {row["code"]: row["name"] for row in rows or []}
    except Exception as error:
        logger.info("badge names not loaded: %s", type(error).__name__)
        names = {}
    return [names.get(code) or code.replace("_", " ").title() for code in codes]


# ---------------------------------------------------------------- cancelling
def cancel_order(order_id: int) -> ActionResult:
    """Cancel a confirmed order (staff/owner only) by setting orders.status = 'cancelled'.

    A database trigger returns the seats and writes the audit log. Map the
    NOT_ALLOWED / ORDER_ALREADY_CANCELLED errors with CANCEL_ORDER_ERRORS.
    Story US-408 (U2-16).
    """
    # A friendly early answer; the database (RLS + column grants) is the real protection.
    if auth.require_role(*ADMIN_ROLES) is None:
        return ActionResult(ok=False, message=CANCEL_ORDER_ERRORS["NOT_ALLOWED"])
    try:
        order = get_order(order_id)
        if order is None:
            return ActionResult(ok=False, message="Order not found.")
        if order["status"] == "cancelled":
            return ActionResult(ok=False, message=CANCEL_ORDER_ERRORS["ORDER_ALREADY_CANCELLED"])
        response = (
            get_client()
            .table("orders")
            .update({"status": "cancelled"})
            .eq("id", int(order_id))
            .execute()
        )
    except Exception as error:
        message, _detail = _error_text(error)
        for code, friendly in CANCEL_ORDER_ERRORS.items():
            if message.startswith(code):
                return ActionResult(ok=False, message=friendly)
        logger.warning("cancel_order failed: order_id=%s %s", order_id, type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_ORDER_ERROR)

    if not response.data:  # RLS hid the row: this user may not change it
        return ActionResult(ok=False, message=CANCEL_ORDER_ERRORS["NOT_ALLOWED"])
    logger.info("order cancelled: order_id=%s", order_id)
    catalog.clear_cache()  # the cancelled seats are free again on the storefront
    return ActionResult(
        ok=True,
        message=f"Order {order['order_number']} is cancelled. Its seats are available again.",
    )


# ---------------------------------------------------------------- owned courses
def get_owned_course_ids(user_id: str) -> set[int]:
    """Return ids of courses the user has in confirmed orders.

    Used for "Unlocked" ribbons (S3), unlocked modules (US-202 AC3) and path nodes
    (US-604). Returns an empty set for guests (empty user_id) or if it can't be read.
    """
    if not user_id:
        return set()
    try:
        order_rows = (
            get_client()
            .table("orders")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "confirmed")
            .execute()
        ).data or []
        order_ids = [int(row["id"]) for row in order_rows]
        if not order_ids:
            return set()
        item_rows = (
            get_client()
            .table("order_items")
            .select("course_id")
            .in_("order_id", order_ids)
            .execute()
        ).data or []
    except Exception as error:
        logger.warning("get_owned_course_ids failed: %s", type(error).__name__)
        return set()
    return {int(row["course_id"]) for row in item_rows}


# ---------------------------------------------------------------- checkout helpers (session)
CHECKOUT_KEY_SESSION = "checkout_idempotency_key"


def checkout_key() -> str:
    """The idempotency key of the CURRENT checkout attempt, made once and kept in session.

    A rerun or double click reuses it, so the database returns the same order (NFR-DATA-04).
    """
    if CHECKOUT_KEY_SESSION not in st.session_state:
        st.session_state[CHECKOUT_KEY_SESSION] = new_idempotency_key()
    return st.session_state[CHECKOUT_KEY_SESSION]


def finish_checkout_attempt() -> None:
    """Forget the key after a successful order, so the next checkout is a new order."""
    st.session_state.pop(CHECKOUT_KEY_SESSION, None)


def item_rows(order: Order) -> list[dict[str, Any]]:
    """Rows for a small table of an order's items (pages show them with st.dataframe)."""
    return [
        {
            "Course": item["title_snapshot"],
            "Seats": item["quantity"],
            "Price": f"${item['unit_price']:,.2f}",
            "Line total": f"${item['unit_price'] * item['quantity']:,.2f}",
        }
        for item in order.get("items", [])
    ]


def readable_date(timestamp: str) -> str:
    """'2026-11-01T10:00:00+00:00' -> '2026-11-01 10:00' for tables and headings."""
    text = str(timestamp or "")
    return text[:16].replace("T", " ") if len(text) >= 16 else text
