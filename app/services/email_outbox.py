"""Order confirmation "emails" (US-406). Nothing is ever really sent.

The email is written to an HTML file in outbox/ (git-ignored) AND saved in the
email_outbox table, because cloud hosts may delete files on restart (NFR-DEP-04).
All order values put into the HTML must be escaped with html.escape (NFR-SEC-15).
"""

from app.models.domain import ActionResult, EmailRecord, Order

OUTBOX_FOLDER = "outbox"


def build_confirmation_email(order: Order, to_email: str, display_name: str) -> EmailRecord:
    """Return {"to_email", "subject", "html_body", "file_name"} for an order (pure, no DB).

    subject = "Your order ORD-YYYYMMDD-0042 is confirmed",
    file_name = "order_<order_number>_<yyyymmddHHMMSS>.html". Story US-406 (U2-06).
    """
    raise NotImplementedError("U2-06 US-406")


def save_confirmation_email(order_id: int) -> ActionResult:
    """Build the email, write the file to outbox/, and insert the email_outbox row.

    Must NEVER raise: if the file write fails, log a warning and still return
    ok=True when the table row was saved (US-406 AC5, NFR-REL-02). Story US-406 (U2-06).
    """
    raise NotImplementedError("U2-06 US-406")


def get_email_for_order(order_id: int) -> EmailRecord | None:
    """Return the saved email for an order (from the table), or None.

    Stories US-407 AC2 (U2-15), US-707 AC3 (U2-18).
    """
    raise NotImplementedError("U2-15 US-407")
