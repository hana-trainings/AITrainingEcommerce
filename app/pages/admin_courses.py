"""Admin course list (doc 02 S13). Staff and owner only.

Stories: US-702 (U3-01) list, US-705 (U3-06) publish/unpublish,
US-706 (U3-07) adjust seats, US-710 (U3-08) delete (owner only).
Plain styling, no gamification. Every action is checked again in the service and
by the database (RLS), so hiding a button is never the only protection.
"""

import streamlit as st

from app.components.guards import guard_admin_page
from app.components.states import empty_state, error_state, flash
from app.components.status_badge import status_badge
from app.config import routes
from app.services import admin
from app.utils.log import get_logger
from app.utils.text import escape_markdown, format_price

logger = get_logger(__name__)

user = guard_admin_page()  # stops the page for guests and customers

st.title("Manage courses")
st.page_link(routes.ADMIN_COURSE_FORM, label="New course", icon=":material/add:")

# ---------------------------------------------------------------- filters (US-702 AC2)
try:
    categories, _paths = admin.list_categories_and_paths()
except Exception as error:
    logger.warning("admin courses: categories failed %s", type(error).__name__)
    categories = []
category_names = {category["id"]: category["name"] for category in categories}

with st.container(horizontal=True, vertical_alignment="bottom"):
    search = st.text_input("Search by title", key="admin_course_search", max_chars=120)
    status_choice = st.segmented_control(
        "Status", ["All", "Published", "Draft"], default="All", key="admin_course_status"
    )
    category_id = st.selectbox(
        "Category",
        [None, *category_names],
        format_func=lambda cid: "All categories" if cid is None else category_names[cid],
        key="admin_course_category",
    )

published = {"Published": True, "Draft": False}.get(status_choice or "All")
try:
    courses = admin.list_courses(search=search, published=published, category_id=category_id)
except Exception as error:  # never show technical details (NFR-SEC-17)
    logger.warning("admin courses: list failed %s", type(error).__name__)
    error_state()
    st.stop()

if not courses:
    empty_state("No courses match.", "Try another search or filter.")
    st.stop()

# ---------------------------------------------------------------- table (US-702 AC1)
st.dataframe(
    [
        {
            "Image": course.get("image_url"),
            "Title": course["title"],
            "Category": course.get("category_name", ""),
            "Level": course.get("level", ""),
            "Price": format_price(course.get("price")),
            "Seats": f"{course['seats_available']} / {course['seats_total']}",
            "Published": bool(course.get("is_published")),
            "Featured": bool(course.get("is_featured")),
            "Last updated": str(course.get("updated_at") or "")[:16].replace("T", " "),
        }
        for course in courses
    ],
    hide_index=True,
    column_config={
        "Image": st.column_config.ImageColumn("Image", width="small"),
        "Published": st.column_config.CheckboxColumn("Published"),
        "Featured": st.column_config.CheckboxColumn("Featured"),
    },
)
st.caption(f"{len(courses)} course(s), including drafts.")

# ---------------------------------------------------------------- row actions
st.subheader("Course actions")
courses_by_id = {course["id"]: course for course in courses}
selected_id = st.selectbox(
    "Choose a course",
    list(courses_by_id),
    format_func=lambda cid: courses_by_id[cid]["title"],
    key="admin_course_selected",
)
course = courses_by_id[selected_id]

with st.container(border=True):
    st.markdown(f"**{escape_markdown(course['title'])}**")
    with st.container(horizontal=True, vertical_alignment="center"):
        status_badge("published" if course.get("is_published") else "draft")
        if course.get("is_featured"):
            status_badge("featured")
        if course["seats_available"] <= 0:
            status_badge("sold_out")
    st.caption(f"{course['seats_available']} of {course['seats_total']} seats available.")

    with st.container(horizontal=True):
        st.page_link(
            routes.ADMIN_COURSE_FORM,
            label="Edit",
            icon=":material/edit:",
            query_params={admin.EDIT_COURSE_PARAM: str(course["id"])},
        )
        # US-705: publish / unpublish. Orders are not affected (AC2).
        if course.get("is_published"):
            toggle_label, toggle_icon = "Unpublish", ":material/visibility_off:"
        else:
            toggle_label, toggle_icon = "Publish", ":material/visibility:"
        if st.button(toggle_label, icon=toggle_icon, key="admin_toggle_publish"):
            result = admin.set_published(course["id"], not course.get("is_published"))
            if result.ok:
                flash(result.message)
                st.rerun()
            st.error(result.message, icon=":material/error:")

# ---------------------------------------------------------------- adjust seats (US-706)
with st.expander("Adjust seats", icon=":material/event_seat:"):
    sold = course["seats_total"] - course["seats_available"]
    st.caption(
        f"{sold} seat(s) already sold. Use a positive number to add seats "
        "and a negative number to remove them."
    )
    with st.form("adjust_seats_form", clear_on_submit=True):
        change = st.number_input("Seats to add (+) or remove (-)", step=1, value=0, format="%d")
        reason = st.text_input("Reason", max_chars=admin.SEAT_REASON_MAX)
        adjust = st.form_submit_button("Save seat change", icon=":material/save:")
    if adjust:
        result = admin.adjust_seats(course["id"], int(change), reason)
        if result.ok:
            flash(result.message)
            st.rerun()
        st.error(result.message, icon=":material/error:")

# ---------------------------------------------------------------- delete (US-710, owner)
if user.role == "owner":  # convenience only; the service and RLS check the role again
    with st.expander("Delete course", icon=":material/delete:"):
        st.warning(
            "Deleting is permanent. Courses that have orders can't be deleted; "
            "unpublish them instead.",
            icon=":material/warning:",
        )
        with st.form("delete_course_form", clear_on_submit=True):
            typed = st.text_input("Type the course title to confirm", max_chars=120)
            delete = st.form_submit_button("Delete permanently", icon=":material/delete_forever:")
        if delete:
            result = admin.delete_course(course["id"], typed)
            if result.ok:
                flash(result.message)
                st.session_state.pop("admin_course_selected", None)
                st.rerun()
            st.error(result.message, icon=":material/error:")
