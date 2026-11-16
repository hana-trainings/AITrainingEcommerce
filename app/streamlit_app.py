"""SkillForge Academy - entry point. Run with:  streamlit run app/streamlit_app.py

What this file does on every run:
1. Checks the settings (stops with a clear message if keys are missing).
2. Registers EVERY page, grouped into Storefront / Account / Admin.
   Pages the current user may not use are registered as "hidden": they are not
   in the menu, but opening their URL still works and the page's guard shows
   "sign in" or "You don't have access". The menu is only convenience; every
   page checks the role itself.
3. Draws the header, then runs the chosen page.

Stories never need to edit this file: pages, services and the header already exist.
"""

import sys
from pathlib import Path

# `streamlit run app/streamlit_app.py` puts app/ on the import path, but our imports
# start with "app." (e.g. from app.services import auth), so add the repo root too.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st  # noqa: E402  (must come after the sys.path line above)

from app.components.header import STORE_NAME, render_header  # noqa: E402
from app.config import routes  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.models.domain import ADMIN_ROLES  # noqa: E402
from app.services import auth  # noqa: E402

st.set_page_config(page_title=STORE_NAME, page_icon=":material/school:", layout="wide")

get_settings()  # fail fast if SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY are missing (NFR-SEC-12)

user = auth.current_user()
role = user.role if user else None
is_signed_in = user is not None
is_admin = role in ADMIN_ROLES
is_owner = role == "owner"


def page(path: str, title: str, icon: str, help_text: str, show: bool = True, **extra):
    """Small helper so each page is one readable line below."""
    return st.Page(
        path,
        title=title,
        icon=icon,
        help=help_text,
        visibility="visible" if show else "hidden",
        **extra,
    )


pages = {
    "Storefront": [
        page(
            routes.HOME,
            "Home",
            ":material/home:",
            "Start here: featured courses and paths.",
            default=True,
        ),
        page(
            routes.COURSES, "Courses", ":material/school:", "Search, filter and sort all courses."
        ),
        page(
            routes.COURSE_DETAIL,
            "Course detail",
            ":material/description:",
            "One course.",
            show=False,
        ),
        page(
            routes.LEARNING_PATHS,
            "Learning paths",
            ":material/route:",
            "Paths shown as skill maps.",
        ),
        page(routes.CART, "Cart", ":material/shopping_cart:", "Courses you plan to unlock."),
        page(
            routes.SIGN_IN,
            "Sign in",
            ":material/login:",
            "Sign in to your account.",
            show=not is_signed_in,
        ),
        page(
            routes.REGISTER,
            "Register",
            ":material/person_add:",
            "Create an account.",
            show=not is_signed_in,
        ),
    ],
    "Account": [
        page(
            routes.CHECKOUT,
            "Checkout",
            ":material/shopping_cart_checkout:",
            "Review and place your order.",
            show=is_signed_in,
        ),
        page(
            routes.ORDER_CONFIRMATION,
            "Order confirmation",
            ":material/task_alt:",
            "Your new order.",
            show=False,
        ),
        page(
            routes.MY_ORDERS,
            "My orders",
            ":material/receipt_long:",
            "Your past orders.",
            show=is_signed_in,
        ),
        page(
            routes.PASSPORT,
            "Learner Passport",
            ":material/badge:",
            "Your XP, badges and paths.",
            show=is_signed_in,
        ),
    ],
    "Admin": [
        page(
            routes.ADMIN_DASHBOARD,
            "Dashboard",
            ":material/dashboard:",
            "Store summary.",
            show=is_admin,
        ),
        page(
            routes.ADMIN_COURSES,
            "Manage courses",
            ":material/list_alt:",
            "All courses, incl. drafts.",
            show=is_admin,
        ),
        page(
            routes.ADMIN_COURSE_FORM,
            "Course editor",
            ":material/edit_document:",
            "Create or edit a course.",
            show=is_admin,
        ),
        page(
            routes.ADMIN_CATEGORIES_PATHS,
            "Categories & paths",
            ":material/category:",
            "Organize the catalog.",
            show=is_admin,
        ),
        page(
            routes.ADMIN_ORDERS,
            "Orders",
            ":material/receipt:",
            "All customer orders.",
            show=is_admin,
        ),
        page(
            routes.ADMIN_STAFF,
            "Staff",
            ":material/manage_accounts:",
            "Change user roles (owner only).",
            show=is_owner,
        ),
    ],
}

current_page = st.navigation(pages, position="sidebar")
render_header(user)
current_page.run()
