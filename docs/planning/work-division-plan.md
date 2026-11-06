# Work Division Plan

| | |
|---|---|
| **Team** | 1 Tech Lead + 3 participants (User 1, User 2, User 3) |
| **Collaboration** | GitHub (repo, Issues, Projects board, Pull Requests, Actions) |
| **Based on** | [00 Consolidated](../requirements/00-consolidated-requirements.md) · [01 Stories](../requirements/01-product-features-user-stories.md) · [02 UI/UX](../requirements/02-ui-ux-requirements.md) · [03 NFRs](../requirements/03-non-functional-requirements.md) |

> Demo / training project. Durations are suggestions. Adjust to your schedule.

---

## 1. The approach in one picture

```
Phase 1: Foundation (Tech Lead)          Phase 2: Stories (User 1, 2, 3)              Phase 3: Release
┌──────────────────────────────┐        ┌────────────────────────────────────┐      ┌──────────────────┐
│ repo, CI, schema, RLS, seed, │  push  │ take your next story → branch →     │      │ bug bash, deploy,│
│ auth core, app shell, page   │ ─────► │ build → test → PR → review → merge  │ ───► │ tag v1.0         │
│ stubs, service stubs,        │  to    │ → next story on your list           │      │                  │
│ components, test fixtures    │  main  │                                     │      │                  │
└──────────────────────────────┘        └────────────────────────────────────┘      └──────────────────┘
```

**Why this shape:** the Tech Lead builds every shared piece first, so no one waits on schema, auth, navigation, or components. Each user then has their own ordered story list, grouped so that most dependencies stay inside the same list.

| Rule | What it means |
|---|---|
| Foundation first | Nobody starts a story until the foundation is merged to `main` and tagged `foundation-v1`. |
| Your list, in order | Each user works through their own list (§3) from top to bottom. |
| One story at a time | Each user has at most **one** story In progress. Finish, merge, then take the next. |
| One story per PR | A branch and PR contain exactly one story. |
| Say your pick code | Each story has a pick code, e.g. **U2-03**. Use it in stand-ups, Issue comments, and PR titles so everyone knows who is on what. |
| Shared files are already done | The entry point, navigation, DB schema, and component APIs exist before stories start. Changing them is a small, separate PR reviewed by the Lead. |

---

## 2. Phase 1: Foundation (Tech Lead, about 1 week)

The Lead builds the skeleton that every story depends on and pushes it to GitHub. Each item below is a commit (or a small PR) on `main`.

### 2.1 Repository and process

| # | Item | Output |
|---|---|---|
| F1 | GitHub repo, branch protection on `main` (PR required, 1 approval, CI green, branch up to date) | Repo settings |
| F2 | Labels, milestones, Projects board (Backlog → Ready → In progress → In review → Done) | Board |
| F3 | One Issue per story in §3. Title starts with the pick code (`U2-03 US-402 Review and place order`), acceptance criteria pasted as a checklist, label `user:1/2/3`, assignee set, `Depends on` filled in | Issues |
| F4 | `CONTRIBUTING.md` (the workflow in §4), PR template, Issue template | `.github/`, root |
| F5 | `CODEOWNERS`: Lead owns `supabase/`, `app/streamlit_app.py`, `app/services/supabase_client.py`, `requirements.txt`, `.github/` | `.github/CODEOWNERS` |
| F6 | GitHub Actions CI: `ruff` + `pytest` on every PR; secret scanning on | `.github/workflows/ci.yml` |
| F7 | Decide open questions Q1 - Q6 (doc 00 §8); record answers in `docs/architecture/decisions.md` | Doc |

### 2.2 Database (Supabase dev project)

| # | Item | Output |
|---|---|---|
| F8 | All tables from doc 00 §6, with indexes (NFR-PERF-06) | `supabase/migrations/` |
| F9 | RLS policies for guest, customer, staff, owner (NFR-SEC-05/06) | Migration |
| F10 | `place_order(idempotency_key)`: seat check, seat deduction, order + items, XP and badge awards, all in one transaction (US-403, US-601 - 603 server side, NFR-DATA-01 - 04) | Migration |
| F11 | Audit log table + helper function (NFR-SEC-18); storage bucket + policies for course images (NFR-SEC-16) | Migration |
| F12 | Seed data: 4 categories, 12 - 16 courses, 3 paths, badges, demo accounts (customer, staff, owner), a few sample orders | `supabase/seed/` |

### 2.3 Application skeleton

| # | Item | Output |
|---|---|---|
| F13 | Pinned Python version and `requirements.txt`; settings + secrets loading with fail-fast (NFR-SEC-11/12); basic logging | `app/config/`, `app/utils/` |
| F14 | Supabase client factory | `app/services/supabase_client.py` |
| F15 | **Auth core:** `sign_in`, `sign_out`, `current_user()`, `require_role()`, plus a working Sign in page (US-502, US-503) | `app/services/auth.py`, `app/pages/sign_in.py` |
| F16 | **App shell:** entry point with role-based navigation, header, demo ribbon. **Every page in the sitemap (doc 02 §5.1) is already registered** as a stub that says "Coming soon - US-xxx" | `app/streamlit_app.py`, `app/pages/*.py` |
| F17 | **Service stubs:** every service function needed by the stories, with signature, docstring, return shape, and `raise NotImplementedError`. This is the contract. | `app/services/*.py`, `docs/architecture/service-contracts.md` |
| F18 | **Component stubs:** working plain-Streamlit versions with final function signatures: course card, seat meter, XP pill, XP bar, level chip, badge, path node map, empty / error / access-denied states | `app/components/*.py` |
| F19 | Basic theme from doc 02 §3 color tokens | `.streamlit/config.toml`, `assets/styles/` |
| F20 | Test setup: `conftest.py` with a fake Supabase client and sample data, one example unit test, one example integration test | `tests/` |
| F21 | README local setup steps (clone, venv, `.env`, run) | `README.md` |

### 2.4 Page and service files created by the foundation

Stories fill these in. Because they already exist and are already in navigation, no story needs to edit the entry point.

| Page file | Service module(s) |
|---|---|
| `home.py`, `courses.py`, `course_detail.py`, `learning_paths.py` | `catalog.py` |
| `cart.py` | `cart.py` |
| `checkout.py`, `order_confirmation.py`, `my_orders.py` | `orders.py`, `email_outbox.py` |
| `sign_in.py`, `register.py`, `passport.py` | `auth.py`, `profile.py`, `gamification.py` |
| `admin_dashboard.py`, `admin_courses.py`, `admin_course_form.py`, `admin_categories_paths.py`, `admin_orders.py`, `admin_staff.py` | `admin.py` |

### 2.5 Foundation exit checklist (tag `foundation-v1`)

- [ ] A fresh clone runs locally by following the README.
- [ ] Every page opens without errors (stubs show "Coming soon").
- [ ] Demo customer, staff, and owner can sign in and see the right navigation.
- [ ] Calling `place_order` from a test reduces seats and creates an order.
- [ ] CI is green on `main`.
- [ ] All story Issues are on the board, assigned to User 1, 2, or 3, with pick codes.

### 2.6 What participants do during Phase 1

| Who | Task | Output |
|---|---|---|
| All | Install Python, Git, an editor; clone the repo as soon as F13 lands | Working local setup |
| All | Read docs 00 - 03 and your own story Issues; comment with questions | Clearer acceptance criteria |
| User 1 | Start design stories **U1-01** and **U1-02** (no code needed) | Style guide, wireframes |
| User 2, User 3 | Review the Lead's foundation PRs (learning the codebase early) | Comments |

---

## 3. Phase 2: Stories by user

Each story is one Issue, one branch, one PR. Work top to bottom. **Depends on** lists stories that must be merged first; a dependency owned by another user is marked with their pick code. "-" means the story can start as soon as the foundation is tagged.

Size: **S** about half a day, **M** about 1 day, **L** about 2 days. Each user has about 14 - 15 days of story work.

### 3.1 User 1: Storefront, catalog, and design

Focus: everything a visitor sees before the cart: Home, Courses, Course detail, Learning Paths, header XP, and the visual design.

| Pick | Story | Title | Files | Depends on | Size |
|---|---|---|---|---|---|
| U1-01 | D-01 | Style guide and component sheet (doc 02 §11) | `docs/design/` | - (Phase 1) | M |
| U1-02 | D-02 | Wireframes S1 - S16 and key flows | `docs/design/` | - (Phase 1) | L |
| U1-03 | US-101 | Browse the catalog | `courses.py`, `catalog.list_courses` | - | M |
| U1-04 | US-201 | View course details | `course_detail.py`, `catalog.get_course` | - | M |
| U1-05 | US-102 | Keyword search | `courses.py`, `catalog.search_courses` | U1-03 | S |
| U1-06 | US-103 | Filter results | `courses.py`, `catalog.search_courses` | U1-03 | M |
| U1-07 | US-104 | Sort results | `courses.py` | U1-03 | S |
| U1-08 | US-105 | No results state | `courses.py` | U1-03 | S |
| U1-09 | NFR-PERF-03 | Cache the public catalog | `catalog.py` | U1-03 | S |
| U1-10 | US-202 | Locked syllabus preview | `course_detail.py` | U1-04 | S |
| U1-11 | US-203 | Seat availability on detail | `course_detail.py` | U1-04 | S |
| U1-12 | US-205 | Related courses / next in path | `course_detail.py`, `catalog.related_courses` | U1-04 | S |
| U1-13 | US-106 | Featured and "Almost full" on Home (S1) | `home.py`, `catalog.featured_courses` | - | M |
| U1-14 | US-604 | Learning Paths page with skill tree (S5) | `learning_paths.py`, `catalog.list_paths` | - | M |
| U1-15 | US-204 | Add to cart from detail | `course_detail.py` | U1-04, **U2-01** | S |
| U1-16 | US-505 | Password reset note | `sign_in.py` | - | S |
| U1-17 | US-602 | Levels in header (XP bar + level chip) | `gamification.py`, header hook in shell | - | M |
| U1-18 | S16 | System states: not found, error, store unavailable | `app/components/states.py` | - | M |
| U1-19 | D-03 | Visual polish: course card, seat meter | `app/components/` | U1-01 | M |
| U1-20 | D-04 | Visual polish: XP, level, badge, path map | `app/components/` | U1-01 | M |
| U1-21 | NFR-UX-01 - 03 | Accessibility pass across all pages | many (small fixes) | most stories merged | M |

### 3.2 User 2: Cart, checkout, and orders

Focus: the buying flow from "Add to cart" to "My Orders", plus the admin orders view.

| Pick | Story | Title | Files | Depends on | Size |
|---|---|---|---|---|---|
| U2-01 | US-301 | Add a course to the cart (guest session cart) | `cart.add_item`, course card button | - | M |
| U2-02 | US-302 | View the cart | `cart.py` page, `cart.get_items` | U2-01 | M |
| U2-03 | US-402 | Review and place order | `checkout.py`, `orders.place_order` (calls DB function) | U2-02 | M |
| U2-04 | US-401 | Checkout requires sign-in | `checkout.py` | - | S |
| U2-05 | US-405 | Order confirmation page | `order_confirmation.py` | U2-03 | M |
| U2-06 | US-406 | Confirmation email to outbox (file + table) | `email_outbox.py` | U2-03 | M |
| U2-07 | US-404 | Handle stock conflict | `checkout.py` | U2-03 | M |
| U2-08 | US-403 | Verify seat deduction (tests against `place_order`) | `tests/integration/` | U2-03 | S |
| U2-09 | NFR-MNT-05 | Checkout tests: no oversell, double submit | `tests/integration/` | U2-07 | M |
| U2-10 | US-303 | Change quantity | `cart.py` | U2-02 | S |
| U2-11 | US-304 | Remove an item | `cart.py` | U2-02 | S |
| U2-12 | US-307 | Cart price check | `cart.py` | U2-02 | S |
| U2-13 | US-305 | Persistent cart for signed-in customers | `cart.py` service (`cart_items` table) | U2-02 | M |
| U2-14 | US-306 | Merge guest cart on sign-in | `cart.merge_guest_cart`, one call in `auth.sign_in` | U2-13 | S |
| U2-15 | US-407 | Order history | `my_orders.py`, `orders.list_my_orders` | - (seed orders) | M |
| U2-16 | US-408 | Order status / cancel | `my_orders.py` | U2-15 | S |
| U2-17 | US-605 | Celebrations + Reduce motion setting | `order_confirmation.py`, `profile.py` | U2-05, **U3-04** | M |
| U2-18 | US-707 | Admin: view orders | `admin_orders.py` | - | M |

### 3.3 User 3: Account, gamification, and admin

Focus: register, Learner Passport, XP and badges, and the owner/staff admin area.

| Pick | Story | Title | Files | Depends on | Size |
|---|---|---|---|---|---|
| U3-01 | US-702 | Admin course list | `admin_courses.py`, `admin.list_courses` | - | M |
| U3-02 | US-701 | Admin area access and landing | `admin_dashboard.py` | - | S |
| U3-03 | US-703 | Create course | `admin_course_form.py`, `admin.create_course` | - | M |
| U3-04 | US-504 | Learner Passport (S10) | `passport.py`, `profile.py` | - | M |
| U3-05 | US-501 | Register | `register.py`, `auth.register` | - | M |
| U3-06 | US-705 | Publish / unpublish | `admin_courses.py` | U3-01 | S |
| U3-07 | US-706 | Adjust seats | `admin_courses.py` | U3-01 | S |
| U3-08 | US-710 | Delete course | `admin_courses.py` | U3-01 | S |
| U3-09 | US-704 | Edit course + image upload | `admin_course_form.py`, `admin.update_course` | U3-03 | L |
| U3-10 | US-709 | Manage staff (owner only) | `admin_staff.py` | - | M |
| U3-11 | US-708 | Admin dashboard metrics | `admin_dashboard.py` | U3-02 | M |
| U3-12 | US-711 | Manage categories and learning paths | `admin_categories_paths.py` | - | L |
| U3-13 | US-601 | Show XP earned (toast + history on Passport) | `gamification.py`, `passport.py` | U3-04 | S |
| U3-14 | US-603 | Badge shelf | `passport.py` | U3-04 | S |
| U3-15 | NFR-AUTH-04 | Token refresh and session expiry | `auth.py` | - | M |
| U3-16 | US-606 | Ethical gamification check | review + small fixes | U3-13, U3-14, **U1-17**, **U2-17** | S |

### 3.4 Tech Lead stories (alongside reviews in Phase 2)

| Pick | Story | Title | Files | Depends on | Size |
|---|---|---|---|---|---|
| L-01 | NFR-SEC-05 | RLS break test (try every role) | `tests/integration/` | - | M |
| L-02 | NFR-PRIV-07 | Demo reset script | `scripts/` | - | S |
| L-03 | NFR-DEP | Deploy to Streamlit Cloud + deployment guide | `docs/deployment/` | **U2-03** | M |

### 3.5 Cross-user dependencies

Only these stories wait on another user. They are placed late in each list, so the other user's story should already be merged by then.

| Waiting story | Needs | Owner of the needed story |
|---|---|---|
| U1-15 US-204 Add to cart from detail | U2-01 US-301 | User 2 (their first story) |
| U1-21 Accessibility pass | Most pages merged | Everyone |
| U2-17 US-605 Celebrations | U3-04 US-504 | User 3 (their 4th story) |
| U3-16 US-606 Ethical gamification | U1-17 US-602, U2-17 US-605 | User 1, User 2 |
| L-03 Deploy | U2-03 US-402 | User 2 (their 3rd story) |

If your next story is still blocked, skip to the next unblocked story on **your own** list and come back to it.

### 3.6 Finished early or stuck?

- **Finished your list:** help another user by taking a story from the **bottom** of their list, after agreeing in stand-up. Reassign the Issue to yourself and keep its pick code.
- **Stuck more than half a day:** say the pick code in stand-up or comment on the Issue. The Lead helps or swaps the story.

---

## 4. Story workflow (every story, every time)

```
1. Pick     Take the next story on your list. Move the Issue to "In progress".
            Say it in stand-up: "User 2, starting U2-03 (US-402)".
2. Branch   git checkout main && git pull
            git checkout -b feature/U2-03-US-402-place-order
3. Build    Change only the files listed for the story. Fill in the stub functions.
4. Test     Unit tests for your service functions. Run: ruff check . && pytest
5. Commit   Small commits with the story ID: "US-402: place order button and summary"
6. Sync     git pull --rebase origin main   (fix any conflicts locally)
7. PR       Open PR to main. Title "U2-03 US-402 Review and place order". Body has "Closes #12",
            screenshots (desktop + mobile), and the checklist below. Move Issue to "In review".
8. Review   One of the other users reviews against the acceptance criteria (rotation in §4.3).
            CODEOWNERS adds the Lead automatically if a protected file changed.
9. Merge    CI green + approval + branch up to date → Squash and merge. Delete the branch.
10. Repeat  Pull main and take the next story on your list.
```

### 4.1 PR checklist

- [ ] Exactly one story in this PR; pick code in the title
- [ ] Acceptance criteria met (ticked in the Issue)
- [ ] Unit tests added and passing; `ruff` passes
- [ ] Only the story's files changed (or the extra file is explained)
- [ ] No secrets, keys, or `.env` committed
- [ ] Screenshots for UI changes (desktop + mobile)

### 4.2 When a story needs something outside its files

| Need | What to do |
|---|---|
| A DB change (new column, policy) | Add a **new** migration file in your PR. Never edit a merged migration. The Lead reviews it (CODEOWNERS). |
| A new dependency | Add it to `requirements.txt` in your PR; the Lead reviews. |
| A change to a service contract or component signature | Open a small separate PR first, get it merged, then continue. Keep old callers working. Tell the user who owns that area. |
| A dependency story isn't merged yet | Don't start it. Take the next unblocked story on your list. |

### 4.3 Reviews

| PR from | Reviewed by |
|---|---|
| User 1 | User 2 |
| User 2 | User 3 |
| User 3 | User 1 |
| Tech Lead | Any user |

- Review within half a day when asked. Reviewing is part of the work, not extra.
- The reviewer runs the branch locally and clicks through the acceptance criteria.
- Swap the rotation each week so everyone sees every area.

### 4.4 Definition of Done

A story is **Done** when the PR is merged to `main`, CI is green, the reviewer verified the acceptance criteria on the shared dev Supabase, and the Issue is closed.

---

## 5. Phase 3: Integration and release

Starts when all **Must** stories are Done.

| Step | Who | Output |
|---|---|---|
| End-to-end smoke test: find course → cart → checkout → seats go down → confirmation → My Orders → admin sees order | Lead + User 2 | Pass / bug list |
| Bug bash: test an area you did **not** build (User 1 tests User 2's area, User 2 tests User 3's, User 3 tests User 1's) | All users | Bug Issues (`type:bug`), fixed with the same one-per-PR flow by the area's owner |
| Security review against doc 03; RLS test passes | Lead | Checklist |
| Final deploy, deployment guide, trainer guide (demo accounts shared privately) | Lead | Live URL, docs |
| Demo script for your area (what to click, what to show) | Each user | `docs/demo-script.md` |
| Tag release `v1.0` | Lead | GitHub release |

---

## 6. Suggested timeline

| Week | Lead | User 1 | User 2 | User 3 |
|---|---|---|---|---|
| 1 | Foundation F1 - F21, tag `foundation-v1` | U1-01, U1-02 (design) | Setup, review foundation | Setup, review foundation |
| 2 | Reviews, L-01, L-02 | U1-03 - U1-10 | U2-01 - U2-06 | U3-01 - U3-07 |
| 3 | Reviews, L-03 | U1-11 - U1-16 | U2-07 - U2-13 | U3-08 - U3-11 |
| 4 | Reviews, help where needed | U1-17 - U1-20 | U2-14 - U2-18 | U3-12 - U3-16 |
| 5 | Release tasks | U1-21, bug bash, demo script | Bug bash, demo script | Bug bash, demo script |

---

## 7. GitHub setup reference

| Item | Value |
|---|---|
| Labels | `user:1`, `user:2`, `user:3`, `user:lead`, `epic:E1` … `epic:E7`, `type:story/nfr/design/bug`, `priority:must/should/could`, `size:S/M/L`, `schema-change`, `blocked` |
| Issue title | `U2-03 US-402 Review and place order` |
| Milestones | `Foundation`, `Stories`, `Release v1.0` |
| Board columns | Backlog → Ready → In progress → In review → Done. Group or filter the board by `user:` label so each user sees their own list. |
| Branch names | `feature/U1-03-US-101-catalog`, `fix/U2-08-US-403-negative-seats`, `design/U1-19-D-03-course-card`, `db/U3-09-US-704-image-column` |
| Merge method | Squash and merge (one commit per story on `main`) |

## 8. Shared environments

| Environment | Used for | Notes |
|---|---|---|
| Local Streamlit + shared **dev** Supabase | Daily development | Everyone uses the anon key in their own `.env`. Only the Lead holds the service role key. |
| Separate **test** Supabase project (optional) | Integration tests | Can be reset freely with the demo reset script |
| Streamlit Cloud | Demo / deployment lesson | Deployed from `main` |

Never share keys in Issues, PRs, or chat screenshots. Share them through a private channel agreed by the team.

## 9. Meetings

| Meeting | When | Length | Purpose |
|---|---|---|---|
| Foundation walkthrough | When `foundation-v1` is tagged | 60 min | Lead shows the structure, stubs, contracts, and the story workflow |
| Stand-up | Daily (or async in a GitHub Discussion) | 10 min | Each user says: pick code done, pick code doing, anything blocked |
| Board review | Twice a week | 20 min | Check cross-user dependencies (§3.5); rebalance if a user is behind |
| Demo + retro | End of each week | 45 min | Show merged stories from `main`; what to improve |

## 10. Risks

| Risk | Mitigation |
|---|---|
| Foundation takes longer than planned | User 1 works on design; Users 2 and 3 review foundation PRs; the Lead merges the foundation in pieces so setup can start early |
| A user is blocked by another user's story | Cross-user dependencies are few and placed late (§3.5); skip to the next unblocked story on your list |
| A user falls behind | Board review twice a week; users who finish early take stories from the bottom of that user's list (§3.6) |
| A service contract turns out wrong | Fix it in a small separate PR first, keeping existing callers working |
| PRs wait too long for review | Fixed review rotation (§4.3) and a half-day review target |
| Checkout overselling or double orders | Single DB transaction in the foundation + U2-08 and U2-09 tests |
| Keys leaked to GitHub | `.gitignore`, PR checklist, GitHub secret scanning |
