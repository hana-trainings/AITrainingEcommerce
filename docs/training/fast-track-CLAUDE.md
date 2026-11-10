# AI Training E-commerce: rules for Claude Code

<PRODUCT NAME>: a demo app for a high school class (replace this line with one sentence about your product). Streamlit + Supabase. No real payments or emails.

## Read first
- Stories and plan: `docs/planning/work-division-plan.md`, `docs/requirements/01-product-features-user-stories.md`
- Look and feel: `docs/requirements/02-ui-ux-requirements.md` (section 3 color tokens win)
- Security and quality: `docs/requirements/03-non-functional-requirements.md`

## Layers (explain these to the student when asked)
page (`app/pages`) -> service (`app/services`) -> Supabase table + security rule (`supabase/migrations`)
Pages never call Supabase directly. Reusable UI is in `app/components`. Business rules live in services or database functions.

## Rules
- Build only the story you are asked for. Touch only its files. Ask before changing `app/streamlit_app.py`, `requirements.txt`, service or component signatures, or any merged migration (add a NEW migration file instead).
- Never read, print or commit `.env`, `.streamlit/secrets.toml` or any key. The service role key is never used in the app.
- Add files to git by name, never `git add -A`. Never push to `main`. Never merge a PR.
- Keep code beginner-friendly: clear names, short functions, a comment for each non-obvious "why", type hints on service functions.
- If a test fails, say whether the test or the code is wrong before changing anything. Never delete a test to get green.
- Ethical gamification: no fake timers, fake scarcity, random rewards, leaderboards or penalties.

## Commands (venv active)
- Run: `streamlit run app/streamlit_app.py`
- Lint: `ruff check .`
- Tests: `python -m pytest tests/unit -q`

## Skills
- Streamlit pages and components: `developing-with-streamlit`
- SQL, migrations, security rules: `supabase-postgres-best-practices`
- Layout, color, accessibility: `ui-ux-pro-max`

## When reviewing (a separate, read-only session)
Report only. Do not edit files. Check scope, acceptance criteria, secrets, role checks and tests. End with VERDICT, BLOCKERS, SHOULD FIX, NOT CHECKED.
