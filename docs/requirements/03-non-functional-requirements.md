# 03 - Non-Functional Requirements

| | |
|---|---|
| **Audience** | Developers, trainers, reviewers |
| **Related docs** | [00 Consolidated](00-consolidated-requirements.md) · [01 Features & Stories](01-product-features-user-stories.md) · [02 UI/UX](02-ui-ux-requirements.md) |

> Demo / training app. The targets below are sized for a classroom demo, but the security practices are real so learners see how it should be done.

Priority: **Must** / **Should** / **Could**.

---

## 1. Authentication (sign-in)

| ID | Requirement | Priority |
|---|---|---|
| NFR-AUTH-01 | Use **Supabase Auth** with email + password. The app does not store or hash passwords itself. | Must |
| NFR-AUTH-02 | Email confirmation is **disabled** in the Supabase project for the demo (no emails are sent). Documented in the deployment guide. | Must |
| NFR-AUTH-03 | After sign-in, the access token and refresh token are kept only in Streamlit `session_state` (server memory for that browser session). Tokens are never written to logs, files, or the UI. | Must |
| NFR-AUTH-04 | Expired access tokens are refreshed using the refresh token; if refresh fails, the user is signed out with a message. | Must |
| NFR-AUTH-05 | Sign-out calls Supabase sign-out and clears all session state. | Must |
| NFR-AUTH-06 | Known limitation: refreshing the browser tab starts a new Streamlit session and the user must sign in again. Acceptable for the demo; documented for learners. | Must (document) |
| NFR-AUTH-07 | Sign-in errors are generic ("Email or password is incorrect") so they don't reveal which emails are registered. | Must |
| NFR-AUTH-08 | Supabase's built-in auth rate limits stay enabled to slow down password guessing. | Must |
| NFR-AUTH-09 | Social login and multi-factor authentication are out of scope; MFA can be shown as a "next step" topic in training. | Won't |

## 2. Security

### 2.1 Passwords and accounts

| ID | Requirement | Priority |
|---|---|---|
| NFR-SEC-01 | New accounts always get role `customer`. Role can't be set from the registration form or any client request. | Must |
| NFR-SEC-02 | Only an Owner can change roles (enforced in the database, not just hidden in the UI). The last Owner can't be demoted. | Must |
| NFR-SEC-03 | Password policy: at least 8 characters with at least one letter and one number. Configured in Supabase Auth and validated in the form. | Must |
| NFR-SEC-04 | Demo account passwords are not committed to the repo. They are shared by the trainer separately. | Must |

### 2.2 Authorization and Row Level Security (RLS)

| ID | Requirement | Priority |
|---|---|---|
| NFR-SEC-05 | **RLS is enabled on every table.** The UI hiding a page is never the only protection. | Must |
| NFR-SEC-06 | Policies (summary): | Must |

| Table | Guest (anon) | Customer | Staff | Owner |
|---|---|---|---|---|
| `courses`, `categories`, `learning_paths` | Read published | Read published | Read all, create, update | Same as staff + delete |
| `profiles` | None | Read/update own (not `role`, not `xp`) | Read all | Read all, update `role` |
| `cart_items` | None | Full access to own rows only | None | None |
| `orders`, `order_items` | None | Read own | Read all, update status | Same as staff |
| `email_outbox` | None | Read own | Read all | Read all |
| `xp_events`, `user_badges` | None | Read own | Read all | Read all |
| `audit_log` | None | None | Read | Read |

| ID | Requirement | Priority |
|---|---|---|
| NFR-SEC-07 | The Streamlit app uses only the Supabase **anon (publishable) key** plus the signed-in user's token, so RLS applies to every request. | Must |
| NFR-SEC-08 | The **service role key is never used in the Streamlit app** and never stored in the repo, `.env.example`, or Streamlit secrets. It may only be used locally by the developer for seeding scripts. | Must |
| NFR-SEC-09 | Checkout, inventory deduction, XP awards, and badge awards happen inside Postgres functions (`SECURITY DEFINER`, fixed `search_path`) that check `auth.uid()`. Prices and XP are read from the database, never trusted from the client. | Must |
| NFR-SEC-10 | Admin pages check the user's role on every page load (role read from the database, not cached forever in session). | Must |

### 2.3 Secrets and configuration

| ID | Requirement | Priority |
|---|---|---|
| NFR-SEC-11 | Secrets live in `.env` (local) or `.streamlit/secrets.toml` / the hosting platform's secret settings. Both are git-ignored; only `.example` templates are committed. | Must |
| NFR-SEC-12 | The app fails fast with a clear message if required secrets are missing (without printing their values). | Must |

### 2.4 Input handling

| ID | Requirement | Priority |
|---|---|---|
| NFR-SEC-13 | All form inputs are validated for type, length, and range (e.g. price 0-9,999, seats 1-10,000, summary ≤ 200 chars, quantity 1-5). | Must |
| NFR-SEC-14 | Database access goes through the Supabase client (parameterized). No SQL is built by string concatenation. | Must |
| NFR-SEC-15 | Any user-provided text rendered as HTML (e.g. course descriptions in cards, email content) is escaped. `unsafe_allow_html` is only used with escaped or static content. | Must |
| NFR-SEC-16 | Image uploads: JPG/PNG/WebP only, max 2 MB, stored in a Supabase Storage bucket that only Staff/Owner can write to; public read for course images. File names are generated by the app, not taken from the user. | Must |
| NFR-SEC-17 | Error messages shown to users never include stack traces, SQL, or keys. Details go to logs only. | Must |

### 2.5 Audit

| ID | Requirement | Priority |
|---|---|---|
| NFR-SEC-18 | An `audit_log` table records: course create/update/publish/delete, seat adjustments, role changes, order cancellations. Each entry stores who, what, when, and before/after values. | Should |

## 3. Privacy and child safety

The training audience can include minors.

| ID | Requirement | Priority |
|---|---|---|
| NFR-PRIV-01 | Collect only display name, email, and password. No date of birth, phone, address, school, photos, or payment details. | Must |
| NFR-PRIV-02 | Avatars are chosen from a preset list; no photo uploads by customers. | Must |
| NFR-PRIV-03 | No third-party analytics, ads, or tracking scripts. | Must |
| NFR-PRIV-04 | No public profiles, leaderboards, chat, or user-generated content visible to other customers. | Must |
| NFR-PRIV-05 | All seed and sample content is fictional and age-appropriate. | Must |
| NFR-PRIV-06 | Learners are told to use a test/training email address rather than a personal one. The register page shows this hint. | Should |
| NFR-PRIV-07 | A trainer script can delete all demo users and orders to reset the environment after a session. | Should |

## 4. Data integrity

| ID | Requirement | Priority |
|---|---|---|
| NFR-DATA-01 | Order placement is a single transaction: lock course rows, check seats, insert order + items, deduct seats, clear cart, award XP/badges. All or nothing. | Must |
| NFR-DATA-02 | Database constraints: `seats_available >= 0`, `seats_available <= seats_total`, `price >= 0`, `quantity BETWEEN 1 AND 5`, unique course slug, unique order number. | Must |
| NFR-DATA-03 | `order_items` store the unit price and course title at time of purchase, so later edits don't change past orders. | Must |
| NFR-DATA-04 | Double-click / duplicate submit can't create two orders (button disabled while submitting + an idempotency key per checkout attempt). | Must |
| NFR-DATA-05 | Courses with orders can't be hard-deleted (foreign key restrict); they can be unpublished. | Must |
| NFR-DATA-06 | Schema changes are managed as SQL migration files in `supabase/migrations/`, applied in order. | Must |
| NFR-DATA-07 | Monetary values stored as `numeric(10,2)`, never floating point. | Must |

## 5. Performance

Targets for a demo with up to ~50 concurrent users and ~100 courses.

| ID | Requirement | Priority |
|---|---|---|
| NFR-PERF-01 | Storefront pages render in under **3 seconds** on a normal connection (after the hosting platform has woken up). | Should |
| NFR-PERF-02 | Search/filter results return in under **1 second**. | Should |
| NFR-PERF-03 | Public catalog data (published courses, categories, paths) is cached with `st.cache_data` with a short TTL (e.g. 60 seconds). User-specific data (cart, orders, XP) is never shared via cache. | Must |
| NFR-PERF-04 | Seat counts at checkout are always read fresh from the database (never from cache). | Must |
| NFR-PERF-05 | Course images are resized/compressed on upload (target ≤ 300 KB). | Could |
| NFR-PERF-06 | Database indexes on `courses(is_published)`, `courses(category_id)`, `orders(user_id, created_at)`, `cart_items(user_id)`. | Should |

## 6. Usability and accessibility

| ID | Requirement | Priority |
|---|---|---|
| NFR-UX-01 | Meet WCAG 2.1 AA where Streamlit allows (contrast, labels, keyboard use, alt text). See doc 02 section 8. | Should |
| NFR-UX-02 | Works on latest Chrome, Edge, Firefox, Safari, and on mobile browsers at 390px width. | Must |
| NFR-UX-03 | "Reduce motion" setting turns off celebrations. | Should |
| NFR-UX-04 | Every action that changes data gives feedback (toast, message, or page change) within 1 second, with a spinner for longer operations. | Must |

## 7. Reliability and error handling

| ID | Requirement | Priority |
|---|---|---|
| NFR-REL-01 | If Supabase is unreachable, show a friendly "Store is temporarily unavailable" page instead of a crash. | Must |
| NFR-REL-02 | Failing to write the confirmation email file must not fail the order (US-406). | Must |
| NFR-REL-03 | Availability target is best-effort (free-tier hosting). Free-tier sleep/wake behavior is documented for trainers. | Must (document) |
| NFR-REL-04 | Supabase backups: rely on the platform default; seed scripts can rebuild demo data from scratch. | Should |

## 8. Maintainability and code quality

| ID | Requirement | Priority |
|---|---|---|
| NFR-MNT-01 | Follow the repo folder structure: `app/pages` (screens), `app/components` (UI pieces), `app/services` (Supabase access and business logic), `app/models` (data classes), `app/utils`, `app/config`. Pages don't call Supabase directly; they go through services. | Must |
| NFR-MNT-02 | Python 3.11+, dependencies pinned in `requirements.txt`. | Must |
| NFR-MNT-03 | Code formatted and linted with `ruff`; type hints on service functions. | Should |
| NFR-MNT-04 | Code is written to be readable by learners: clear names, short functions, comments explaining *why* for non-obvious parts. | Must |
| NFR-MNT-05 | Unit tests (pytest) for services and validation; integration tests for checkout (including stock conflict and no-oversell) against a test Supabase project or local Supabase. | Should |
| NFR-MNT-06 | README explains local setup, Supabase setup, seeding, and running tests. | Must |

## 9. Logging and monitoring

| ID | Requirement | Priority |
|---|---|---|
| NFR-LOG-01 | Use Python `logging` with levels; log errors with context (page, action, user id), never passwords, tokens, or keys. | Must |
| NFR-LOG-02 | Order placed, order failed (reason), and email-file write failures are logged at INFO/WARNING. | Should |

## 10. Deployment and environments

| ID | Requirement | Priority |
|---|---|---|
| NFR-DEP-01 | Environments: **local** (developer machine) and **cloud demo**. Optionally a separate Supabase project for tests. | Must |
| NFR-DEP-02 | **Primary hosting: Streamlit Community Cloud**, deployed from the GitHub repo, with secrets set in the app settings. | Must |
| NFR-DEP-03 | **Vercel note:** Streamlit needs a long-running server with WebSocket connections. Vercel runs serverless functions, which don't support that, so Streamlit apps don't run properly on Vercel. Options for the deployment lesson: (a) use Streamlit Cloud as the main target and explain why Vercel doesn't fit (a good teaching point), or (b) teach a second deployment on a container host that supports Streamlit (e.g. Render, Railway, Hugging Face Spaces, Google Cloud Run). Decision needed (see doc 00, open questions). | Must (decide) |
| NFR-DEP-04 | Cloud hosts have a temporary file system: files in `outbox/` may disappear on restart. That's why confirmation emails are also saved to the `email_outbox` table (US-406 AC3). `outbox/` is git-ignored. | Must |
| NFR-DEP-05 | Deployment guide in `docs/deployment/` covers: creating the Supabase project, running migrations and seed, disabling email confirmation, setting secrets, deploying, and resetting demo data. | Must |
| NFR-DEP-06 | Same code runs locally and in the cloud; differences are only in configuration/secrets. | Must |

## 11. Scalability and limits (demo scope)

- Designed for up to ~50 concurrent users, ~100 courses, ~10,000 orders.
- Uses Supabase free tier; its limits (database size, auth rate limits, project pause after inactivity) are acceptable and documented.
- No load testing required.

## 12. Constraints and assumptions

- Streamlit (Python) for UI; Supabase for database, auth, and storage. No separate backend API.
- Single currency (USD shown as "demo prices"), English only.
- No real payments and no real emails at any point.
- Content must stay age-appropriate for mixed-age training groups.
