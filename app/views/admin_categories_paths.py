"""Manage categories and learning paths (US-711, U3-12). Staff and owner only.

Plain styling, no gamification. The service checks the role again and the
database RLS policies are the real protection.
"""

import streamlit as st

from app.components.guards import guard_admin_page
from app.components.states import error_state, flash
from app.services import admin
from app.utils.log import get_logger
from app.utils.text import escape_markdown

logger = get_logger(__name__)

user = guard_admin_page()  # stops the page for guests and customers

st.title("Categories & paths")

try:
    categories, paths = admin.list_categories_and_paths()
    all_courses = admin.list_courses()
    badge_names = admin.badge_names()
except Exception as error:  # never show technical details (NFR-SEC-17)
    logger.warning("categories/paths: load failed %s", type(error).__name__)
    error_state()
    st.stop()

NEW = 0  # "create a new one" in the pickers below (real ids start at 1)


def show_result(result) -> None:
    """Toast + reload on success, error message otherwise."""
    if result.ok:
        flash(result.message)
        st.rerun()
    st.error(result.message, icon=":material/error:")


categories_tab, paths_tab = st.tabs(["Categories", "Learning paths"])

# ---------------------------------------------------------------- categories (AC1)
with categories_tab:
    if categories:
        st.dataframe(
            [
                {"Icon": row["icon"], "Name": row["name"], "Sort order": row["sort_order"]}
                for row in categories
            ],
            hide_index=True,
        )
    categories_by_id = {row["id"]: row for row in categories}
    picked_category = st.selectbox(
        "Category to edit",
        [NEW, *categories_by_id],
        format_func=lambda cid: "New category" if cid == NEW else categories_by_id[cid]["name"],
        key="category_picker",
    )
    current = categories_by_id.get(picked_category, {})
    with st.form(f"category_form_{picked_category}"):
        name = st.text_input(
            "Name", value=current.get("name", ""), max_chars=admin.CATEGORY_NAME_MAX
        )
        icon = st.text_input(
            "Icon (one emoji)", value=current.get("icon", "📘"), max_chars=admin.ICON_MAX
        )
        sort_order = st.number_input(
            "Sort order", min_value=0, step=1, value=int(current.get("sort_order", 0))
        )
        save_category = st.form_submit_button(
            "Save category", type="primary", icon=":material/save:"
        )
    if save_category:
        show_result(admin.save_category(name, icon, int(sort_order), picked_category or None))

# ---------------------------------------------------------------- learning paths (AC2)
with paths_tab:
    for path in paths:
        titles = [escape_markdown(course["title"]) for course in path.get("courses", [])]
        with st.container(border=True):
            st.markdown(f"**{escape_markdown(path['name'])}**")
            st.caption(" → ".join(titles) if titles else "No courses yet.")

    paths_by_id = {path["id"]: path for path in paths}
    course_titles = {course["id"]: course["title"] for course in all_courses}
    picked_path = st.selectbox(
        "Learning path to edit",
        [NEW, *paths_by_id],
        format_func=lambda pid: "New learning path" if pid == NEW else paths_by_id[pid]["name"],
        key="path_picker",
    )
    current_path = paths_by_id.get(picked_path, {})
    current_badge = badge_names.get(current_path.get("badge_code") or "", "")
    with st.form(f"path_form_{picked_path}"):
        path_name = st.text_input(
            "Name", value=current_path.get("name", ""), max_chars=admin.PATH_NAME_MAX
        )
        path_description = st.text_area(
            "Description",
            value=current_path.get("description", ""),
            max_chars=admin.PATH_DESCRIPTION_MAX,
        )
        ordered_courses = st.multiselect(
            "Courses, in order",
            list(course_titles),
            default=[
                course["id"]
                for course in current_path.get("courses", [])
                if course["id"] in course_titles
            ],
            format_func=lambda cid: course_titles[cid],
            help="The order you pick them in is the order of the path. "
            "To reorder, remove a course and add it again.",
        )
        badge_name = st.text_input(
            "Completion badge name",
            value=current_badge or "Path Master: ",
            max_chars=admin.BADGE_NAME_MAX,
        )
        save_path = st.form_submit_button("Save path", type="primary", icon=":material/save:")
    if save_path:
        show_result(
            admin.save_path(
                path_name, path_description, list(ordered_courses), badge_name, picked_path or None
            )
        )
