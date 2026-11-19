"""Course detail (doc 02 S4). Public.

Reads the course slug from st.query_params[routes.COURSE_PARAM].

Stories: US-201 details (U1-04), US-202 locked syllabus preview (U1-10),
US-203 seat meter (U1-11), US-205 related courses / next in path (U1-12),
US-204 add to cart (U1-15).
"""

import streamlit as st

from app.components.course_card import (
    add_course_to_cart,
    course_card,
    course_image,
    level_tag,
    shopper_course_ids,
)
from app.components.path_map import path_node_map, path_nodes_for
from app.components.seat_meter import seat_meter, seat_state
from app.components.states import load_or_stop, not_found
from app.components.xp import xp_pill
from app.config import routes
from app.models.domain import ADMIN_ROLES, Course
from app.services import auth, catalog
from app.utils.text import escape_markdown, format_price

user = auth.current_user()
# Staff and owner may preview drafts (US-201 AC4). RLS enforces this again in the database.
is_staff = user is not None and user.role in ADMIN_ROLES

slug = st.query_params.get(routes.COURSE_PARAM, "")
course = load_or_stop(
    lambda: catalog.get_course(slug, include_unpublished=is_staff), "course detail"
)
if course is None:
    st.title("Course not found")
    not_found("Course")
    st.stop()

owned_ids, cart_ids = shopper_course_ids(user)
is_owned = course["id"] in owned_ids
is_in_cart = course["id"] in cart_ids
seats_available = int(course.get("seats_available") or 0)
seats_total = int(course.get("seats_total") or 0)


def buy_box(course: Course) -> None:
    """Price, XP, seats and the main action (doc 02 S4 "above the fold")."""
    with st.container(border=True):
        st.markdown(f"## {format_price(course.get('price'))}")
        xp_pill(int(course.get("xp_reward") or 0))
        st.caption(
            f"Earn +{int(course.get('xp_reward') or 0)} XP the first time you unlock this course."
        )
        seat_meter(seats_available, seats_total)  # US-203: real numbers from the database
        if is_owned:
            st.success(
                "You own this course. All modules are unlocked.", icon=":material/lock_open:"
            )
        elif not course.get("is_published", True):
            # Staff draft preview: a draft is not for sale (the cart would refuse it anyway).
            st.button(
                "Draft: not for sale",
                key="detail_draft",
                icon=":material/edit_note:",
                disabled=True,
                width="stretch",
            )
        elif is_in_cart:
            st.page_link(routes.CART, label="In cart · View cart", icon=":material/shopping_cart:")
        elif seat_state(seats_available, seats_total) == "sold_out":
            st.button("Sold out", icon=":material/block:", disabled=True, width="stretch")
        elif st.button(
            "Add to cart",
            key="detail_add",
            type="primary",
            icon=":material/add_shopping_cart:",
            width="stretch",
        ):
            add_course_to_cart(course)  # US-204
        for path in course.get("paths", []):
            st.caption(
                f":material/route: Course {path['position']} of {path['course_count']} in "
                f"{escape_markdown(path['path_name'])}"
            )


def syllabus(course: Course) -> None:
    """US-202: module 1 in full, the rest locked until the course is owned."""
    modules = course.get("modules", [])
    st.subheader("Syllabus")
    if not modules:
        st.caption("The syllabus will be published soon.")
        return
    for index, module in enumerate(modules):
        title = escape_markdown(module.get("title", ""))
        with st.container(border=True):
            if is_owned or index == 0:
                st.markdown(f":material/play_circle: **Module {index + 1}: {title}**")
                if module.get("description"):
                    st.markdown(escape_markdown(module["description"]))
                if is_owned:
                    st.badge("Unlocked", icon=":material/lock_open:", color="green")
                else:
                    st.badge("Free preview", icon=":material/visibility:", color="blue")
            else:
                # Title only + lock icon + words (never color alone, doc 02 section 8).
                st.markdown(f":material/lock: **Module {index + 1}: {title}**")
                st.caption("Unlock with this course")


def bullet_list(heading: str, items: list[str], icon: str, empty_text: str) -> None:
    st.subheader(heading)
    if not items:
        st.caption(empty_text)
        return
    for item in items:
        st.markdown(f"{icon} {escape_markdown(item)}")


# ---------------------------------------------------------------- above the fold
if not course.get("is_published", True):
    st.warning(
        "Draft preview: only staff can see this course until it is published.",
        icon=":material/visibility:",
    )

st.title(escape_markdown(course.get("title", "Course")))  # DB text: escape Markdown
with st.container(horizontal=True, gap="small"):
    level_tag(course.get("level", ""))
    st.badge(
        escape_markdown(course.get("category_name", "")), icon=":material/category:", color="gray"
    )
    st.badge(
        f"{float(course.get('duration_hours') or 0):g} hours",
        icon=":material/schedule:",
        color="gray",
    )
    if course.get("instructor_name"):
        st.badge(
            f"Instructor: {escape_markdown(course['instructor_name'])}",
            icon=":material/person:",
            color="gray",
        )

main_column, side_column = st.columns([3, 2], gap="large")
with main_column:
    course_image(course)
    st.markdown(f"**{escape_markdown(course.get('summary', ''))}**")
with side_column:
    buy_box(course)

# ---------------------------------------------------------------- below the fold
st.subheader("About this course")
st.markdown(escape_markdown(course.get("description", "")))

learn_column, prereq_column = st.columns(2, gap="large")
with learn_column:
    bullet_list(
        "What you'll learn",
        course.get("outcomes") or [],
        ":material/check_circle:",
        "Learning outcomes will be added soon.",
    )
with prereq_column:
    bullet_list(
        "Prerequisites",
        course.get("prerequisites") or [],
        ":material/arrow_right:",
        "None. This is a great place to start.",
    )

syllabus(course)

# ---------------------------------------------------------------- path map + next step (US-205)
if course.get("paths"):
    st.subheader("Where this fits in your path")
    all_paths = {path["id"]: path for path in load_or_stop(catalog.list_paths, "course detail")}
    for path_info in course["paths"]:
        path = all_paths.get(path_info["path_id"])
        if path is None:
            continue
        nodes = path_nodes_for(path, owned_ids, cart_ids)
        path_node_map(path["name"], nodes, bonus_xp=int(path.get("bonus_xp") or 0))
        next_course = catalog.next_course_in_path(path["id"], course["id"])
        if next_course is not None:
            st.page_link(
                routes.COURSE_DETAIL,
                label=f"Next in {escape_markdown(path['name'])}: "
                f"{escape_markdown(next_course['title'])}",
                icon=":material/arrow_forward:",
                query_params={routes.COURSE_PARAM: next_course["slug"]},
            )

related = load_or_stop(lambda: catalog.related_courses(course["id"], limit=4), "course detail")
if related:
    st.subheader("Related courses")
    grid = st.grid(4, min_column_width=240, gap="medium")
    for related_course in related:
        with grid:
            clicked = course_card(
                related_course,
                owned=related_course["id"] in owned_ids,
                in_cart=related_course["id"] in cart_ids,
                key_prefix="related",
            )
        if clicked:
            add_course_to_cart(related_course)
