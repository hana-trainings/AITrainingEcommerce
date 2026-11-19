"""Email drafts (admin). Staff and owner only.

The app's own email service never sends anything: every email (welcome emails for
new accounts, order confirmations) is saved as a draft in the email_outbox table.
This page lets staff read those drafts. It only reads; nobody edits or sends here.
"""

import streamlit as st

from app.components.guards import guard_admin_page
from app.components.states import empty_state, error_state
from app.services import email_outbox, orders
from app.utils.log import get_logger
from app.utils.text import escape_markdown

logger = get_logger(__name__)

user = guard_admin_page()  # stops the page for guests and customers

st.title("Email drafts")
st.caption(
    "Every email the store creates is saved here as a draft. "
    "This is a demo: no email is ever really sent."
)

# ---------------------------------------------------------------- filter
TYPE_CHOICES = {"All": None} | {
    label: email_type for email_type, label in email_outbox.EMAIL_TYPE_LABELS.items()
}
type_label = st.segmented_control(
    "Type", list(TYPE_CHOICES), default="All", key="admin_emails_type"
)

try:
    drafts = email_outbox.list_drafts(email_type=TYPE_CHOICES.get(type_label or "All"))
except Exception as error:  # never show technical details (NFR-SEC-17)
    logger.warning("admin_emails: could not load drafts: %s", type(error).__name__)
    error_state()
    st.stop()

if not drafts:
    empty_state("No email drafts yet", "Drafts appear when someone registers or places an order.")
    st.stop()


def type_label_for(draft: dict) -> str:
    return email_outbox.EMAIL_TYPE_LABELS.get(draft.get("email_type", ""), "Email")


# ---------------------------------------------------------------- table
st.dataframe(
    [
        {
            "Type": type_label_for(draft),
            "To": draft.get("to_email", ""),
            "Subject": draft.get("subject", ""),
            "Created": orders.readable_date(draft.get("created_at", "")),
            "Status": str(draft.get("status", "draft")).title(),
        }
        for draft in drafts
    ],
    hide_index=True,
    alt="Saved email drafts",
)

# ---------------------------------------------------------------- preview
labels = {
    draft["id"]: f"{type_label_for(draft)} · {draft.get('to_email', '')}" for draft in drafts
}
selected_id = st.selectbox(
    "Open a draft",
    options=list(labels),
    format_func=lambda draft_id: labels[draft_id],
    key="admin_emails_selected",
)
selected = next(draft for draft in drafts if draft["id"] == selected_id)

with st.container(border=True):
    st.caption(
        f"To: {escape_markdown(selected.get('to_email', ''))} · "
        f"Subject: {escape_markdown(selected.get('subject', ''))}"
    )
    # Simple tags only, no attributes: links and forms in a stored row are inert.
    st.html(email_outbox.safe_preview_html(selected.get("html_body", "")))
