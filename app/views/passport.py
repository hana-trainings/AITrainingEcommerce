"""Learner Passport profile (doc 02 S10). Signed-in users only.

Stories: US-504 (U3-04) profile, US-601 (U3-13) XP history + toast,
US-603 (U3-14) badge shelf, US-605 setting (Reduce motion), US-606 ethical rules.

Everything shown here is the user's OWN data from the database: no comparisons
with other learners, no timers, no penalties (US-606).
"""

import streamlit as st

from app.components.badge import badge_medallion
from app.components.guards import guard_customer_page
from app.components.path_map import path_node_map
from app.components.states import empty_state, error_state, flash
from app.components.xp import level_chip, xp_bar
from app.config import routes
from app.services import gamification, profile
from app.utils.log import get_logger
from app.utils.text import escape_markdown

logger = get_logger(__name__)

user = guard_customer_page(return_to=routes.PASSPORT)  # stops the page for guests

st.title("Learner Passport")

try:
    my_profile = profile.get_my_profile()
except Exception as error:  # never show technical details (NFR-SEC-17)
    logger.warning("passport: profile load failed %s", type(error).__name__)
    my_profile = None
if my_profile is None:
    error_state()
    st.stop()

progress = gamification.get_level_progress(my_profile.get("xp_total", 0))
# Only preset avatar names are ever drawn, so nothing else can end up in the Markdown.
avatar = my_profile.get("avatar")
avatar = avatar if avatar in profile.AVATAR_CHOICES else "account_circle"

# ---------------------------------------------------------------- identity card
with st.container(border=True):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(f"## :material/{avatar}:", width="content")
        with st.container():
            st.markdown(f"### {escape_markdown(my_profile.get('display_name', ''))}")
            st.caption(escape_markdown(my_profile.get("email", "")))
    level_chip(progress["level"], progress["name"])
    xp_bar(progress["xp_total"], progress["level_start_xp"], progress["next_level_xp"])
    if progress["next_level_xp"] is not None:
        to_go = progress["next_level_xp"] - progress["xp_total"]
        st.caption(f"{to_go} XP to {progress['next_level_name']}.")

# ---------------------------------------------------------------- edit details
profile_complete = bool(my_profile.get("avatar")) and bool(my_profile.get("interests"))
with st.expander("Edit your details", icon=":material/edit:", expanded=not profile_complete):
    if not profile_complete:
        st.caption("Pick an avatar and 1-3 interests to complete your Passport and earn +25 XP.")
    with st.form("passport_form"):
        new_name = st.text_input(
            "Display name", value=my_profile.get("display_name", ""), max_chars=50
        )
        new_avatar = st.pills(
            "Avatar",
            profile.AVATAR_CHOICES,
            default=my_profile.get("avatar")
            if my_profile.get("avatar") in profile.AVATAR_CHOICES
            else None,
            format_func=lambda name: f":material/{name}: {name.replace('_', ' ').title()}",
            help="Pick a picture from the list. Photo uploads are not allowed.",
        )
        known_interests = [
            item for item in my_profile.get("interests", []) if item in profile.INTEREST_CHOICES
        ]
        new_interests = st.pills(
            "Interests (pick 1 to 3)",
            profile.INTEREST_CHOICES,
            selection_mode="multi",
            default=known_interests,
        )
        saved = st.form_submit_button("Save details", type="primary", icon=":material/save:")
    if saved:
        result = profile.update_profile(new_name, new_avatar or "", list(new_interests or []))
        if result.ok:
            # US-601 / US-603: tell the learner what the DATABASE just awarded (toast).
            parts = [result.message]
            if result.data.get("xp_awarded"):
                parts.append(f"+{result.data['xp_awarded']} XP")
            if result.data.get("new_badges"):
                parts.append("New badge unlocked: Identity Set")
            flash(" · ".join(parts))
            st.rerun()  # redraw the header and this page with the new numbers
        else:
            for message in result.data.get("errors", {}).values():
                st.error(message, icon=":material/error:")
            if not result.data.get("errors"):
                st.error(result.message, icon=":material/error:")

if my_profile.get("interests"):
    st.caption("Interests: " + escape_markdown(", ".join(my_profile["interests"])))

# ---------------------------------------------------------------- badge shelf (US-603)
st.subheader("Badges")
try:
    badges = gamification.list_badges_with_status()
except Exception as error:
    logger.warning("passport: badges failed %s", type(error).__name__)
    badges = []
if badges:
    earned_count = sum(1 for badge in badges if badge["earned"])
    st.caption(f"{earned_count} of {len(badges)} earned. Locked badges show how to unlock them.")
    columns = st.columns(4)
    for index, badge in enumerate(badges):
        with columns[index % 4]:
            badge_medallion(
                badge["name"],
                badge["description"],
                earned=badge["earned"],
                hint=badge["hint"],
                icon=badge["icon"] or ":material/workspace_premium:",
            )
else:
    st.caption("Badges are not available right now.")

# ---------------------------------------------------------------- path progress
st.subheader("Learning path progress")
try:
    paths = gamification.get_path_progress()
except Exception as error:
    logger.warning("passport: path progress failed %s", type(error).__name__)
    paths = []
if not paths:
    empty_state("No learning paths yet.", action_label="Browse courses", action_page=routes.COURSES)
for item in paths:
    path_node_map(
        item["path"].get("name", ""), item["nodes"], bonus_xp=item["path"].get("bonus_xp", 0)
    )

# ---------------------------------------------------------------- owned courses
st.subheader("My courses")
try:
    owned = gamification.list_my_owned_courses()
except Exception as error:
    logger.warning("passport: owned courses failed %s", type(error).__name__)
    owned = []
if owned:
    for course in owned:
        st.page_link(
            routes.COURSE_DETAIL,
            label=escape_markdown(course.get("title", "")),
            icon=":material/check_circle:",
            query_params={routes.COURSE_PARAM: course.get("slug", "")},
        )
else:
    empty_state(
        "You haven't unlocked any courses yet.",
        "Courses you buy appear here.",
        action_label="Browse courses",
        action_page=routes.COURSES,
        icon=":material/school:",
    )

# ---------------------------------------------------------------- XP history (US-601)
st.subheader("XP history")
try:
    events = gamification.list_my_xp_events()
except Exception as error:
    logger.warning("passport: xp history failed %s", type(error).__name__)
    events = []
if events:
    st.dataframe(
        [
            {
                "Date": event["created_at"][:10],
                "What you did": gamification.xp_action_label(event["action"]),
                "XP": f"+{event['points']}",
            }
            for event in events
        ],
        hide_index=True,
    )
else:
    st.caption("Your XP history will appear here.")

# ---------------------------------------------------------------- settings (US-605)
st.subheader("Settings")


def _save_reduce_motion() -> None:
    result = profile.set_reduce_motion(st.session_state["passport_reduce_motion"])
    if result.ok:
        st.toast(result.message, icon=":material/check_circle:")
    else:
        st.toast(result.message, icon=":material/error:")


st.toggle(
    "Reduce motion",
    value=profile.get_reduce_motion(),
    key="passport_reduce_motion",
    on_change=_save_reduce_motion,
    help="Turns off balloons and other celebrations.",
)
