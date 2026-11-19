"""Page file paths, in ONE place.

Paths are relative to app/streamlit_app.py (that is how Streamlit resolves them).
Use these constants with st.page_link / st.switch_page instead of typing paths.

Why the folder is called "views" and not "pages": if a folder named "pages" sits next
to the entry script, Streamlit starts in its OLD multipage mode after every restart and
can run a page without app/streamlit_app.py. Then "from app..." imports fail. Keep
the name "views".
"""

HOME = "views/home.py"
COURSES = "views/courses.py"
COURSE_DETAIL = "views/course_detail.py"
LEARNING_PATHS = "views/learning_paths.py"
CART = "views/cart.py"
SIGN_IN = "views/sign_in.py"
REGISTER = "views/register.py"

CHECKOUT = "views/checkout.py"
ORDER_CONFIRMATION = "views/order_confirmation.py"
MY_ORDERS = "views/my_orders.py"
PASSPORT = "views/passport.py"

ADMIN_DASHBOARD = "views/admin_dashboard.py"
ADMIN_COURSES = "views/admin_courses.py"
ADMIN_COURSE_FORM = "views/admin_course_form.py"
ADMIN_CATEGORIES_PATHS = "views/admin_categories_paths.py"
ADMIN_ORDERS = "views/admin_orders.py"
ADMIN_EMAILS = "views/admin_emails.py"
ADMIN_STAFF = "views/admin_staff.py"

# Query parameter names shared between pages.
COURSE_PARAM = "course"  # course slug, e.g. ?course=sql-for-analysts
ORDER_PARAM = "order"  # order id on the confirmation page
