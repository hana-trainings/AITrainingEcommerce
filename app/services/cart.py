"""Shopping cart (Epic E3).

Where the cart lives:
- Guest: in st.session_state only (US-305 AC2), key GUEST_CART_KEY,
  as {course_id (int): quantity}.
- Signed in: in the cart_items table (primary key user_id + course_id), US-305.
The functions below hide that difference from pages.

Prices and seats are ALWAYS read fresh from the courses table (never cached and
never taken from the page), so the cart can't show a stale price (US-307, NFR-PERF-04).
"""

from typing import Any

import streamlit as st

from app.models.domain import ActionResult, CartLine, CartSummary
from app.services import auth, orders
from app.services.supabase_client import get_client
from app.utils.log import get_logger

logger = get_logger(__name__)

GUEST_CART_KEY = "guest_cart"
MIN_QUANTITY = 1
MAX_QUANTITY = 5  # US-303 AC1
# {course_id: price} the customer last saw, to flag price changes (US-307).
SEEN_PRICES_KEY = "cart_seen_prices"

_COURSE_COLUMNS = "id, slug, title, image_url, price, seats_available, xp_reward, is_published"
NOT_AVAILABLE_MESSAGE = "This course is not available right now."
GENERIC_CART_ERROR = "Something went wrong with your cart, please try again."


# ---------------------------------------------------------------- small helpers
def _user_id() -> str | None:
    """The signed-in user's id, or None for a guest."""
    user = auth.current_user()
    return user.id if user else None


def _guest_cart() -> dict[int, int]:
    """The guest cart dict in session state (created the first time)."""
    if GUEST_CART_KEY not in st.session_state:
        st.session_state[GUEST_CART_KEY] = {}
    return st.session_state[GUEST_CART_KEY]


def _read_course(course_id: int) -> dict[str, Any] | None:
    """Read one course FRESH from the database. None if missing or not visible to you."""
    response = (
        get_client().table("courses").select(_COURSE_COLUMNS).eq("id", course_id).limit(1).execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def _seat_limit(seats_available: int) -> int:
    """Most seats one cart line may hold: 5, or fewer if fewer seats are left (US-303 AC2)."""
    return max(0, min(MAX_QUANTITY, int(seats_available)))


def _saved_quantities(user_id: str) -> dict[int, int]:
    """{course_id: quantity} from this user's saved cart (cart_items table)."""
    response = (
        get_client()
        .table("cart_items")
        .select("course_id, quantity, added_at")
        .eq("user_id", user_id)
        .order("added_at")
        .execute()
    )
    return {int(row["course_id"]): int(row["quantity"]) for row in response.data or []}


def _current_quantities() -> dict[int, int]:
    """{course_id: quantity} for whoever is using the app right now."""
    user_id = _user_id()
    if user_id is None:
        return dict(_guest_cart())
    return _saved_quantities(user_id)


def _save_quantity(course_id: int, quantity: int, already_in_cart: bool) -> None:
    """Write one line's quantity to the right place (session or table)."""
    user_id = _user_id()
    if user_id is None:
        _guest_cart()[course_id] = quantity
        return
    table = get_client().table("cart_items")
    if already_in_cart:
        table.update({"quantity": quantity}).eq("user_id", user_id).eq(
            "course_id", course_id
        ).execute()
    else:
        table.insert({"user_id": user_id, "course_id": course_id, "quantity": quantity}).execute()


# ---------------------------------------------------------------- add / count
def add_item(course_id: int, quantity: int = 1) -> ActionResult:
    """Add a course (or +1 if already there, capped at MAX_QUANTITY and seats_available).

    Returns ActionResult with a toast message, ok=False if sold out.
    Story US-301 (U2-01); also used by US-204 (U1-15).
    """
    try:
        course = _read_course(int(course_id))
        if course is None or not course.get("is_published"):
            return ActionResult(ok=False, message=NOT_AVAILABLE_MESSAGE)
        title = course["title"]
        limit = _seat_limit(course.get("seats_available", 0))
        if limit == 0:
            return ActionResult(ok=False, message=f"Sorry, {title} is sold out.")

        quantities = _current_quantities()
        current = quantities.get(int(course_id), 0)
        wanted = current + max(1, int(quantity))
        new_quantity = min(wanted, limit)
        if new_quantity <= current:
            return ActionResult(
                ok=False,
                message=f"You already have the most seats allowed for {title} ({current}).",
            )
        _save_quantity(int(course_id), new_quantity, already_in_cart=current > 0)
    except Exception as error:  # never show raw errors to the user (NFR-SEC-17)
        logger.warning("cart.add_item failed: course_id=%s %s", course_id, type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_CART_ERROR)

    if new_quantity < wanted:
        message = f"{title} is in your cart with {new_quantity} seat(s), the most allowed."
    elif current:
        message = f"{title} now has {new_quantity} seats in your cart."
    else:
        message = f"Added {title} to your cart."
    return ActionResult(ok=True, message=message, data={"quantity": new_quantity})


def get_item_count() -> int:
    """Return the number of seats in the cart for the header badge. Story US-301 AC3 (U2-01).

    The header calls this on every page, so it returns 0 instead of raising if the
    database can't be reached (the page itself shows the real error).
    """
    try:
        return sum(_current_quantities().values())
    except Exception as error:
        logger.warning("cart.get_item_count failed: %s", type(error).__name__)
        return 0


def get_cart_course_ids() -> set[int]:
    """Ids of the courses in the cart (for "In cart" states on cards and path maps)."""
    try:
        return set(_current_quantities())
    except Exception as error:
        logger.warning("cart.get_cart_course_ids failed: %s", type(error).__name__)
        return set()


# ---------------------------------------------------------------- view
def _module_counts(course_ids: list[int]) -> dict[int, int]:
    """{course_id: number of modules}, for "unlocks 14 modules" in the preview."""
    if not course_ids:
        return {}
    response = (
        get_client()
        .table("course_modules")
        .select("course_id")
        .in_("course_id", course_ids)
        .execute()
    )
    counts: dict[int, int] = {}
    for row in response.data or []:
        counts[int(row["course_id"])] = counts.get(int(row["course_id"]), 0) + 1
    return counts


def _owned_course_ids() -> set[int]:
    """Courses the signed-in user already bought (XP is only given once per course)."""
    user_id = _user_id()
    if user_id is None:
        return set()
    return orders.get_owned_course_ids(user_id)


def _missing_line(course_id: int, quantity: int) -> CartLine:
    """A cart line whose course was deleted or unpublished (we can't read it any more)."""
    return CartLine(
        course_id=course_id,
        slug="",
        title="A course that is no longer available",
        image_url=None,
        unit_price=0.0,
        quantity=quantity,
        line_total=0.0,
        xp_reward=0,
        seats_available=0,
        is_available=False,
        problem="This course is no longer available. Please remove it from your cart.",
        module_count=0,
        already_owned=False,
    )


def _build_line(course: dict, quantity: int, module_count: int, owned: bool) -> CartLine:
    """Turn a fresh course row + quantity into a cart line, with a problem text if needed."""
    price = float(course.get("price") or 0)
    seats = int(course.get("seats_available") or 0)
    problem = ""
    if not course.get("is_published"):
        problem = "This course is no longer available. Please remove it from your cart."
    elif seats == 0:
        problem = "This course is sold out. Please remove it from your cart."
    elif quantity > seats:
        problem = f"Only {seats} seat(s) left. Lower the quantity to continue."
    return CartLine(
        course_id=int(course["id"]),
        slug=course.get("slug", ""),
        title=course.get("title", ""),
        image_url=course.get("image_url"),
        unit_price=price,
        quantity=quantity,
        line_total=round(price * quantity, 2),
        # The database gives XP once per course, so a course you own earns none again.
        xp_reward=0 if owned else int(course.get("xp_reward") or 0),
        seats_available=seats,
        is_available=problem == "",
        problem=problem,
        module_count=module_count,
        already_owned=owned,
    )


def get_items() -> list[CartLine]:
    """Return cart lines with prices and seats re-read FRESH from the database (no cache).

    Lines whose course is unpublished or sold out have is_available=False and a
    `problem` text; they are excluded from checkout (US-307).
    Stories US-302 (U2-02), US-307 (U2-12), US-305 (U2-13).
    """
    quantities = _current_quantities()
    if not quantities:
        return []
    ids = list(quantities)
    response = get_client().table("courses").select(_COURSE_COLUMNS).in_("id", ids).execute()
    courses = {int(row["id"]): row for row in response.data or []}
    modules = _module_counts(ids)
    owned = _owned_course_ids()

    lines: list[CartLine] = []
    for course_id, quantity in quantities.items():
        course = courses.get(course_id)
        if course is None:
            lines.append(_missing_line(course_id, quantity))
        else:
            lines.append(
                _build_line(course, quantity, modules.get(course_id, 0), course_id in owned)
            )
    return lines


def price_changes(lines: list[CartLine]) -> list[str]:
    """Return messages like "The price of X changed from $49.00 to $59.00." (US-307).

    Compares with the prices this browser session saw last time, then remembers
    the new prices, so each change is reported once.
    """
    seen: dict[int, float] = st.session_state.setdefault(SEEN_PRICES_KEY, {})
    messages = []
    for line in lines:
        if not line.get("slug"):
            continue  # missing course: no price to compare
        course_id, price = line["course_id"], float(line["unit_price"])
        old_price = seen.get(course_id)
        if old_price is not None and abs(old_price - price) >= 0.005:
            messages.append(
                f"The price of {line['title']} changed from ${old_price:,.2f} to ${price:,.2f}."
            )
        seen[course_id] = price
    return messages


def summarize(lines: list[CartLine]) -> CartSummary:
    """Return totals and the "Unlock preview" for the available lines (pure function, no DB).

    Story US-302 AC2 (U2-02).
    """
    available = [line for line in lines if line.get("is_available")]
    subtotal = round(sum(float(line.get("line_total", 0)) for line in available), 2)
    new_courses = [line for line in available if not line.get("already_owned")]
    return CartSummary(
        item_count=sum(int(line.get("quantity", 0)) for line in available),
        subtotal=subtotal,
        total=subtotal,  # no tax, shipping or discounts in the demo store
        total_xp=sum(int(line.get("xp_reward", 0)) for line in available),
        courses_unlocked=len(new_courses),
        modules_unlocked=sum(int(line.get("module_count", 0)) for line in new_courses),
    )


# ---------------------------------------------------------------- change / remove
def update_quantity(course_id: int, quantity: int) -> ActionResult:
    """Set a line's quantity, kept between 1 and min(5, seats_available).

    If capped, ok=True with a message saying so. Story US-303 (U2-10).
    """
    try:
        if int(course_id) not in _current_quantities():
            return ActionResult(ok=False, message="That course is not in your cart.")
        course = _read_course(int(course_id))
        if course is None or not course.get("is_published"):
            return ActionResult(ok=False, message=NOT_AVAILABLE_MESSAGE)
        limit = _seat_limit(course.get("seats_available", 0))
        if limit == 0:
            return ActionResult(ok=False, message=f"Sorry, {course['title']} is sold out.")
        new_quantity = max(MIN_QUANTITY, min(int(quantity), limit))
        _save_quantity(int(course_id), new_quantity, already_in_cart=True)
    except Exception as error:
        logger.warning("cart.update_quantity failed: %s", type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_CART_ERROR)

    if new_quantity < int(quantity):
        message = f"You can have at most {new_quantity} seat(s) of {course['title']}."
    else:
        message = f"{course['title']}: {new_quantity} seat(s)."
    return ActionResult(ok=True, message=message, data={"quantity": new_quantity})


def remove_item(course_id: int) -> ActionResult:
    """Remove a course from the cart. Story US-304 (U2-11)."""
    try:
        user_id = _user_id()
        if user_id is None:
            _guest_cart().pop(int(course_id), None)
        else:
            get_client().table("cart_items").delete().eq("user_id", user_id).eq(
                "course_id", int(course_id)
            ).execute()
    except Exception as error:
        logger.warning("cart.remove_item failed: %s", type(error).__name__)
        return ActionResult(ok=False, message=GENERIC_CART_ERROR)
    return ActionResult(ok=True, message="Removed from your cart.")


# ---------------------------------------------------------------- sign-in merge
def merge_guest_cart(user_id: str) -> ActionResult:
    """Move the session (guest) cart into cart_items after sign-in, adding quantities
    and capping them by US-303 rules, then empty the guest cart.

    Called once from auth.sign_in(). Story US-306 (U2-14).
    """
    guest = dict(st.session_state.get(GUEST_CART_KEY) or {})
    if not guest:
        return ActionResult(ok=True, message="")
    try:
        saved = _saved_quantities(user_id)
        table_rows_changed = 0
        for course_id, guest_quantity in guest.items():
            course = _read_course(int(course_id))
            if course is None or not course.get("is_published"):
                continue  # unavailable courses are dropped (RLS would refuse them anyway)
            limit = _seat_limit(course.get("seats_available", 0))
            if limit == 0:
                continue
            current = saved.get(int(course_id), 0)
            new_quantity = min(current + int(guest_quantity), limit)
            if new_quantity <= current:
                continue
            table = get_client().table("cart_items")
            if current:
                table.update({"quantity": new_quantity}).eq("user_id", user_id).eq(
                    "course_id", int(course_id)
                ).execute()
            else:
                table.insert(
                    {"user_id": user_id, "course_id": int(course_id), "quantity": new_quantity}
                ).execute()
            table_rows_changed += 1
    except Exception as error:
        # Sign-in must still work, so we only report the problem. The session cart is not
        # shown while signed in and sign-out clears it, so those items are effectively lost:
        # the message (shown by the sign-in page) asks the user to add them again.
        logger.warning("cart.merge_guest_cart failed: %s", type(error).__name__)
        return ActionResult(
            ok=False,
            message=(
                "Some courses from your cart could not be saved to your account. "
                "Please check your cart and add them again."
            ),
        )

    st.session_state[GUEST_CART_KEY] = {}
    message = "We added the courses from your cart." if table_rows_changed else ""
    return ActionResult(ok=True, message=message, data={"merged": table_rows_changed})
