# Deploy SkillForge Academy to Streamlit Community Cloud

This guide puts the app on the internet for the deployment lesson (L-03, NFR-DEP-01 to NFR-DEP-06). It takes about 30 minutes the first time.

The same code runs on a laptop and in the cloud. The only difference is configuration: which Supabase project the app talks to, and where its two settings come from (NFR-DEP-06).

| | Local | Cloud demo |
|---|---|---|
| App runs on | Your laptop (`streamlit run app/streamlit_app.py`) | Streamlit Community Cloud |
| Settings come from | `.env` or `.streamlit/secrets.toml` | The app's **Secrets** box in Streamlit Cloud |
| Database | Shared **dev** Supabase project | A **cloud demo** Supabase project (or the dev project if you only have one) |
| Confirmation emails | `outbox/` files + `email_outbox` table | `email_outbox` table (files are temporary) |

## Before you start

- The Must stories are merged into `main`, and the unit tests pass on `main` (`python -m pytest tests/unit -q`).
- You have a GitHub account that can see the repository, and a Supabase account.
- You know the demo account passwords. They are never written in the repo (NFR-SEC-04).

## Step 1: prepare the Supabase project

You can deploy against the dev project. A separate **cloud demo** project is better: class experiments on dev won't break the live demo, and you can reset it freely.

1. In Supabase, create a project (or pick the existing one). Note its name: you will check it before every SQL step.
2. **Apply the database.** Follow [apply-database.md](apply-database.md): run every file in `supabase/migrations/` **in number order** (0001 first, then every later number that exists, including migrations added by stories), then create the demo accounts ([demo-accounts.md](demo-accounts.md)), then run `supabase/seed/01_catalog.sql` and `supabase/seed/02_sample_orders.sql`.
3. **Turn email confirmation off** (NFR-AUTH-02, US-501 AC5): **Authentication > Sign In / Providers > Email**, switch **Confirm email** off and set the minimum password length to 8. No emails are ever sent by this demo, so new accounts must work straight away.
4. Leave Supabase's **auth rate limits** on (NFR-AUTH-08).
5. **Run the two security tests** in the SQL editor: `supabase/tests/place_order_test.sql` and `supabase/tests/rls_test.sql`. Each prints only `PASS` notices and ends with `ROLLBACK`, so they leave nothing behind. Do not deploy if either one shows an `ERROR`.
6. **Copy the two settings** from **Project Settings > API Keys** (or **Connect**):
   - Project URL, for example `https://abcdefghijkl.supabase.co`
   - The **publishable** key, which starts with `sb_publishable_`

> **Never use the secret key.** Keys that start with `sb_secret_` (the old "service role" key) skip every security rule in the database. The app refuses to start if it gets one, and it must never be pasted into Streamlit Cloud, GitHub, a chat or a screenshot. The publishable key is safe to put in the app because Row Level Security decides what each user may see.

## Step 2: create the app on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub. Allow Streamlit to see the repository if asked (for a private repo, it needs that permission).
2. Click **Create app**, then choose to deploy from a GitHub repository.
3. Fill in:

   | Field | Value |
   |---|---|
   | Repository | `<your-org>/AITrainingEcommerce` |
   | Branch | `main` |
   | Main file path | `app/streamlit_app.py` |
   | App URL | Something short, for example `skillforge-academy-demo` |

4. Open **Advanced settings**:
   - **Python version:** `3.12` (the project needs 3.11 or newer and is tested on 3.12).
   - **Secrets:** paste exactly this, with your own values:

     ```toml
     SUPABASE_URL = "https://<your-project-ref>.supabase.co"
     SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
     ```

     These are the only two settings the app needs. Nothing else goes here: no `sb_secret_` key, no database password, no demo passwords.
5. Click **Deploy**. The first build installs `requirements.txt` from the repo root and takes a few minutes. The theme comes from `.streamlit/config.toml` automatically.

Every merge to `main` redeploys the app on its own. To change a secret later: **your app > Settings > Secrets**, edit, save. The app restarts with the new values.

**Who can open the app:** in **Settings > Sharing** you can keep the app private and invite the class by email, or make it public. The data is fictional and the demo has no real payments, but a private app is a sensible default for a class with minors.

## Step 3: smoke test the live app

Tick every line. Use the demo accounts; do this in a private browser window so no old session gets in the way.

| # | Check | Expected |
|---|---|---|
| 1 | Open the app URL | Home page loads in under 3 seconds, with featured courses and no error box |
| 2 | Courses: search "sql", filter by a category | Results update; a nonsense search shows the friendly "no results" state |
| 3 | Open a course | Details, seat meter and locked module preview are shown |
| 4 | As a guest, add a course to the cart, then click Checkout | You are asked to sign in; the cart is kept |
| 5 | Sign in as the demo **customer** | Header shows name, level and XP; you return to checkout |
| 6 | Tick "I understand this is a demo order", place the order | Confirmation page with an `ORD-YYYYMMDD-XXXX` number, XP earned, celebration |
| 7 | My orders | The new order is at the top; "View confirmation email" shows the email |
| 8 | Sign out, sign in as **staff** | Admin menu appears; the orders list shows the customer's order; seats went down |
| 9 | As staff, open the Manage staff page by URL | "You don't have access" |
| 10 | Sign in as **owner** | Manage staff works; switching a user between customer and staff works |
| 11 | Register a brand-new account | Works straight away (no confirmation email), starts as a customer with 50 XP |
| 12 | Wrong password on sign in | Generic "Email or password is incorrect" |

If all pass, share the link. After the lesson, reset the data with `scripts/reset_demo.sql` (see [trainer-guide.md](trainer-guide.md)).

## Confirmation emails in the cloud

The app saves each confirmation email twice: as an HTML file in `outbox/` and as a row in the `email_outbox` table (US-406, NFR-DEP-04).

Streamlit Cloud's file system is **temporary**: files written while the app runs vanish when the app restarts, redeploys or goes to sleep. So in the cloud, `outbox/` files are just a bonus. The copy you can rely on is the database row, which is what "View confirmation email" in **My orders** and the staff order view show. No email is ever really sent.

## Why not Vercel? (teaching point, decision Q1)

Vercel is great for websites and serverless functions, but it is the wrong shape for Streamlit:

- **Streamlit needs a server that keeps running.** Each browser tab keeps a live **WebSocket** connection to one Python process, which holds that user's `session_state` (their sign-in and cart) in memory.
- **Vercel runs serverless functions.** Each request starts a short-lived function that stops after it answers. Functions can't hold a WebSocket open for a whole visit, and the next request may land on a different machine with empty memory.
- Result: a Streamlit app on Vercel either doesn't start, or keeps disconnecting and loses the user's session.

So we deploy to **Streamlit Community Cloud**, which is built for exactly this. If you want a second deployment target later, choose a host that runs a long-lived container, such as Render, Railway, Hugging Face Spaces or Google Cloud Run. See [../architecture/decisions.md](../architecture/decisions.md).

## Troubleshooting

| What you see | Likely cause | Fix |
|---|---|---|
| "The app is not configured yet: Missing setting(s): SUPABASE_URL ..." | Secrets box empty or a name misspelt | Settings > Secrets: exactly `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`, values in double quotes |
| "SUPABASE_PUBLISHABLE_KEY holds a SECRET key" | An `sb_secret_` key was pasted | Replace it with the `sb_publishable_` key. Then **rotate the secret key** in Supabase (it is now exposed) |
| Build fails with `ModuleNotFoundError` | A package is missing from `requirements.txt`, or the wrong Python version | Add the pinned package in a PR, then reboot the app |
| Build fails on a package version | Python version too old for a pinned package | Delete the app and redeploy with Python 3.12 (the version can't be changed in place) |
| Catalog is empty, but no error | Seed not run on **this** Supabase project, or the URL points to another project | Check the project ref in `SUPABASE_URL`; run `01_catalog.sql` there |
| Every page shows a friendly error / "could not load" | Migrations missing on this project, or the project is paused | Supabase dashboard: restore the project if paused; run any missing migrations in order |
| Registering says it worked but sign-in fails | Email confirmation is still on | Authentication > Sign In / Providers > Email: turn **Confirm email** off |
| Sign in works but Admin menu is missing for staff | Role not set on this project | Run the role `update` from [demo-accounts.md](demo-accounts.md) step 2 |
| User is signed out after refreshing the tab | Expected (NFR-AUTH-06): a refresh starts a new Streamlit session | Sign in again; explain this known limitation to learners |
| App shows "Zzz, this app has gone to sleep" | No visits for a while (free tier) | Click the wake-up button and wait about a minute. Open it before class starts |
| Supabase project paused | Free projects pause after about a week without activity | Supabase dashboard > Restore project. Do this the day before class |
| Old `outbox/` files are gone | Expected in the cloud (temporary file system) | Use "View confirmation email", which reads the `email_outbox` table |
| Changes merged but the app shows old code | Redeploy still running or failed | App menu > Manage app > logs; or Reboot app |

## Checklist: what must never happen

- No `.env`, `.streamlit/secrets.toml`, key or password is committed to GitHub.
- No `sb_secret_` key in the Secrets box, in code, in an Issue, PR or screenshot.
- No real emails sent and no real payments taken.
- The demo is never pointed at a project holding real personal data.
