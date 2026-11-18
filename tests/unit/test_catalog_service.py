"""Unit tests for app/services/catalog.py (Storefront stories U1-03 to U1-14).

They use the fake Supabase client from tests/conftest.py. Sample published courses:
101 Python for Data Beginners (featured, 22/30 seats, $49, Beginner, Data Analytics)
102 SQL for Analysts          (3/30 seats -> "few", $79, Intermediate, Data Analytics)
103 Prompt Engineering        (featured, SOLD OUT, $39, Beginner, AI)
104 Intro to Neural Networks  (DRAFT: never visible to guests)
Path 1 "Data Analyst Path" = 101 then 102.
"""

import pytest

from app.services import catalog


def ids(courses):
    return [course["id"] for course in courses]


def add_course(fake_client, **overrides):
    """Add one more published course to the fake database."""
    course = {
        "id": 105,
        "slug": "data-viz",
        "title": "Data Visualization",
        "summary": "Charts.",
        "description": "Make honest charts.",
        "category_id": 2,
        "level": "Beginner",
        "duration_hours": 5,
        "price": 59.0,
        "seats_total": 40,
        "seats_available": 40,
        "tags": ["charts"],
        "image_url": None,
        "xp_reward": 100,
        "is_published": True,
        "is_featured": False,
    }
    course.update(overrides)
    fake_client.tables["courses"].append(course)
    return course


# ---------------------------------------------------------------- US-101 browse (U1-03)
def test_list_courses_shows_only_published_with_category(session_state):
    page = catalog.list_courses()

    assert page["total"] == 3
    assert 104 not in ids(page["courses"])  # AC1: drafts are hidden
    sql = next(course for course in page["courses"] if course["id"] == 102)
    assert sql["category_name"] == "Data Analytics"


def test_list_courses_pages_through_results(session_state):
    first = catalog.list_courses(page=1, page_size=2)
    second = catalog.list_courses(page=2, page_size=2)

    assert len(first["courses"]) == 2 and len(second["courses"]) == 1
    assert set(ids(first["courses"])) | set(ids(second["courses"])) == {101, 102, 103}
    assert first["total"] == second["total"] == 3


def test_list_courses_page_beyond_the_end_is_empty_and_bad_page_is_page_one(session_state):
    assert catalog.list_courses(page=9)["courses"] == []
    assert len(catalog.list_courses(page=0)["courses"]) == 3  # page 0 is treated as page 1


def test_list_courses_with_empty_catalog(session_state, fake_client):
    fake_client.tables["courses"] = []
    assert catalog.list_courses() == {"courses": [], "total": 0}


def test_database_error_is_raised_for_the_page_to_handle(session_state, fake_client):
    def broken_table(_name):
        raise ConnectionError("network down")

    fake_client.table = broken_table
    with pytest.raises(ConnectionError):
        catalog.list_courses()


# ---------------------------------------------------------------- US-102 keyword (U1-05)
def test_search_matches_title_case_insensitive_and_trims_spaces(session_state):
    page = catalog.search_courses("  sQl  ")
    assert ids(page["courses"]) == [102]
    assert page["total"] == 1


def test_search_matches_tags_summary_and_description(session_state):
    assert ids(catalog.search_courses("pandas")["courses"]) == [101]  # tag + description
    assert ids(catalog.search_courses("talk to ai")["courses"]) == [103]  # summary
    assert ids(catalog.search_courses("group by")["courses"]) == [102]  # description


def test_empty_search_shows_everything_and_unknown_word_shows_nothing(session_state):
    assert catalog.search_courses("   ")["total"] == 3
    assert catalog.search_courses("underwater basket weaving")["total"] == 0


def test_search_never_finds_drafts(session_state):
    assert catalog.search_courses("neural")["total"] == 0


# ---------------------------------------------------------------- US-103 filters (U1-06)
def test_filter_by_category_and_level(session_state):
    assert ids(catalog.search_courses(filters={"category_ids": [1]})["courses"]) == [103]
    beginner = catalog.search_courses(filters={"levels": ["Beginner"]})
    assert set(ids(beginner["courses"])) == {101, 103}


def test_filter_by_price_and_duration_ranges(session_state):
    cheap = catalog.search_courses(filters={"price_min": 0, "price_max": 50})
    assert set(ids(cheap["courses"])) == {101, 103}
    long = catalog.search_courses(filters={"duration_min": 7, "duration_max": 20})
    assert ids(long["courses"]) == [102]


def test_filter_by_path_and_only_available(session_state):
    in_path = catalog.search_courses(filters={"path_id": 1})
    assert set(ids(in_path["courses"])) == {101, 102}
    available = catalog.search_courses(filters={"only_available": True})
    assert 103 not in ids(available["courses"])  # sold out is hidden


def test_filters_and_keyword_combine_with_and(session_state):
    page = catalog.search_courses("python", filters={"levels": ["Intermediate"]})
    assert page["total"] == 0  # Python course is Beginner, so nothing matches both


def test_filter_that_matches_nothing(session_state):
    assert catalog.search_courses(filters={"category_ids": [999]})["total"] == 0


# ---------------------------------------------------------------- US-104 sort (U1-07)
def test_sort_by_price(session_state):
    assert ids(catalog.search_courses(sort="price_asc")["courses"]) == [103, 101, 102]
    assert ids(catalog.search_courses(sort="price_desc")["courses"]) == [102, 101, 103]


def test_sort_featured_first_then_by_title(session_state):
    # Featured: Prompt Engineering, Python for Data (by title), then SQL.
    assert ids(catalog.search_courses(sort="featured")["courses"]) == [103, 101, 102]


def test_sort_fewest_seats_puts_sold_out_last(session_state):
    assert ids(catalog.search_courses(sort="fewest_seats")["courses"]) == [102, 101, 103]


def test_sort_newest_uses_created_at(session_state, fake_client):
    for course in fake_client.tables["courses"]:
        course["created_at"] = f"2026-11-0{course['id'] - 100}T10:00:00+00:00"
    assert ids(catalog.search_courses(sort="newest")["courses"]) == [103, 102, 101]


# ---------------------------------------------------------------- categories
def test_list_categories_in_sort_order(session_state, fake_client):
    fake_client.tables["categories"].append(
        {"id": 3, "name": "Data Engineering", "icon": "x", "sort_order": 0}
    )
    assert [category["id"] for category in catalog.list_categories()] == [3, 1, 2]


def test_filter_bounds(session_state, fake_client):
    assert catalog.filter_bounds() == {"max_price": 79.0, "max_duration": 8.0}
    fake_client.tables["courses"] = []
    catalog.clear_cache()
    assert catalog.filter_bounds() == {"max_price": 1.0, "max_duration": 1.0}


# ---------------------------------------------------------------- US-201 detail (U1-04)
def test_get_course_with_modules_and_path_position(session_state, fake_client):
    fake_client.tables["course_modules"] = [
        {"id": 2, "course_id": 102, "position": 2, "title": "Joins", "description": "B"},
        {"id": 1, "course_id": 102, "position": 1, "title": "Select", "description": "A"},
    ]
    course = catalog.get_course("sql-for-analysts")

    assert course["title"] == "SQL for Analysts"
    assert [module["title"] for module in course["modules"]] == ["Select", "Joins"]
    assert course["paths"] == [
        {"path_id": 1, "path_name": "Data Analyst Path", "position": 2, "course_count": 2}
    ]


def test_get_course_hides_drafts_unless_staff_preview(session_state):
    assert catalog.get_course("neural-networks-draft") is None  # AC4
    preview = catalog.get_course("neural-networks-draft", include_unpublished=True)
    assert preview["is_published"] is False
    assert preview["category_name"] == "Artificial Intelligence"


def test_get_course_unknown_or_empty_slug(session_state):
    assert catalog.get_course("does-not-exist") is None
    assert catalog.get_course("") is None
    assert catalog.get_course("does-not-exist", include_unpublished=True) is None


def test_get_course_returns_a_copy_not_the_cached_data(session_state):
    course = catalog.get_course("sql-for-analysts")
    course["title"] = "Changed by a page"
    assert catalog.get_course("sql-for-analysts")["title"] == "SQL for Analysts"


# ---------------------------------------------------------------- US-106 home (U1-13)
def test_featured_courses(session_state):
    assert set(ids(catalog.featured_courses())) == {101, 103}
    assert len(catalog.featured_courses(limit=1)) == 1
    assert catalog.featured_courses(limit=0) == []


def test_almost_full_uses_real_seat_counts_only(session_state):
    # Only SQL (3 seats) is really "few". Sold-out and roomy courses are not shown.
    assert ids(catalog.almost_full_courses()) == [102]


def test_almost_full_is_empty_when_no_course_is_nearly_full(session_state, fake_client):
    for course in fake_client.tables["courses"]:
        course["seats_available"] = course["seats_total"]
    assert catalog.almost_full_courses() == []


def test_almost_full_orders_by_fewest_seats(session_state, fake_client):
    add_course(fake_client, id=106, slug="tiny", title="Tiny", seats_available=1)
    assert ids(catalog.almost_full_courses()) == [106, 102]


# ---------------------------------------------------------------- US-205 related (U1-12)
def test_related_courses_same_path_first_then_category(session_state, fake_client):
    add_course(fake_client)  # 105, same category as 101
    assert ids(catalog.related_courses(101)) == [102, 105]


def test_related_courses_excludes_itself_and_drafts(session_state):
    # 103 is alone in category 1 (104 is a draft) and in no path.
    assert catalog.related_courses(103) == []


def test_related_courses_respects_limit(session_state, fake_client):
    for number in range(5):
        add_course(fake_client, id=200 + number, slug=f"extra-{number}", title=f"Extra {number}")
    assert len(catalog.related_courses(101, limit=4)) == 4


def test_next_in_path(session_state):
    assert ids(catalog.next_in_path({101})) == [102]
    assert catalog.next_in_path(set()) == []  # no path started
    assert catalog.next_in_path({101, 102}) == []  # path finished


def test_next_course_in_path(session_state):
    assert catalog.next_course_in_path(1, 101)["id"] == 102
    assert catalog.next_course_in_path(1, 102) is None  # last step
    assert catalog.next_course_in_path(1, 103) is None  # not in this path


# ---------------------------------------------------------------- US-604 paths (U1-14)
def test_list_paths_with_courses_in_order(session_state):
    paths = catalog.list_paths()
    assert [path["name"] for path in paths] == ["Data Analyst Path"]
    assert ids(paths[0]["courses"]) == [101, 102]


def test_list_paths_hides_draft_courses(session_state, fake_client):
    fake_client.tables["learning_path_courses"].append(
        {"path_id": 1, "course_id": 104, "position": 3}
    )
    assert ids(catalog.list_paths()[0]["courses"]) == [101, 102]


def test_list_paths_when_there_are_none(session_state, fake_client):
    fake_client.tables["learning_paths"] = []
    assert catalog.list_paths() == []


# ---------------------------------------------------------------- U1-09 cache (NFR-PERF-03)
def test_catalog_is_cached_until_cleared(session_state, fake_client):
    assert catalog.list_courses()["total"] == 3
    add_course(fake_client)

    assert catalog.list_courses()["total"] == 3  # served from the cache
    catalog.clear_cache()
    assert catalog.list_courses()["total"] == 4  # fresh after clearing


def test_cache_never_holds_drafts_even_if_the_client_can_see_them(session_state, fake_client):
    # The fake client has no RLS (like a staff session); drafts must still not be cached.
    catalog.list_courses()
    catalog.get_course("neural-networks-draft", include_unpublished=True)
    assert 104 not in ids(catalog.search_courses("")["courses"])


# ---------------------------------------------------------------- seat rule (US-203)
@pytest.mark.parametrize(
    ("available", "total", "expected"),
    [
        (0, 30, "sold_out"),
        (-1, 30, "sold_out"),
        (5, 100, "few"),
        (10, 100, "few"),
        (11, 100, "available"),
        (6, 0, "available"),
    ],
)
def test_seat_status(available, total, expected):
    assert catalog.seat_status(available, total) == expected


# ---------------------------------------------------------------- path badge (US-604)
def test_path_badge_name_uses_the_badges_table(session_state, fake_client):
    fake_client.tables["badges"] = [
        {"code": "path_master_data_analyst", "name": "Path Master: Data Analyst"}
    ]
    path = catalog.list_paths()[0]
    assert catalog.path_badge_name(path) == "Path Master: Data Analyst"


def test_path_badge_name_is_none_without_a_badge_code(session_state):
    assert catalog.path_badge_name({"name": "No badge path", "badge_code": None}) is None


def test_path_badge_name_is_none_for_an_unknown_code(session_state):
    # Sample data has no badge rows, so the path's code points at nothing.
    assert catalog.path_badge_name(catalog.list_paths()[0]) is None
