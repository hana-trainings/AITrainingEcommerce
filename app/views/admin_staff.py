"""Staff management (doc 02 S15). OWNER only (US-709, U3-10).

The owner switches users between customer and staff. The database enforces the
same rules (only the owner may change roles, the last owner can't be demoted)
and writes every change to the audit log (AC4).
"""

import streamlit as st

from app.components.guards import guard_owner_page
from app.components.states import empty_state, error_state, flash
from app.services import admin
from app.utils.log import get_logger
from app.utils.text import escape_markdown

logger = get_logger(__name__)

user = guard_owner_page()  # stops the page for everyone except the owner (AC3)

st.title("Staff management")
st.caption("Switch users between customer and staff. Every change is saved in the audit log.")

try:
    users = admin.list_users()
except Exception as error:  # never show technical details (NFR-SEC-17)
    logger.warning("staff page: list failed %s", type(error).__name__)
    error_state()
    st.stop()

if not users:
    empty_state("No users yet.")
    st.stop()

st.dataframe(
    [
        {
            "Name": row["display_name"],
            "Email": row["email"],
            "Role": row["role"],
            "Joined": row["created_at"][:10],
        }
        for row in users
    ],
    hide_index=True,
)

st.subheader("Change a role")
users_by_id = {row["id"]: row for row in users}
picked = st.selectbox(
    "User",
    list(users_by_id),
    format_func=lambda uid: f"{users_by_id[uid]['display_name']} ({users_by_id[uid]['role']})",
    key="staff_user_picker",
)
target = users_by_id[picked]

if target["role"] == "owner":
    # S15: a clear guard message instead of a control that would fail.
    st.info(
        "Owner accounts are managed by the trainer, and the last owner can't be demoted.",
        icon=":material/lock:",
    )
    st.stop()

new_role = "staff" if target["role"] == "customer" else "customer"
action = "Make staff" if new_role == "staff" else "Make customer"
st.caption(
    f"{escape_markdown(target['display_name'])} is now **{target['role']}**. "
    f"Staff can manage courses, categories, paths and orders."
)


@st.dialog("Confirm role change")
def confirm_role_change(user_id: str, name: str, role: str) -> None:
    st.write(f"Change {escape_markdown(name)} to **{role}**?")
    with st.container(horizontal=True):
        if st.button("Yes, change role", type="primary", key="confirm_role_yes"):
            result = admin.change_user_role(user_id, role)  # owner re-checked in the service
            if result.ok:
                flash(result.message)
                st.rerun()
            st.error(result.message, icon=":material/error:")
        if st.button("Cancel", key="confirm_role_cancel"):
            st.rerun()


if st.button(action, icon=":material/manage_accounts:", key="staff_change_role"):
    confirm_role_change(picked, target["display_name"], new_role)
