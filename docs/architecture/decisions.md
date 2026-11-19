# Architecture and product decisions

This file records the answers to the open questions in [docs/requirements/00-consolidated-requirements.md §8](../requirements/00-consolidated-requirements.md#8-open-questions). Each answer uses the stated default unless noted. If a decision changes later, add a new dated entry below the old one instead of editing it, so the history stays readable.

| # | Question | Decision | Status |
|---|---|---|---|
| Q1 | Where do we deploy? | Streamlit Community Cloud only. Vercel is explained as a teaching point, not used. | Decided |
| Q2 | Is order cancellation (US-408) needed? | Yes, built: staff can cancel; seats go back. | Decided |
| Q3 | Password reset by email (US-505)? | No. The sign-in page says "Forgot password? Ask your trainer." | Decided |
| Q4 | 5 seats per course per order? | Yes. | Decided |
| Q5 | Currency and price range? | USD, seed prices $0 to $499. | Decided |
| Q6 | Store name and logo? | "SkillForge Academy" (fictional), simple icon, no real brand. | Decided |

---

## Q1. Deployment target: Streamlit Community Cloud only

**Decision.** The app is deployed to Streamlit Community Cloud from the `main` branch, with `app/streamlit_app.py` as the main file and the two settings (`SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`) in the app's Secrets box. No second host is set up. Steps: [docs/deployment/streamlit-cloud.md](../deployment/streamlit-cloud.md).

**Why.**
- Streamlit keeps a long-running Python process per user session and talks to the browser over a WebSocket. Session data (sign-in, cart) lives in that process's memory.
- Vercel runs short-lived serverless functions. They can't keep a WebSocket open and don't share memory between requests, so a Streamlit app can't run properly there (NFR-DEP-03).
- Streamlit Cloud is free, deploys straight from GitHub, and is built for this. One target keeps the deployment lesson short.

**Consequences.**
- The cloud file system is temporary, so confirmation emails are also saved in the `email_outbox` table (NFR-DEP-04).
- Refreshing the browser tab starts a new session and signs the user out (NFR-AUTH-06). Accepted for the demo.
- If a second target is wanted later, use a container host (Render, Railway, Hugging Face Spaces, Google Cloud Run). The code doesn't need to change, only configuration (NFR-DEP-06).

## Q2. Order cancellation (US-408): built

**Decision.** Orders have a status, `confirmed` or `cancelled`. Staff and owner can cancel a confirmed order. Cancelling gives the seats back to the courses. A cancelled order can't be changed again.

**Why.** It shows a real order lifecycle and an inventory rule that runs inside the database, which is useful for teaching.

**How it is enforced.** Customers have no right to change orders at all. Staff may update only the `status` column (column grant plus RLS policy in migration 0012). A trigger allows only `confirmed -> cancelled` and returns the seats (migration 0007). XP and badges are **not** taken back, because the gamification rules forbid penalties (US-606).

## Q3. Password reset: no email, "Ask your trainer"

**Decision.** Supabase's reset email is not enabled. The sign-in page shows "Forgot password? Ask your trainer." The trainer deletes the learner's account in the Supabase dashboard and the learner registers again.

**Why.** The demo sends no real emails of any kind (out of scope in doc 00 §7), learners use made-up addresses, and many are minors. Email confirmation is off for the same reason (NFR-AUTH-02).

## Q4. Seat limit: 1 to 5 per course per order

**Decision.** A cart line holds 1 to 5 seats of a course.

**How it is enforced.** The form limits the input, and the database has `check (quantity between 1 and 5)` on both `cart_items` and `order_items` (migrations 0006 and 0007), so the rule holds even if the page is bypassed.

## Q5. Currency and prices: USD, $0 to $499

**Decision.** All prices are in US dollars, stored as `numeric(10,2)` (never floating point) and shown like `$59.00`. Seed courses stay within $0 to $499 (today they run from $0 for one free course to $179). No taxes, coupons or other currencies.

**Note.** The database allows prices up to $9,999 (US-703 AC1), so staff can create pricier courses in class; $0 to $499 is the range used by the seed data.

## Q6. Name and logo: "SkillForge Academy"

**Decision.** The store is called **SkillForge Academy**, a made-up name. It uses the Material "school" icon next to the name (`app/components/header.py`) instead of a designed logo. Courses, instructors and companies in the seed data are all fictional.

**Why.** No real brand is imitated, and nothing suggests the courses can really be bought.
