"""Course catalog and search (doc 02 S2). Public.

Stories: US-101 browse (U1-03), US-102 keyword search (U1-05), US-103 filters
(U1-06), US-104 sort (U1-07), US-105 no results (U1-08), US-204 add to cart
from a card (U1-15).

How the page remembers things: every filter widget has a `key`, so its value
lives in st.session_state and survives reruns. Callbacks (on_click) change
those values BEFORE the widgets are drawn again, which is how "Clear filters"
and the removable chips work.
"""

import math

import streamlit as st

from app.components.course_card import add_course_to_cart, course_card, shopper_course_ids
from app.components.states import load_or_stop
from app.models.domain import COURSE_LEVELS, CourseFilters
from app.services import auth, catalog
from app.utils.text import escape_markdown

# ---------------------------------------------------------------- session keys
KEYWORD = "catalog_keyword"  # the search that was submitted
KEYWORD_BOX = "catalog_keyword_box"  # what is typed in the box
CATEGORIES = "catalog_categories"
LEVELS = "catalog_levels"
PRICE = "catalog_price"
DURATION = "catalog_duration"
PATH = "catalog_path"
ONLY_AVAILABLE = "catalog_only_available"
SORT = "catalog_sort"
PAGE = "catalog_page"
LAST_QUERY = "catalog_last_query"

user = auth.current_user()

st.title("Courses")
st.caption("Search, filter and sort every course. Prices are in demo dollars.")

categories = load_or_stop(catalog.list_categories, "courses page")
paths = load_or_stop(catalog.list_paths, "courses page")
bounds = load_or_stop(catalog.filter_bounds, "courses page")
max_price = int(math.ceil(bounds["max_price"]))
max_duration = int(math.ceil(bounds["max_duration"]))
category_names = {category["id"]: category["name"] for category in categories}
path_names = {path["id"]: path["name"] for path in paths}

# Defaults for every filter, so "clear" can put them back.
DEFAULTS = {
    CATEGORIES: [],
    LEVELS: [],
    PRICE: (0, max_price),
    DURATION: (0, max_duration),
    PATH: None,
    ONLY_AVAILABLE: False,
}


# ---------------------------------------------------------------- callbacks
def clear_filters(include_keyword: bool = False) -> None:
    """US-103 AC3 "Clear filters" (and US-105 "Clear filters" also clears the search)."""
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    if include_keyword:
        st.session_state[KEYWORD] = ""
        st.session_state[KEYWORD_BOX] = ""
    st.session_state[PAGE] = 1


def remove_filter(key: str) -> None:
    """Remove one active filter chip (US-103 AC4)."""
    st.session_state[key] = DEFAULTS[key]


def remove_keyword() -> None:
    st.session_state[KEYWORD] = ""
    st.session_state[KEYWORD_BOX] = ""


def change_page(step: int) -> None:
    st.session_state[PAGE] = max(1, st.session_state.get(PAGE, 1) + step)


for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)
st.session_state.setdefault(KEYWORD, "")
# Keep the submitted search visible in the box, also after visiting another page (US-102 AC3).
st.session_state.setdefault(KEYWORD_BOX, st.session_state[KEYWORD])
st.session_state.setdefault(SORT, "featured")
st.session_state.setdefault(PAGE, 1)

# The price/duration sliders must stay inside the real catalog range, even if
# the catalog changed since the value was stored.
for key, top in ((PRICE, max_price), (DURATION, max_duration)):
    low, high = st.session_state[key]
    st.session_state[key] = (max(0, min(low, top)), max(0, min(high, top)))

# ---------------------------------------------------------------- search box (US-102)
# A form sends the search only on Enter or the Search button (US-102 AC2).
with (
    st.form("catalog_search", border=False),
    st.container(horizontal=True, vertical_alignment="bottom"),
):
    st.text_input(
        "Search courses",
        key=KEYWORD_BOX,
        placeholder="Try python, SQL or ethics",
        max_chars=100,
        icon=":material/search:",
    )
    searched = st.form_submit_button("Search", type="primary", icon=":material/search:")
if searched:
    st.session_state[KEYWORD] = (st.session_state.get(KEYWORD_BOX) or "").strip()

# ---------------------------------------------------------------- filters (US-103)
with st.sidebar:
    st.header("Filters")
    st.multiselect(
        "Category",
        options=list(category_names),
        format_func=lambda category_id: category_names.get(category_id, "Unknown"),
        key=CATEGORIES,
        placeholder="All categories",
    )
    st.pills("Level", options=list(COURSE_LEVELS), selection_mode="multi", key=LEVELS)
    st.slider("Price (demo $)", min_value=0, max_value=max_price, key=PRICE, step=1)
    st.slider("Duration (hours)", min_value=0, max_value=max_duration, key=DURATION, step=1)
    st.selectbox(
        "Learning path",
        options=[None, *path_names],
        format_func=lambda path_id: "Any path" if path_id is None else path_names[path_id],
        key=PATH,
    )
    st.toggle("Only show available", key=ONLY_AVAILABLE, help="Hide sold-out courses.")
    st.button("Clear filters", icon=":material/filter_alt_off:", on_click=clear_filters)


def build_filters() -> CourseFilters:
    """Turn the widget values into the CourseFilters the service expects."""
    filters: CourseFilters = {}
    if st.session_state[CATEGORIES]:
        filters["category_ids"] = list(st.session_state[CATEGORIES])
    if st.session_state[LEVELS]:
        filters["levels"] = list(st.session_state[LEVELS])
    price_low, price_high = st.session_state[PRICE]
    if (price_low, price_high) != (0, max_price):
        filters["price_min"], filters["price_max"] = float(price_low), float(price_high)
    duration_low, duration_high = st.session_state[DURATION]
    if (duration_low, duration_high) != (0, max_duration):
        filters["duration_min"], filters["duration_max"] = (
            float(duration_low),
            float(duration_high),
        )
    if st.session_state[PATH] is not None:
        filters["path_id"] = st.session_state[PATH]
    if st.session_state[ONLY_AVAILABLE]:
        filters["only_available"] = True
    return filters


def active_chips() -> list[tuple[str, str]]:
    """(label, session key) for every active filter, for the removable chips."""
    chips = []
    if st.session_state[CATEGORIES]:
        names = ", ".join(category_names.get(cid, "?") for cid in st.session_state[CATEGORIES])
        chips.append((f"Category: {names}", CATEGORIES))
    if st.session_state[LEVELS]:
        chips.append((f"Level: {', '.join(st.session_state[LEVELS])}", LEVELS))
    if tuple(st.session_state[PRICE]) != (0, max_price):
        low, high = st.session_state[PRICE]
        chips.append((f"Price: ${low} to ${high}", PRICE))
    if tuple(st.session_state[DURATION]) != (0, max_duration):
        low, high = st.session_state[DURATION]
        chips.append((f"Duration: {low} to {high} h", DURATION))
    if st.session_state[PATH] is not None:
        chips.append((f"Path: {path_names.get(st.session_state[PATH], '?')}", PATH))
    if st.session_state[ONLY_AVAILABLE]:
        chips.append(("Only available", ONLY_AVAILABLE))
    return chips


keyword = st.session_state[KEYWORD]
filters = build_filters()

# ---------------------------------------------------------------- chips + sort
with st.container(horizontal=True, vertical_alignment="bottom"):
    chips = active_chips()
    if keyword:
        st.button(
            f"Search: {escape_markdown(keyword)}",
            key="chip_keyword",
            icon=":material/close:",
            help="Remove this search",
            on_click=remove_keyword,
        )
    for label, key in chips:
        # Chip labels contain category/path names from the database, so escape them.
        st.button(
            escape_markdown(label),
            key=f"chip_{key}",
            icon=":material/close:",
            help="Remove this filter",
            on_click=remove_filter,
            args=(key,),
        )
    st.space("stretch")
    st.selectbox(
        "Sort by",
        options=list(catalog.SORT_LABELS),
        format_func=lambda option: catalog.SORT_LABELS[option],
        key=SORT,
        width=220,
    )

# A new search, filter or sort starts again at page 1.
query_signature = repr((keyword, sorted(filters.items()), st.session_state[SORT]))
if st.session_state.get(LAST_QUERY) != query_signature:
    st.session_state[LAST_QUERY] = query_signature
    st.session_state[PAGE] = 1


def run_search() -> dict:
    return load_or_stop(
        lambda: catalog.search_courses(
            keyword=keyword,
            filters=filters,
            sort=st.session_state[SORT],
            page=st.session_state[PAGE],
        ),
        "courses page",
    )


results = run_search()
total = results["total"]
if not results["courses"] and total > 0:
    # The stored page is past the end (e.g. a course was unpublished meanwhile):
    # jump to the last real page instead of showing an empty grid with no way back.
    st.session_state[PAGE] = max(1, math.ceil(total / catalog.PAGE_SIZE))
    results = run_search()
    total = results["total"]
owned_ids, cart_ids = shopper_course_ids(user)

# ---------------------------------------------------------------- results count (US-102 AC3)
result_word = "result" if total == 1 else "results"
if keyword:
    st.markdown(f"**{total} {result_word} for '{escape_markdown(keyword)}'**")
else:
    st.markdown(f"**{total} {'course' if total == 1 else 'courses'}**")


def show_cards(courses: list, key_prefix: str) -> None:
    """A responsive grid: 3 cards per row on desktop, 1 per row on a phone."""
    grid = st.grid(3, min_column_width=260, gap="medium")
    for course in courses:
        with grid:
            clicked = course_card(
                course,
                owned=course["id"] in owned_ids,
                in_cart=course["id"] in cart_ids,
                key_prefix=key_prefix,
            )
        if clicked:
            add_course_to_cart(course)


# ---------------------------------------------------------------- no results (US-105)
if total == 0:
    with st.container(border=True):
        st.markdown("### :material/search_off: No courses match your search")
        st.markdown(
            "Try a shorter word, check the spelling, or clear the filters to see every course."
        )
        st.button(
            "Clear filters",
            key="no_results_clear",
            type="primary",
            icon=":material/filter_alt_off:",
            on_click=clear_filters,
            kwargs={"include_keyword": True},
        )
    st.subheader("You might like these")
    suggestions = load_or_stop(lambda: catalog.featured_courses(limit=3), "courses page")
    if len(suggestions) < 3:  # top up with other courses so there are always 3 ideas
        extra = load_or_stop(lambda: catalog.list_courses(page_size=6), "courses page")
        known = {course["id"] for course in suggestions}
        suggestions += [c for c in extra["courses"] if c["id"] not in known]
    show_cards(suggestions[:3], key_prefix="suggested")
    st.stop()

show_cards(results["courses"], key_prefix="results")

# ---------------------------------------------------------------- pagination (US-101 AC4)
page_count = max(1, math.ceil(total / catalog.PAGE_SIZE))
if page_count > 1:
    page = st.session_state[PAGE]
    with st.container(horizontal=True, horizontal_alignment="center", vertical_alignment="center"):
        st.button(
            "Previous",
            icon=":material/chevron_left:",
            disabled=page <= 1,
            on_click=change_page,
            args=(-1,),
        )
        st.markdown(f"Page {page} of {page_count}", width="content")
        st.button(
            "Next",
            icon=":material/chevron_right:",
            icon_position="right",
            disabled=page >= page_count,
            on_click=change_page,
            args=(1,),
        )
