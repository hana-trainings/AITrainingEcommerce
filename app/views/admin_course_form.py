"""Create / edit course form (doc 02 S13). Staff and owner only.

Stories: US-703 (U3-03) create, US-704 (U3-09) edit + image upload.
Open with ?course_id=<id> to edit; without it the form creates a new course.
The service validates everything again (never trust the form alone, NFR-SEC-13).
"""

import pandas as pd
import streamlit as st

from app.components.guards import guard_admin_page
from app.components.states import error_state, flash, not_found
from app.config import routes
from app.models.domain import COURSE_LEVELS, CourseInput
from app.services import admin
from app.utils.log import get_logger
from app.utils.text import escape_markdown

logger = get_logger(__name__)

user = guard_admin_page()  # stops the page for guests and customers

# Field messages kept across the rerun after "Save", tagged with the form they belong
# to, so the errors of one course never show up on another course's form.
ERRORS_KEY = "course_form_errors"


def current_errors() -> dict[str, str]:
    saved = st.session_state.get(ERRORS_KEY) or {}
    return saved.get("errors", {}) if saved.get("form") == form_key else {}


def remember_errors(errors: dict[str, str]) -> None:
    st.session_state[ERRORS_KEY] = {"form": form_key, "errors": errors}


def field_error(name: str) -> None:
    """Show the message for one field right under it (doc 02 S13)."""
    message = current_errors().get(name)
    if message:
        st.error(message, icon=":material/error:")


def lines(text: str) -> list[str]:
    """One list item per line, empty lines dropped."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def table_rows(frame: pd.DataFrame) -> list[dict]:
    """Rows of a data editor as plain dicts, without empty rows or NaN values."""
    rows = []
    for record in frame.to_dict("records"):
        clean = {key: (None if pd.isna(value) else value) for key, value in record.items()}
        if any(value not in (None, "") for value in clean.values()):
            rows.append(clean)
    return rows


# ---------------------------------------------------------------- which course?
raw_id = st.query_params.get(admin.EDIT_COURSE_PARAM)
course_id = int(raw_id) if raw_id and raw_id.isdigit() else None
course: dict = {}
try:
    if course_id is not None:
        course = admin.get_course_for_edit(course_id) or {}
    categories, paths = admin.list_categories_and_paths()
except Exception as error:  # never show technical details (NFR-SEC-17)
    logger.warning("course form: load failed %s", type(error).__name__)
    error_state()
    st.stop()

if course_id is not None and not course:
    not_found("Course")
    st.stop()

st.title("Edit course" if course else "New course")
st.page_link(routes.ADMIN_COURSES, label="Back to courses", icon=":material/arrow_back:")
if course:
    editor = admin.get_editor_name(course.get("updated_by")) or "the system"
    when = str(course.get("updated_at") or "")[:16].replace("T", " ")
    # US-704 AC3. Names come from the database, so escape them.
    st.caption(f"Last updated by {escape_markdown(editor)} at {when} UTC.")

category_names = {category["id"]: category["name"] for category in categories}
path_names = {path["id"]: path["name"] for path in paths}
path_ids_by_name = {name: path_id for path_id, name in path_names.items()}

if not category_names:
    st.warning("Create a category first on Categories & paths.", icon=":material/warning:")
    st.stop()

# ---------------------------------------------------------------- the form
form_key = f"course_form_{course_id or 'new'}"  # a fresh form for each course
with st.form(form_key):
    st.subheader("Basics")
    title = st.text_input("Title *", value=course.get("title", ""), max_chars=admin.TITLE_MAX)
    field_error("title")
    slug = st.text_input(
        "Slug",
        value=course.get("slug", ""),
        max_chars=admin.SLUG_MAX,
        help="The course's web address name. Leave empty to make it from the title.",
    )
    field_error("slug")
    summary = st.text_input(
        "Summary *", value=course.get("summary", ""), max_chars=admin.SUMMARY_MAX
    )
    field_error("summary")
    description = st.text_area(
        "Description *", value=course.get("description", ""), max_chars=admin.DESCRIPTION_MAX
    )
    field_error("description")
    instructor = st.text_input(
        "Instructor name", value=course.get("instructor_name") or "", max_chars=80
    )
    field_error("instructor_name")

    st.subheader("Pricing & seats")
    price = st.number_input(
        "Price in USD (demo) *",
        min_value=0.0,
        max_value=float(admin.PRICE_MAX),
        value=float(course.get("price", 0.0)),
        step=1.0,
        format="%.2f",
    )
    field_error("price")
    seats_total = st.number_input(
        "Total seats *",
        min_value=admin.SEATS_MIN,
        max_value=admin.SEATS_MAX,
        value=int(course.get("seats_total", 20)),
        step=1,
        help="On a new course every seat is available. Changing it later keeps sold seats sold.",
    )
    field_error("seats_total")
    duration = st.number_input(
        "Duration in hours *",
        min_value=0.5,
        max_value=float(admin.DURATION_MAX),
        value=float(course.get("duration_hours", 4.0)),
        step=0.5,
    )
    field_error("duration_hours")

    st.subheader("Content")
    outcomes = st.text_area(
        "Learning outcomes (one per line)", value="\n".join(course.get("outcomes") or [])
    )
    field_error("outcomes")
    prerequisites = st.text_area(
        "Prerequisites (one per line)", value="\n".join(course.get("prerequisites") or [])
    )
    field_error("prerequisites")
    st.caption("Modules, in order. Add a row for each module.")
    modules_frame = st.data_editor(
        pd.DataFrame(
            [
                {"title": module.get("title", ""), "description": module.get("description") or ""}
                for module in course.get("modules", [])
            ],
            columns=["title", "description"],
        ),
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "title": st.column_config.TextColumn("Module title", max_chars=admin.TITLE_MAX),
            "description": st.column_config.TextColumn(
                "Description", max_chars=admin.MODULE_DESCRIPTION_MAX
            ),
        },
        key=f"{form_key}_modules",
    )
    field_error("modules")

    st.subheader("Organization")
    current_category = course.get("category_id")
    category_id = st.selectbox(
        "Category *",
        list(category_names),
        index=list(category_names).index(current_category)
        if current_category in category_names
        else 0,
        format_func=lambda cid: category_names[cid],
    )
    field_error("category_id")
    level = st.segmented_control(
        "Level *", COURSE_LEVELS, default=course.get("level", COURSE_LEVELS[0])
    )
    field_error("level")
    tags = st.text_input(
        "Tags (comma separated)", value=", ".join(course.get("tags") or []), max_chars=400
    )
    field_error("tags")
    st.caption("Learning paths: pick a path and the step this course is in that path.")
    paths_frame = st.data_editor(
        pd.DataFrame(
            [
                {"path": path_names.get(link["path_id"], ""), "step": link["position"]}
                for link in course.get("paths", [])
            ],
            columns=["path", "step"],
        ),
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "path": st.column_config.SelectboxColumn(
                "Learning path", options=list(path_ids_by_name)
            ),
            "step": st.column_config.NumberColumn(
                "Step", min_value=1, max_value=admin.PATH_POSITION_MAX, step=1
            ),
        },
        key=f"{form_key}_paths",
    )
    field_error("path_positions")

    st.subheader("Media")
    if course.get("image_url"):
        st.image(course["image_url"], width=240, caption="Current image")
        remove_image = st.checkbox("Remove the current image")
    else:
        remove_image = False
    image_file = st.file_uploader(
        "Course image (JPG, PNG or WebP, up to 2 MB)", type=["jpg", "jpeg", "png", "webp"]
    )
    field_error("image_url")

    st.subheader("Visibility")
    featured = st.checkbox("Featured on the home page", value=bool(course.get("is_featured")))
    st.caption(
        "Currently published." if course.get("is_published") else "Currently a draft (hidden)."
    )
    with st.container(horizontal=True):
        save_draft = st.form_submit_button("Save as draft", icon=":material/save:")
        save_publish = st.form_submit_button(
            "Save and publish", type="primary", icon=":material/publish:"
        )

# ---------------------------------------------------------------- saving
if save_draft or save_publish:
    path_positions = []
    for row in table_rows(paths_frame):
        if row.get("path") in path_ids_by_name and row.get("step") is not None:
            path_positions.append(
                {"path_id": path_ids_by_name[row["path"]], "position": int(row["step"])}
            )
    data = CourseInput(
        title=title,
        slug=slug,
        summary=summary,
        description=description,
        category_id=category_id,
        level=level,  # type: ignore[typeddict-item]
        duration_hours=duration,
        price=price,
        seats_total=int(seats_total),
        instructor_name=instructor,
        outcomes=lines(outcomes),
        prerequisites=lines(prerequisites),
        modules=[
            {"title": str(row.get("title") or ""), "description": str(row.get("description") or "")}
            for row in table_rows(modules_frame)
        ],
        tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
        path_positions=path_positions,
        image_url=None if remove_image else course.get("image_url"),
        is_featured=featured,
        is_published=bool(save_publish),
    )

    # 1. Check the form first, so a form with mistakes never uploads a picture.
    form_errors = admin.validate_course_input(data)
    if form_errors:
        remember_errors(form_errors)
        st.rerun()  # draw each message next to its field

    # 2. Upload the new picture (type and size are checked in the service first).
    new_image_url = None
    if image_file is not None:
        upload = admin.upload_course_image(image_file.getvalue(), image_file.type or "")
        if not upload.ok:
            remember_errors({"image_url": upload.message})
            st.rerun()
        new_image_url = upload.data["image_url"]
        data["image_url"] = new_image_url

    # 3. Save. update_course also removes the old picture when it was replaced.
    result = admin.update_course(course["id"], data) if course else admin.create_course(data)

    if result.ok:
        st.session_state.pop(ERRORS_KEY, None)
        flash(result.message)
        if not course:
            st.query_params[admin.EDIT_COURSE_PARAM] = str(result.data["course_id"])
        st.rerun()  # show the saved course (a new course opens in edit mode)

    if new_image_url:
        admin.delete_course_image(new_image_url)  # not saved, so don't keep an unused file
    remember_errors(result.data.get("errors", {}))
    if current_errors():
        st.rerun()  # draw each message next to its field
    st.error(result.message, icon=":material/error:")
elif current_errors():
    st.error("Please fix the highlighted fields.", icon=":material/error:")
