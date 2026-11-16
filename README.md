# SkillForge Academy (AI Training E-commerce)

A demo course store built with **Streamlit** and **Supabase** for a training class.
It sells fictional AI and Data courses. **No real payments and no real emails.**

## Local setup (Windows, PowerShell)

You need Python 3.11 or newer, Git, and the Supabase **publishable** key (`sb_publishable_...`)
for the team's dev project (your Tech Lead shares it privately). Never use or share the
secret key (`sb_secret_...`).

```powershell
# 1. Get the code
git clone <your-team-repo-url>
cd AITrainingEcommerce

# 2. Create a virtual environment (Python 3.11 or newer; 3.12 also works)
py -3.11 -m venv .venv

# 3. Turn it on (your prompt then starts with "(.venv)")
.\.venv\Scripts\Activate.ps1
#    If PowerShell blocks scripts, run this once, then try again:
#    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 4. Install the pinned packages
python -m pip install -r requirements.txt

# 5. Create your settings file and fill in SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY
Copy-Item .env.example .env
notepad .env

# 6. Run the app (opens http://localhost:8501)
streamlit run app/streamlit_app.py

# 7. Lint and run the unit tests (no internet or keys needed)
ruff check .
python -m pytest tests/unit -q
```

Instead of `.env` you can use `.streamlit/secrets.toml` (copy `.streamlit/secrets.toml.example`).
Both files are git-ignored. If a setting is missing, the app stops and tells you which one.

Good to know:
- Refreshing the browser tab starts a new session, so you must sign in again (NFR-AUTH-06).
- Errors in the browser are generic on purpose. See the full error in the terminal, or run
  `streamlit run app/streamlit_app.py --client.showErrorDetails=full` while developing.

## How the code is organized

```
app/
├── streamlit_app.py   # entry point: settings check, navigation, header (stories don't edit it)
├── pages/             # one file per screen (stubs say "Coming soon - US-xxx")
├── components/        # shared UI: course card, seat meter, XP, badges, guards, states, header
├── services/          # the only code that talks to Supabase (see docs/architecture/service-contracts.md)
├── models/domain.py   # data shapes shared by services and pages
├── config/            # settings loading and page routes
└── utils/             # logging and text helpers
assets/styles/         # design tokens (theme lives in .streamlit/config.toml)
supabase/              # SQL migrations, seed data
tests/unit/            # pytest + Streamlit AppTest with a fake Supabase client (tests/conftest.py)
tests/integration/     # tests against a real test Supabase project
docs/                  # requirements, plan, architecture, deployment
```

Layers: **page -> service -> Supabase table + security rule (RLS)**. Pages never import `supabase`.

## Building a story

1. Read your story in `docs/planning/work-division-plan.md` and the service it needs in
   `docs/architecture/service-contracts.md`.
2. Fill in the stub page and the `NotImplementedError` service functions. Keep the signatures.
3. Add unit tests using the `fake_client` / `session_state` fixtures from `tests/conftest.py`.
4. `ruff check .` and `python -m pytest tests/unit -q` must pass before you open a PR.

See `CLAUDE.md` for the team rules and `docs/requirements/` for the requirements.
