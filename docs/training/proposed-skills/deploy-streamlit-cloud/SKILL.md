---
name: deploy-streamlit-cloud
description: Use (Tech Lead, in a separate deploy session) to prepare, deploy, smoke-test, and roll back the app on Streamlit Community Cloud with Supabase. Covers story L-03 and NFR-DEP.
---

# Deploy to Streamlit Community Cloud

Hosting is Streamlit Community Cloud (NFR-DEP-02). Vercel does not run Streamlit (needs a long-running WebSocket server); explain this as a teaching point (NFR-DEP-03).

## 1. Pre-deploy checklist (run from a clean checkout of `main`)
- [ ] CI is green on `main`; `ruff check .` and `python -m pytest tests/unit -q` pass.
- [ ] `requirements.txt` is complete and pinned; Python version noted (3.11+).
- [ ] Fresh clone runs locally with only README steps.
- [ ] `git ls-files` shows no `.env`, `secrets.toml`, or keys. Secret scanning is on.
- [ ] Supabase **cloud demo** project exists: migrations applied in order, seed loaded, email confirmation disabled for the demo, RLS enabled on every table (run the Supabase advisors / `get_advisors` check if available).
- [ ] The app reads settings from `st.secrets` or environment variables, with fail-fast if missing (NFR-SEC-11/12).
- [ ] Service role key is NOT in the app or in Streamlit secrets.

## 2. Deploy
1. Streamlit Community Cloud: New app, repo `<org>/AITrainingEcommerce`, branch `main`, main file `app/streamlit_app.py`.
2. Advanced settings: Python version, and paste the secrets as TOML:
```
SUPABASE_URL = "https://<project>.supabase.co"
SUPABASE_ANON_KEY = "<anon key only>"
```
3. Deploy. Read the build log; fix missing packages in `requirements.txt` through a normal PR.

## 3. Smoke test on the live URL
Home loads, search works, add to cart, sign in as demo customer, place order, seats go down, confirmation page, My Orders shows it, sign in as demo staff and see the order, owner can open Staff page, a customer cannot open admin pages.

## 4. Roll back
Revert the bad PR on GitHub (a new revert PR), or in Streamlit reboot the app / point to the previous good commit. If a migration caused it, add a new corrective migration. Never edit a merged one.

## 5. Record
Update `docs/deployment/` with: live URL, Supabase project name (no keys), steps used, how to reset demo data (`scripts/` demo reset), known limits (outbox files are temporary in the cloud; emails are also stored in `email_outbox`).

## Never
Put keys in the repo, chat, Issues, or screenshots. Share demo logins only through the team's private channel.
