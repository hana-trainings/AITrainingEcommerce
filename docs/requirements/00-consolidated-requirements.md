# 00 - Consolidated Requirements

**Project:** AI Training E-commerce
**Purpose:** Demo and training app. Sells fictional AI and Data training courses. No real payments, no real emails.
**Stack:** Streamlit (Python UI) · Supabase (Postgres, Auth, Storage)
**Deployment:** Streamlit Community Cloud (primary). See [open question Q1](#8-open-questions) about Vercel.

| Detailed document | Contents |
|---|---|
| [01 - Product Features & User Stories](01-product-features-user-stories.md) | Roles, 7 epics, user stories with acceptance criteria, seed data, out of scope |
| [02 - UI / UX Requirements](02-ui-ux-requirements.md) | Vision analysis, gamification design, sitemap, flows, screen-by-screen requirements, designer deliverables |
| [03 - Non-Functional Requirements](03-non-functional-requirements.md) | Sign-in, security, RLS, privacy, data integrity, performance, deployment |

---

## 1. Goals

1. Give learners a realistic, end-to-end e-commerce app to study: catalog, cart, checkout, auth, admin, database.
2. Look **professional yet gamified**, so browsing creates curiosity to "unlock" courses.
3. Show good practice: Row Level Security, safe secrets handling, transactional inventory updates.
4. Be deployable to the cloud for a deployments lesson.
5. Be appropriate for mixed-age training groups, including minors.

## 2. Users and roles

| Role | Summary |
|---|---|
| Guest | Browse, search, view details, add to session cart |
| Customer | Plus saved cart, checkout, order history, XP, badges, profile |
| Staff | Plus manage courses, seats, categories, paths; view orders |
| Owner | Plus manage staff roles; delete courses |

## 3. Feature summary

| # | Feature (brief) | Epic | Key stories | Highlights |
|---|---|---|---|---|
| 1 | Add to cart | E3 | US-301 - US-307 | Seats as quantity (1-5), guest session cart, saved cart when signed in, merge on sign-in, live price/seat check |
| 2 | Checkout & order confirmation | E4 | US-401 - US-408 | Sign-in required, no card, demo checkbox, atomic seat deduction, stock conflict handling, confirmation page with celebration, email saved to `outbox/` folder + `email_outbox` table |
| 3 | Product search | E1 | US-101 - US-106 | Keyword search, filters (category, level, price, duration, path, available), sort, empty state, featured sections |
| 4 | Product detail | E2 | US-201 - US-205 | Full course info, locked-module sneak peek, real seat meter, path position, related courses |
| 5 | Customer register / sign in | E5 | US-501 - US-505 | Supabase Auth email + password, generic errors, Learner Passport profile |
| 6 | Owner & staff product management | E7 | US-701 - US-711 | Role-gated admin, course CRUD with image upload, publish, seat adjustment, orders view, dashboard, owner manages staff |
| + | Gamification (from UI vision) | E6 | US-601 - US-606 | XP, 5 levels, badges, learning-path skill tree, celebrations, ethical rules |

## 4. UI/UX summary

- **Core metaphor:** "Unlock your skill map". Each course is a node on a learning path; buying unlocks it.
- **Curiosity drivers:** locked modules, locked badges, unfilled path nodes, XP rewards shown on every card, "Unlock preview" in cart.
- **Professional base:** clean light theme, indigo primary, amber for XP, consistent cards, clear pricing.
- **Admin is plain**, with no gamification.
- **Ethical rules:** no fake timers, fake scarcity, random rewards, leaderboards, or penalties.
- 16 screens (S1-S16) defined for desktop and mobile in doc 02.

## 5. Non-functional summary

- **Auth:** Supabase Auth, email confirmation off for demo, tokens only in session state, generic errors, rate limits on.
- **Security:** RLS on every table, anon key only in the app, service role key never in the app, server-side checkout/XP functions, input validation, HTML escaping, restricted uploads, audit log.
- **Privacy & child safety:** minimal personal data (name, email), preset avatars, no tracking, no public profiles.
- **Integrity:** single-transaction checkout, no negative seats, price snapshot on orders, no duplicate orders.
- **Performance:** < 3 s pages, < 1 s search, cached public catalog, fresh seat reads at checkout.
- **Deployment:** Streamlit Cloud; outbox files are temporary in the cloud, so emails are also stored in the database.

## 6. Data model overview (logical)

To be finalized as SQL migrations in `supabase/migrations/`.

| Table | Purpose | Key fields |
|---|---|---|
| `profiles` | One row per auth user | id (= auth user id), display_name, avatar, interests, role, xp_total, level, reduce_motion |
| `categories` | Course categories | id, name, icon, sort_order |
| `courses` | The products | id, slug, title, summary, description, category_id, level, duration_hours, price, seats_total, seats_available, instructor_name, outcomes, prerequisites, tags, image_url, xp_reward, is_published, is_featured, updated_by, timestamps |
| `course_modules` | Syllabus | id, course_id, position, title, description |
| `learning_paths` | Paths for the skill tree | id, name, description, bonus_xp, badge_code |
| `learning_path_courses` | Courses in a path | path_id, course_id, position |
| `cart_items` | Saved carts | user_id, course_id, quantity |
| `orders` | Orders | id, order_number, user_id, status, total, idempotency_key, created_at |
| `order_items` | Order lines | order_id, course_id, title_snapshot, unit_price, quantity |
| `email_outbox` | Saved confirmation emails | id, order_id, user_id, to_email, subject, html_body, file_name, created_at |
| `xp_events` | XP history | id, user_id, action, points, created_at |
| `badges` / `user_badges` | Badge definitions and awards | code, name, description, icon / user_id, badge_code, awarded_at |
| `audit_log` | Admin actions | id, actor_id, action, entity, entity_id, before, after, created_at |

Key database function: `place_order(idempotency_key)` handles checkout, seat deduction, XP and badges in one transaction.

## 7. Scope

**In scope:** the features in section 3, seed data (4 categories, 12-16 courses, 3 paths, demo accounts), deployment guide.

**Out of scope:** real payments, taxes, coupons, real emails (including auth emails), course content delivery/LMS, reviews, social login, MFA, multi-language, multi-currency.

## 8. Open questions

| # | Question | Default if not answered |
|---|---|---|
| Q1 | **Vercel:** Streamlit can't run properly on Vercel (it needs a long-running WebSocket server). Should the deployment lesson use Streamlit Cloud only, or Streamlit Cloud plus a container host (Render / Railway / Hugging Face Spaces / Cloud Run)? | Streamlit Cloud only; explain why Vercel doesn't fit as a teaching point |
| Q2 | Is order cancellation (US-408) needed for the demo? | Could; build last |
| Q3 | Should password reset (US-505) use Supabase's reset email? It would send a real email. | No; show "Ask your trainer" |
| Q4 | Quantity limit of 5 seats per course per order OK? | Yes |
| Q5 | Display currency (USD) and price ranges for seed courses? | USD, $0 - $499 |
| Q6 | Brand name and logo for the store? | Placeholder name "SkillForge Academy" (fictional) |

## 9. Suggested build order

1. Supabase schema, RLS, seed data.
2. Auth (register, sign in, sign out, roles).
3. Catalog, search, course detail.
4. Cart.
5. Checkout transaction, confirmation page, outbox email.
6. Admin: course CRUD, seats, orders, staff management.
7. Gamification: XP, levels, badges, path map, celebrations.
8. Deployment and trainer guide.

## 10. Traceability

| Feature | Stories (doc 01) | Screens (doc 02) | Key NFRs (doc 03) |
|---|---|---|---|
| Add to cart | US-301 - 307 | S3, S4, S6 | NFR-SEC-13, NFR-PERF-04 |
| Checkout & confirmation | US-401 - 408 | S7, S8, S11 | NFR-SEC-09, NFR-DATA-01 - 04, NFR-DEP-04, NFR-REL-02 |
| Search | US-101 - 106 | S1, S2, S3 | NFR-PERF-02, NFR-PERF-03 |
| Product detail | US-201 - 205 | S4, S5 | NFR-SEC-15 |
| Register / sign in | US-501 - 505 | S9, S10 | NFR-AUTH-01 - 08, NFR-SEC-01 - 03, NFR-PRIV-01 - 06 |
| Owner & staff management | US-701 - 711 | S12 - S15 | NFR-SEC-02, 05 - 10, 16, 18 |
| Gamification | US-601 - 606 | S1, S4, S5, S8, S10 | NFR-SEC-09, NFR-PRIV-04, NFR-UX-03 |
