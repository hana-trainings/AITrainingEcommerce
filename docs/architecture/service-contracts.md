# Service contracts

Every function a story needs already exists in `app/services/` with its final signature,
type hints, a docstring and `raise NotImplementedError("<pick> <story>")`. A story **fills in the body**;
it does not change the signature. If a signature must change, open a small separate PR first
(work plan section 4.2). Data shapes (`Course`, `CartLine`, `ActionResult`, ...) are in
`app/models/domain.py`.

Layers: page (`app/pages`) -> service (`app/services`) -> Supabase table + RLS (`supabase/migrations`).
Pages never import `supabase`; only services do, through `supabase_client.get_client()`
(one client per browser session, kept in `st.session_state`).

IDs: `profiles.id` / user ids are uuid strings; every other id (course, category, path, order, ...) is an `int`.

## Functions

| Module | Function | Parameters | Story (pick) | Returns | State |
|---|---|---|---|---|---|
| auth | `sign_in` | `email: str, password: str` | US-502 (foundation) | `ActionResult` | real |
| auth | `sign_out` | – | US-503 (foundation) | `None` | real |
| auth | `register` | `display_name: str, email: str, password: str, confirm_password: str` | US-501 (U3-05 builds the page) | `ActionResult` (`data["errors"]` per field) | real |
| auth | `current_user` | – | foundation | `CurrentUser \| None` | real |
| auth | `require_role` | `*allowed_roles: Role` | US-701, NFR-SEC-10 (foundation) | `CurrentUser \| None` | real |
| auth | `fetch_role` | `user_id: str` | NFR-SEC-10 (foundation) | `Role \| None` | real |
| auth | `validate_password` | `password: str` | NFR-SEC-03 (foundation) | `list[str]` problems | real |
| auth | `validate_registration` | `display_name, email, password, confirm_password` | US-501 (foundation) | `dict[str, str]` | real |
| auth | `refresh_session` | – | NFR-AUTH-04 (U3-15) | `bool` | real |
| catalog | `list_courses` | `page: int = 1, page_size: int = 12` | US-101 (U1-03) | `CoursePage` | real |
| catalog | `search_courses` | `keyword: str = "", filters: CourseFilters \| None = None, sort: SortOption = "featured", page: int = 1, page_size: int = 12` | US-102 (U1-05), US-103 (U1-06), US-104 (U1-07) | `CoursePage` | real |
| catalog | `list_categories` | – | US-103 (U1-06) | `list[Category]` | real |
| catalog | `get_course` | `slug: str, include_unpublished: bool = False` | US-201 (U1-04), US-202/203 | `Course \| None` (with `modules`, `paths`) | real |
| catalog | `featured_courses` | `limit: int = 6` | US-106 (U1-13), US-105 (U1-08) | `list[Course]` | real |
| catalog | `almost_full_courses` | `limit: int = 4` | US-106 (U1-13) | `list[Course]` | real |
| catalog | `related_courses` | `course_id: int, limit: int = 4` | US-205 (U1-12) | `list[Course]` | real |
| catalog | `next_in_path` | `owned_course_ids: set[int], limit: int = 3` | US-405 (U2-05), US-205 | `list[Course]` | real |
| catalog | `list_paths` | – | US-604 (U1-14) | `list[LearningPath]` | real |
| cart | `add_item` | `course_id: int, quantity: int = 1` | US-301 (U2-01), US-204 (U1-15) | `ActionResult` | real |
| cart | `get_item_count` | – | US-301 AC3 (U2-01), header badge | `int` | real |
| cart | `get_items` | – | US-302 (U2-02), US-307 (U2-12), US-305 (U2-13) | `list[CartLine]` | real |
| cart | `summarize` | `lines: list[CartLine]` | US-302 AC2 (U2-02) | `CartSummary` | real |
| cart | `update_quantity` | `course_id: int, quantity: int` | US-303 (U2-10) | `ActionResult` | real |
| cart | `remove_item` | `course_id: int` | US-304 (U2-11) | `ActionResult` | real |
| cart | `merge_guest_cart` | `user_id: str` | US-306 (U2-14) | `ActionResult` | real |
| orders | `new_idempotency_key` | – | US-402 (U2-03), NFR-DATA-04 | `str` (uuid) | real |
| orders | `place_order` | `idempotency_key: str` | US-402 (U2-03), US-403 (U2-08), US-404 (U2-07) | `PlaceOrderOutcome` | real |
| orders | `get_order` | `order_id: int` | US-405 (U2-05), US-407 (U2-15), US-707 (U2-18) | `Order \| None` (with `items`) | real |
| orders | `list_my_orders` | – | US-407 (U2-15) | `list[Order]` | real |
| orders | `cancel_order` | `order_id: int` | US-408 (U2-16) | `ActionResult` | real |
| orders | `get_owned_course_ids` | `user_id: str` | US-202 AC3 (U1-10), US-604, S3 "Unlocked" | `set[int]` | real |
| email_outbox | `build_confirmation_email` | `order: Order, to_email: str, display_name: str` | US-406 (U2-06) | `EmailRecord` | real |
| email_outbox | `save_confirmation_email` | `order_id: int` | US-406 (U2-06), NFR-REL-02 | `ActionResult` (never raises) | real |
| email_outbox | `get_email_for_order` | `order_id: int` | US-407 AC2 (U2-15), US-707 AC3 (U2-18) | `EmailRecord \| None` | real |
| profile | `get_my_profile` | – | US-504 (U3-04) | `Profile \| None` | real |
| profile | `update_profile` | `display_name: str, avatar: str, interests: list[str]` | US-504 (U3-04) | `ActionResult` | real |
| profile | `claim_profile_completion` | – | US-504 AC3 (U3-04), US-601 | `ActionResult` | real |
| profile | `set_reduce_motion` | `enabled: bool` | US-605 (U2-17) | `ActionResult` | real |
| profile | `get_reduce_motion` | – | US-605 (U2-17) | `bool` | real |
| gamification | `get_level_progress` | `xp_total: int` | US-602 (U1-17) | `LevelProgress` | real |
| gamification | `list_my_xp_events` | – | US-601 (U3-13) | `list[XpEvent]` | real |
| gamification | `list_badges_with_status` | – | US-603 (U3-14) | `list[BadgeStatus]` | real |
| gamification | `build_path_nodes` | `path: LearningPath, owned_course_ids: set[int], cart_course_ids: set[int]` | US-604 (U1-14) | `list[PathNode]` | real |
| gamification | `get_path_progress` | – | US-504 (U3-04), US-604 | `list[PathProgress]` | real |
| admin | `list_courses` | `search: str = "", published: bool \| None = None, category_id: int \| None = None` | US-702 (U3-01) | `list[Course]` | real |
| admin | `validate_course_input` | `data: CourseInput` | US-703 AC2 (U3-03) | `dict[str, str]` | real |
| admin | `create_course` | `data: CourseInput` | US-703 (U3-03) | `ActionResult` (`data["course_id"]`) | real |
| admin | `get_course_for_edit` | `course_id: int` | US-704 (U3-09) | `Course \| None` | real |
| admin | `update_course` | `course_id: int, data: CourseInput` | US-704 (U3-09) | `ActionResult` | real |
| admin | `upload_course_image` | `file_bytes: bytes, content_type: str` | US-704 (U3-09), US-703 AC3 | `ActionResult` (`data["image_url"]`) | real |
| admin | `set_published` | `course_id: int, published: bool` | US-705 (U3-06) | `ActionResult` | real |
| admin | `adjust_seats` | `course_id: int, change: int, reason: str` | US-706 (U3-07) | `ActionResult` | real |
| admin | `delete_course` | `course_id: int, typed_title: str` | US-710 (U3-08) | `ActionResult` | real |
| admin | `list_categories_and_paths` | – | US-711 (U3-12) | `tuple[list[Category], list[LearningPath]]` | real |
| admin | `save_category` | `name: str, icon: str, sort_order: int, category_id: int \| None = None` | US-711 (U3-12) | `ActionResult` | real |
| admin | `save_path` | `name: str, description: str, course_ids_in_order: list[int], badge_name: str, path_id: int \| None = None` | US-711 (U3-12) | `ActionResult` | real |
| admin | `list_all_orders` | `status: OrderStatus \| None = None, date_from: str \| None = None, date_to: str \| None = None, search: str = ""` | US-707 (U2-18) | `list[Order]` | real |
| admin | `get_dashboard_metrics` | – | US-708 (U3-11) | `DashboardMetrics` | real |
| admin | `list_users` | – | US-709 (U3-10) | `list[UserRow]` | real |
| admin | `change_user_role` | `user_id: str, new_role: Role` | US-709 (U3-10) | `ActionResult` | real |

## Database calls the services rely on

| Call | Used by | Notes |
|---|---|---|
| RPC `place_order(p_idempotency_key uuid)` | `orders.place_order` | Returns `{order_id, order_number, total, xp_awarded, new_level, level_up, new_badges, already_existed}`. Errors start with `NOT_SIGNED_IN`, `CART_EMPTY`, `COURSE_UNAVAILABLE: <title>`, `NOT_ENOUGH_SEATS: <title>` (detail `seats_available=<n>`), `INVALID_REQUEST`. Map them with `orders.PLACE_ORDER_ERRORS`. |
| RPC `claim_profile_completion()` | `profile.claim_profile_completion` | +25 XP once; error `PROFILE_INCOMPLETE`. |
| RPC `write_audit_log(action, entity, entity_id, before, after)` | `admin.adjust_seats` (reason) | Staff only. Course, role and cancel changes are already audited by triggers. |
| RPC `level_for_xp(xp)` | optional | Same table as `gamification.LEVELS`. |
| `orders.status` update | `orders.cancel_order` | Errors `NOT_ALLOWED`, `ORDER_ALREADY_CANCELLED`. |
| `profiles.role` update | `admin.change_user_role` | Owner only, `customer` <-> `staff`; errors `NOT_ALLOWED`, `LAST_OWNER`. |
| Storage bucket `course-images` | `admin.upload_course_image` | Staff/owner write, public read. |
| RPC `admin_replace_course_children(p_course_id, p_modules jsonb, p_path_positions jsonb)` | `admin.create_course`, `admin.update_course` | Migration 0025. Staff only, one transaction. Errors `NOT_ALLOWED`, `INVALID_REQUEST`, `COURSE_NOT_FOUND`, `DUPLICATE_PATH`, `POSITION_TAKEN`. |
| RPC `admin_replace_path_courses(p_path_id, p_course_ids bigint[])` | `admin.save_path` | Migration 0025. Staff only, one transaction. Errors `NOT_ALLOWED`, `INVALID_REQUEST`, `DUPLICATE_COURSE`, `PATH_NOT_FOUND`, `POSITION_TAKEN`. |
| `email_outbox` unique `order_id` | `email_outbox.save_confirmation_email` | Migration 0020. A repeat save hits 23505 and is treated as "already saved". |

## Shared UI components (`app/components/`)

| File | Function(s) |
|---|---|
| `course_card.py` | `course_card(course, *, owned=False, in_cart=False, key_prefix="card") -> bool` (True when "Add to cart" clicked), `level_tag(level)` |
| `seat_meter.py` | `seat_meter(seats_available, seats_total)`, `seat_state(seats_available, seats_total) -> "available" \| "few" \| "sold_out"` |
| `xp.py` | `xp_pill(points)`, `xp_bar(xp_total, level_start_xp, next_level_xp)`, `level_chip(level, name)` |
| `badge.py` | `badge_medallion(name, description, *, earned, hint="", icon=...)` |
| `path_map.py` | `path_node_map(path_name, nodes, *, bonus_xp=0)` |
| `status_badge.py` | `status_badge(status)` |
| `states.py` | `coming_soon`, `empty_state`, `error_state`, `not_found`, `store_unavailable`, `access_denied`, `sign_in_prompt`, `flash`, `show_flash` |
| `guards.py` | `guard_customer_page(return_to=None)`, `guard_admin_page()`, `guard_owner_page()` (each returns `CurrentUser` or stops the page) |
| `header.py` | `render_header(user)` (called by the entry point; U1-17 and U2-01 improve it here) |

## Stories with no page or no service function (by design)

- D-01, D-02, D-03, D-04, U1-21 (NFR-UX), US-606: design, polish or review work; no new service function.
- U1-09 (NFR-PERF-03): adds caching inside `catalog.py`; no new function.
- US-403 (U2-08), NFR-MNT-05 (U2-09), L-01: tests in `tests/integration/`. L-02: `scripts/`. L-03: `docs/deployment/`.
- US-505 (U1-16): the "Ask your trainer" note is already on the sign-in page.
- US-701 (U3-02): the role check is done by `guard_admin_page()`; the story builds the landing content.
- Order detail (sitemap) lives inside `my_orders.py` and `admin_orders.py`; there is no separate page file in the work plan.
