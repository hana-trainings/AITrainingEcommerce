"""Page file paths, in ONE place.

Paths are relative to app/streamlit_app.py (that is how Streamlit resolves them).
Use these constants with st.page_link / st.switch_page instead of typing paths.
"""

HOME = "pages/home.py"
COURSES = "pages/courses.py"
COURSE_DETAIL = "pages/course_detail.py"
LEARNING_PATHS = "pages/learning_paths.py"
CART = "pages/cart.py"
SIGN_IN = "pages/sign_in.py"
REGISTER = "pages/register.py"

CHECKOUT = "pages/checkout.py"
ORDER_CONFIRMATION = "pages/order_confirmation.py"
MY_ORDERS = "pages/my_orders.py"
PASSPORT = "pages/passport.py"

ADMIN_DASHBOARD = "pages/admin_dashboard.py"
ADMIN_COURSES = "pages/admin_courses.py"
ADMIN_COURSE_FORM = "pages/admin_course_form.py"
ADMIN_CATEGORIES_PATHS = "pages/admin_categories_paths.py"
ADMIN_ORDERS = "pages/admin_orders.py"
ADMIN_STAFF = "pages/admin_staff.py"

# Query parameter names shared between pages.
COURSE_PARAM = "course"  # course slug, e.g. ?course=sql-for-analysts
ORDER_PARAM = "order"  # order id on the confirmation page
