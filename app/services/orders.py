"""Checkout and orders (Epic E4).

Placing an order is done ENTIRELY by the database function `place_order`
(one transaction: check seats, create order + items, deduct seats, clear cart,
award XP and badges). The app never calculates prices or XP itself (NFR-SEC-09).
"""

from app.models.domain import ActionResult, Order, PlaceOrderOutcome

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


def new_idempotency_key() -> str:
    """Return a new random UUID string for ONE checkout attempt.

    Create it once when the checkout page opens and keep it in session state, so a
    double click sends the same key and the database returns the same order
    (NFR-DATA-04). Story US-402 (U2-03).
    """
    raise NotImplementedError("U2-03 US-402")


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
    raise NotImplementedError("U2-03 US-402")


def get_order(order_id: int) -> Order | None:
    """Return one order with "items" (title_snapshot, unit_price, quantity), or None.

    RLS returns only the customer's own orders (staff/owner see all).
    Stories US-405 (U2-05), US-407 AC2 (U2-15), US-707 AC3 (U2-18).
    """
    raise NotImplementedError("U2-05 US-405")


def list_my_orders() -> list[Order]:
    """Return the signed-in customer's orders, newest first, with item_count.

    Story US-407 (U2-15).
    """
    raise NotImplementedError("U2-15 US-407")


def cancel_order(order_id: int) -> ActionResult:
    """Cancel a confirmed order (staff/owner only) by setting orders.status = 'cancelled'.

    A database trigger returns the seats and writes the audit log. Map the
    NOT_ALLOWED / ORDER_ALREADY_CANCELLED errors with CANCEL_ORDER_ERRORS.
    Story US-408 (U2-16).
    """
    raise NotImplementedError("U2-16 US-408")


def get_owned_course_ids(user_id: str) -> set[int]:
    """Return ids of courses the user has in confirmed orders.

    Used for "Unlocked" ribbons (S3), unlocked modules (US-202 AC3) and path nodes
    (US-604). The first story that needs it implements it: US-202 (U1-10).
    """
    raise NotImplementedError("U1-10 US-202")
