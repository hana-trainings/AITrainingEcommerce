# AI Training E-commerce: project rules for Claude Code

Demo / training store ("SkillForge Academy", fictional). Streamlit UI + Supabase (Postgres, Auth, Storage).
No real payments, no real emails. Learners include minors.

## Read first
- Plan and story list: `docs/planning/work-division-plan.md`
- Requirements: `docs/requirements/00` to `03` (stories, UI/UX, NFRs)
- Service contracts: `docs/architecture/service-contracts.md`
- Prompt playbooks: `docs/training/`

## Architecture rules (NFR-MNT-01)
- Pages in `app/pages/` never call Supabase directly. They call `app/services/`.
- Reusable UI goes in `app/components/`. Use the existing component signatures.
- Business rules live in services or in database functions, never in page code.
- Python 3.11+, type hints on service functions, format and lint with `ruff`.
- Code must be readable by high school learners: clear names, short functions, a comment for every non-obvious *why*.

## Working rules
- One story per branch and per PR. Touch only the files listed for the story in the plan.
- Never edit a merged migration. Add a new file in `supabase/migrations/`.
- Never change a service signature or component signature inside a story PR. Ask the Lead for a separate PR.
- Never commit `.env`, `.streamlit/secrets.toml`, or any key. The service role key is never used in the app.
- Never use `git add -A`. Add files by name, then check `git status`.
- Do not push to `main`. Do not merge your own PR.
- Ethical gamification: no fake timers, no fake scarcity, no random rewards, no leaderboards, no penalties.

## Commands
- Install: `pip install -r requirements.txt`
- Run app: `streamlit run app/streamlit_app.py`
- Lint: `ruff check .`
- Tests: `python -m pytest tests/unit -q` (integration: `python -m pytest tests/integration -q`)

## Skills to use
- Streamlit code: `developing-with-streamlit`
- Database, SQL, RLS: `supabase-postgres-best-practices`
- Look and feel, accessibility: `ui-ux-pro-max`
- Team workflow: `implement-story`, `write-tests`, `manual-test-plan`, `review-pr`, `git-pr-workflow`, `deploy-streamlit-cloud`

## Sessions
- Build session: writes code for one story.
- Review session: a NEW session that did not write the code. Read-only. Never fixes code, only reports.
- Deploy session: a NEW session used only by the Tech Lead for release steps.
