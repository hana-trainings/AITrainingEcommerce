"""Order confirmation "emails" (US-406). Nothing is ever really sent.

The email is written to an HTML file in outbox/ (git-ignored) AND saved in the
email_outbox table, because cloud hosts may delete files on restart (NFR-DEP-04).
All order values put into the HTML must be escaped with html.escape (NFR-SEC-15).
"""

import html
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

from app.models.domain import ActionResult, EmailRecord, Order
from app.services import auth, orders
from app.services.supabase_client import get_client
from app.utils.log import get_logger
from app.utils.text import format_price

logger = get_logger(__name__)

OUTBOX_FOLDER = "outbox"
# outbox/ at the repo root, whatever folder the app was started from.
OUTBOX_PATH = Path(__file__).resolve().parents[2] / OUTBOX_FOLDER
DEMO_FOOTER = "This is a demo store. No payment was taken and no real email was sent."


def _safe_file_part(text: str) -> str:
    """Keep only letters, digits, "-" and "_" (the table only accepts safe file names)."""
    return re.sub(r"[^A-Za-z0-9_-]", "", text)[:60] or "order"


def _readable_date(timestamp: str) -> str:
    """'2026-11-01T10:00:00+00:00' -> '1 Nov 2026, 10:00 UTC' (falls back to the raw text)."""
    try:
        moment = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    except ValueError:
        return str(timestamp)
    return moment.astimezone(UTC).strftime("%d %b %Y, %H:%M UTC").lstrip("0")


def _item_rows(order: Order) -> str:
    """One escaped HTML table row per order item."""
    rows = []
    for item in order.get("items", []):
        line_total = float(item["unit_price"]) * int(item["quantity"])
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item['title_snapshot']))}</td>"
            f"<td style='text-align:center'>{int(item['quantity'])}</td>"
            f"<td style='text-align:right'>{html.escape(format_price(item['unit_price']))}</td>"
            f"<td style='text-align:right'>{html.escape(format_price(line_total))}</td>"
            "</tr>"
        )
    return "".join(rows)


def build_confirmation_email(order: Order, to_email: str, display_name: str) -> EmailRecord:
    """Return {"to_email", "subject", "html_body", "file_name"} for an order (pure, no DB).

    subject = "Your order ORD-YYYYMMDD-0042 is confirmed",
    file_name = "order_<order_number>_<yyyymmddHHMMSS>.html". Story US-406 (U2-06).
    """
    number = str(order.get("order_number", ""))
    subject = f"Your order {number} is confirmed"
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    file_name = f"order_{_safe_file_part(number)}_{stamp}.html"
    e = html.escape  # short name: EVERY value from the user or database goes through it
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{e(subject)}</title></head>
<body style="font-family: Arial, sans-serif; color: #0F172A; background: #F8FAFC; padding: 16px;">
<div style="max-width: 600px; margin: auto; background: #FFFFFF; padding: 24px;">
<p><strong>To:</strong> {e(to_email)}<br><strong>Subject:</strong> {e(subject)}</p>
<h1 style="color: #4F46E5; font-size: 24px;">SkillForge Academy</h1>
<p>Hi {e(display_name or "learner")},</p>
<p>Thank you! Your order is confirmed.</p>
<p><strong>Order number:</strong> {e(number)}<br>
<strong>Date:</strong> {e(_readable_date(order.get("created_at", "")))}</p>
<table style="width: 100%; border-collapse: collapse;">
<thead><tr><th style="text-align:left">Course</th><th>Seats</th>
<th style="text-align:right">Price</th><th style="text-align:right">Line total</th></tr></thead>
<tbody>{_item_rows(order)}</tbody>
</table>
<p><strong>Total:</strong> {e(format_price(order.get("total")))}</p>
<p><strong>XP earned:</strong> +{int(order.get("xp_awarded") or 0)} XP</p>
<hr><p style="color: #475569; font-size: 14px;">{e(DEMO_FOOTER)}</p>
</div></body></html>
"""
    return EmailRecord(to_email=to_email, subject=subject, html_body=body, file_name=file_name)


def _write_file(email: EmailRecord) -> bool:
    """Write the email to outbox/<file_name>. Returns False (and logs) if that fails."""
    try:
        OUTBOX_PATH.mkdir(parents=True, exist_ok=True)
        (OUTBOX_PATH / email["file_name"]).write_text(email["html_body"], encoding="utf-8")
        return True
    except OSError as error:
        logger.warning("email file write failed: %s", type(error).__name__)  # US-406 AC5
        return False


def _is_duplicate(error: Exception) -> bool:
    """True for Postgres "unique violation" (23505): this order already has its email (0020)."""
    code = str(getattr(error, "code", "") or "")
    return code == "23505" or "duplicate key" in str(error).lower()


def save_confirmation_email(order_id: int) -> ActionResult:
    """Build the email, write the file to outbox/, and insert the email_outbox row.

    Must NEVER raise: if the file write fails, log a warning and still return
    ok=True when the table row was saved (US-406 AC5, NFR-REL-02). Story US-406 (U2-06).
    Only ONE email per order is kept (unique order_id, migration 0020).
    """
    saved = ActionResult(ok=True, message="Confirmation email saved.")
    failed = ActionResult(
        ok=False, message="Your order is confirmed, but we could not save the email copy."
    )
    try:
        user = auth.current_user()
        if user is None:
            return ActionResult(ok=False, message="Please sign in.")
        if get_email_for_order(order_id) is not None:
            # A repeated checkout call (same idempotency key) must not save a second email.
            return saved
        order = orders.get_order(order_id)
        if order is None:
            return ActionResult(ok=False, message="We could not save the confirmation email.")
        email = build_confirmation_email(order, user.email, user.display_name)
    except Exception as error:  # the order is already placed: never fail it here
        logger.warning(
            "confirmation email not built: order_id=%s %s", order_id, type(error).__name__
        )
        return failed

    try:
        get_client().table("email_outbox").insert(
            {
                "order_id": int(order_id),
                "user_id": user.id,
                "to_email": email["to_email"],
                "subject": email["subject"],
                "html_body": email["html_body"],
                "file_name": email["file_name"],
            }
        ).execute()
    except Exception as error:
        if _is_duplicate(error):  # saved a moment ago by another call: that is fine
            return saved
        logger.warning(
            "confirmation email not saved: order_id=%s %s", order_id, type(error).__name__
        )
        return failed

    file_ok = _write_file(email)  # a failed file write never fails the order (US-406 AC5)
    logger.info("confirmation email saved: order_id=%s file_written=%s", order_id, file_ok)
    return ActionResult(ok=True, message=saved.message, data={"file_written": file_ok})


def get_email_for_order(order_id: int) -> EmailRecord | None:
    """Return the saved email for an order (from the table), or None.

    Stories US-407 AC2 (U2-15), US-707 AC3 (U2-18).
    """
    response = (
        get_client()
        .table("email_outbox")
        .select("id, order_id, user_id, to_email, subject, html_body, file_name, created_at")
        .eq("order_id", int(order_id))
        # The OLDEST row is the one the app saved at checkout (only one is allowed, 0020).
        .order("id")
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None  # type: ignore[return-value]


# ---------------------------------------------------------------- safe preview
# Simple layout tags only. Every attribute is dropped, so links (href), forms (action),
# images (src) and styles can't do anything: the preview is inert even if a stored row
# was written by someone else through the API.
_PREVIEW_TAGS = {
    "p", "br", "hr", "strong", "b", "em", "i", "h1", "h2", "h3",
    "table", "thead", "tbody", "tr", "th", "td", "ul", "ol", "li", "div", "span",
}  # fmt: skip
_VOID_TAGS = {"br", "hr"}
_DROP_CONTENT_TAGS = {"script", "style", "title", "head", "template", "noscript"}


class _PreviewCleaner(HTMLParser):
    """Rebuilds HTML keeping only _PREVIEW_TAGS, without attributes; text is escaped."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0  # > 0 while inside <script>, <style>, ...

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _DROP_CONTENT_TAGS:
            self.skip_depth += 1
        elif tag in _PREVIEW_TAGS and not self.skip_depth:
            self.parts.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        if tag in _DROP_CONTENT_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag in _PREVIEW_TAGS and tag not in _VOID_TAGS and not self.skip_depth:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(html.escape(data))


def safe_preview_html(html_body: str) -> str:
    """Return a stored email as inert HTML for st.html previews (US-407 AC2, US-707 AC3)."""
    cleaner = _PreviewCleaner()
    cleaner.feed(str(html_body or ""))
    cleaner.close()
    return "".join(cleaner.parts)
