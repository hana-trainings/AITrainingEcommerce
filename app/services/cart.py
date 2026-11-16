"""Shopping cart (Epic E3).

Where the cart lives:
- Guest: in st.session_state only (US-305 AC2), key GUEST_CART_KEY,
  as {course_id (int): quantity}.
- Signed in: in the cart_items table (primary key user_id + course_id), US-305.
The functions below hide that difference from pages.
"""

from app.models.domain import ActionResult, CartLine, CartSummary

GUEST_CART_KEY = "guest_cart"
MIN_QUANTITY = 1
MAX_QUANTITY = 5  # US-303 AC1


def add_item(course_id: int, quantity: int = 1) -> ActionResult:
    """Add a course (or +1 if already there, capped at MAX_QUANTITY and seats_available).

    Returns ActionResult with a toast message, ok=False if sold out.
    Story US-301 (U2-01); also used by US-204 (U1-15).
    """
    raise NotImplementedError("U2-01 US-301")


def get_item_count() -> int:
    """Return the number of seats in the cart for the header badge. Story US-301 AC3 (U2-01)."""
    raise NotImplementedError("U2-01 US-301")


def get_items() -> list[CartLine]:
    """Return cart lines with prices and seats re-read FRESH from the database (no cache).

    Lines whose course is unpublished or sold out have is_available=False and a
    `problem` text; they are excluded from checkout (US-307).
    Stories US-302 (U2-02), US-307 (U2-12), US-305 (U2-13).
    """
    raise NotImplementedError("U2-02 US-302")


def summarize(lines: list[CartLine]) -> CartSummary:
    """Return totals and the "Unlock preview" for the available lines (pure function, no DB).

    Story US-302 AC2 (U2-02).
    """
    raise NotImplementedError("U2-02 US-302")


def update_quantity(course_id: int, quantity: int) -> ActionResult:
    """Set a line's quantity, kept between 1 and min(5, seats_available).

    If capped, ok=True with a message saying so. Story US-303 (U2-10).
    """
    raise NotImplementedError("U2-10 US-303")


def remove_item(course_id: int) -> ActionResult:
    """Remove a course from the cart. Story US-304 (U2-11)."""
    raise NotImplementedError("U2-11 US-304")


def merge_guest_cart(user_id: str) -> ActionResult:
    """Move the session (guest) cart into cart_items after sign-in, adding quantities
    and capping them by US-303 rules, then empty the guest cart.

    Called once from auth.sign_in(). Story US-306 (U2-14).
    """
    raise NotImplementedError("U2-14 US-306")
