"""Store header shown above every page (doc 02 section 5.2).

Store name, demo ribbon, cart count, and Sign in button or account menu.
It lives here (not in streamlit_app.py) so stories can improve it without
touching the entry point, e.g. U1-17 (XP bar + level chip) and U2-01 (cart count).
"""

import streamlit as st

from app.components.states import show_flash
from app.components.xp import level_chip, xp_bar
from app.config import routes
from app.models.domain import ADMIN_ROLES, CurrentUser
from app.services import auth, cart, gamification
from app.utils.text import escape_markdown

STORE_NAME = "SkillForge Academy"
DEMO_NOTICE = "Demo store – no real payments"


def _cart_count() -> int:
    # Until U2-01 (US-301) builds cart.get_item_count(), the header shows 0.
    try:
        return cart.get_item_count()
    except NotImplementedError:
        return 0


def _account_menu(user: CurrentUser) -> None:
    with st.popover(escape_markdown(user.display_name), icon=":material/account_circle:"):
        _level_widgets(user)
        st.page_link(routes.PASSPORT, label="Learner Passport", icon=":material/badge:")
        st.page_link(routes.MY_ORDERS, label="My orders", icon=":material/receipt_long:")
        if user.role in ADMIN_ROLES:
            st.page_link(
                routes.ADMIN_DASHBOARD, label="Admin", icon=":material/admin_panel_settings:"
            )
        if st.button("Sign out", icon=":material/logout:", key="header_sign_out"):
            auth.sign_out()
            st.switch_page(routes.HOME)


def _level_widgets(user: CurrentUser) -> None:
    # Until U1-17 (US-602) builds get_level_progress(), no level is shown.
    try:
        progress = gamification.get_level_progress(user.xp_total)
    except NotImplementedError:
        return
    level_chip(progress["level"], progress["name"])
    xp_bar(progress["xp_total"], progress["level_start_xp"], progress["next_level_xp"])


def render_header(user: CurrentUser | None) -> None:
    """Draw the header. `user` is None for guests."""
    show_flash()
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(f"### :material/school: {STORE_NAME}")
        st.space("stretch")
        st.badge(DEMO_NOTICE, icon=":material/info:", color="blue")
        st.page_link(routes.CART, label=f"Cart ({_cart_count()})", icon=":material/shopping_cart:")
        if user is None:
            st.page_link(routes.SIGN_IN, label="Sign in", icon=":material/login:")
        else:
            _account_menu(user)
