"""Store header shown above every page (doc 02 section 5.2).

Store name, demo ribbon, cart count, and Sign in button or account area with
the level chip and XP bar (US-602, U1-17).

The header runs on EVERY page, so a problem in one widget (for example the cart
service is down) must never break the page. Each widget that calls another
service is wrapped and simply shows nothing (or 0) if that call fails.
"""

import streamlit as st

from app.components.states import show_flash
from app.components.xp import level_chip, xp_bar, xp_progress_text
from app.config import routes
from app.models.domain import ADMIN_ROLES, CurrentUser, LevelProgress
from app.services import auth, cart, gamification
from app.utils.log import get_logger
from app.utils.text import escape_markdown

logger = get_logger(__name__)

STORE_NAME = "SkillForge Academy"
DEMO_NOTICE = "Demo store – no real payments"
GUEST_XP_HINT = "Sign up to start earning XP"


def _cart_count() -> int:
    """Seats in the cart for the header badge (US-301 AC3). 0 if the cart can't be read."""
    try:
        return int(cart.get_item_count())
    except NotImplementedError:
        return 0
    except Exception:  # the header must never break the page
        logger.warning("cart count unavailable in header", exc_info=True)
        return 0


def cart_label(count: int) -> str:
    """ "Cart (3)": the number is in the text, so it is not shown by color alone."""
    return f"Cart ({count})"


def _level_progress(user: CurrentUser) -> LevelProgress | None:
    """The user's level and XP progress, or None if it can't be worked out right now."""
    try:
        return gamification.get_level_progress(user.xp_total)
    except NotImplementedError:
        return None
    except Exception:  # the header must never break the page
        logger.warning("level progress unavailable in header", exc_info=True)
        return None


def _level_widgets(progress: LevelProgress) -> None:
    """Level chip + XP bar to the next level (US-602 AC1)."""
    level_chip(progress["level"], progress["name"])
    xp_bar(progress["xp_total"], progress["level_start_xp"], progress["next_level_xp"])


def _account_menu(user: CurrentUser, progress: LevelProgress | None) -> None:
    with st.popover(escape_markdown(user.display_name), icon=":material/account_circle:"):
        if progress is not None:
            st.caption(
                xp_progress_text(
                    progress["xp_total"],
                    progress["next_level_xp"],
                    progress.get("next_level_name") or "",
                )
            )
        st.page_link(routes.PASSPORT, label="Learner Passport", icon=":material/badge:")
        st.page_link(routes.MY_ORDERS, label="My orders", icon=":material/receipt_long:")
        if user.role in ADMIN_ROLES:
            st.page_link(
                routes.ADMIN_DASHBOARD, label="Admin", icon=":material/admin_panel_settings:"
            )
        if st.button("Sign out", icon=":material/logout:", key="header_sign_out"):
            auth.sign_out()
            st.switch_page(routes.HOME)


def _header_xp(progress: LevelProgress | None) -> None:
    """Small level chip and XP text always visible in the header row (doc 02 section 5.2)."""
    if progress is None:
        return
    with st.container(width=240, gap="small"):
        _level_widgets(progress)


def render_header(user: CurrentUser | None) -> None:
    """Draw the header. `user` is None for guests."""
    show_flash()
    progress = _level_progress(user) if user is not None else None
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(f"### :material/school: {STORE_NAME}")
        st.space("stretch")
        st.badge(DEMO_NOTICE, icon=":material/info:", color="blue")
        if user is None:
            st.page_link(routes.REGISTER, label=GUEST_XP_HINT, icon=":material/bolt:")
        else:
            _header_xp(progress)
        st.page_link(routes.CART, label=cart_label(_cart_count()), icon=":material/shopping_cart:")
        if user is None:
            st.page_link(routes.SIGN_IN, label="Sign in", icon=":material/login:")
        else:
            _account_menu(user, progress)
