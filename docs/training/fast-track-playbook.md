# Fast-Track Playbook: Idea to Live App in 2 Sessions (4 hours)

The full [implementation-playbook.md](implementation-playbook.md) is the "do it properly" version (its Part 3 has the long foundation prompts). This page is the **classroom version**: same AIDLC steps, far fewer moving parts. It uses only the 3 installed skills, one `CLAUDE.md` file, about 10 prompts, and no worktrees.

> **Goal:** every student sees a feature travel through every layer (database, service, page, test, review, deploy) and ends with a live URL.

## 1. How we make it fit in 4 hours

| Speed-up | Instead of |
|---|---|
| Each team builds its **own foundation before class** (database, security rules, sample data, sign-in, app shell, empty service and page stubs). See Section 3 | Building it in class |
| Each student builds **3 Must stories**, not 15 | The full story list |
| **One big build prompt per story** that plans, codes and tests together | Separate plan, build, test, manual-plan prompts |
| One branch and **one PR per student** per session, several story commits inside | One PR per story |
| One **fresh-session review prompt** | Review skill, reviewer sub-agent |
| Sub-agents for two stories at once in **one folder**, only when the files differ | Worktrees |
| Printed checklist | Issues and project board |

What stays, even when rushed: **never commit keys, never push to `main`, the AI that wrote the code does not approve it, and a person clicks through the app.**

## 2. AIDLC map

| AIDLC phase | Already done | In Session 1 | In Session 2 |
|---|---|---|---|
| Idea, requirements, plan | Playbook 1 | Read your 3 stories | |
| Design (data, security, screens) | **Team pre-class foundation** | Layer tour | |
| Build | Foundation (pre-class) | **Build 3 stories** | Fix and finish |
| Test | | Unit tests, quick check | Manual test, swap with a teammate |
| Review | | | **Fresh-session review**, human approval |
| Deploy | Supabase cloud project (pre-class) | | **Streamlit Cloud** |
| Operate and learn | | | Smoke test live, recap |

## 3. Pre-class assignment: every team builds its own foundation

Each team has its own product, so each team builds its own foundation **before Session 1**. If this is not finished, the 4 hours are gone. The foundation is the part that is the same for any app: database, security rules, sample data, sign-in, app shell, and empty places for the stories to go.

**Deadline:** finished and checked 48 hours before Session 1. The trainer signs off 24 hours before.
**Team time:** about 4 to 6 hours in total, spread over a few days. Most of it is Claude working while you read and check.

### 3.1 Who does what

| Who | Pre-class tasks |
|---|---|
| **Tech Lead** | Accounts (3.2) and Prompts A to F (3.3), each as its own small PR; tag `foundation-v1` |
| **Users 1, 2, 3** | Machine setup (3.2, last row); read your team's requirement docs and your stories; **review the Lead's PRs by running the branch** and writing one comment on each. This is how you learn the foundation without building it |

The Lead can hand a prompt to a user (for example Prompt F), but only one person edits at a time and every change goes through a PR.

### 3.2 Accounts and setup (Day 1)

| Item | Detail |
|---|---|
| GitHub | Team repo with all four people added. Branch protection on `main` after the first merge: pull request needed, 1 approval |
| Supabase **dev** project | Free project for everyone to develop on. Share only the **anon** key, privately |
| Supabase **cloud demo** project | A second free project used for the live app. Keep its keys with the Lead only |
| Streamlit Community Cloud | Account linked to GitHub (used in Session 2) |
| Every laptop | Python 3.11, Git, `gh` signed in, VS Code and Claude Code working, repo cloned, venv created, `pip install -r requirements.txt` done, `.env` filled with the dev anon key, app opens. Steps are in Part 4 of the [full playbook](implementation-playbook.md) |

### 3.3 The six foundation prompts (Tech Lead)

Use your own documents: requirements `docs/requirements/00` to `03` and your `docs/planning/work-division-plan.md`. Replace `<PRODUCT>` with your product name. Put the skills in the prompt exactly as written. Copy [fast-track-CLAUDE.md](fast-track-CLAUDE.md) to the repo root as `CLAUDE.md` first and replace the product name.

**Prompt A. Repo basics**

```text
Read CLAUDE.md and my docs in docs/requirements and docs/planning. Create:
.gitignore (blocks .env, .streamlit/secrets.toml, .venv, outbox), .github/pull_request_template.md with a short checklist
(one story, tests pass, no secrets, screenshots), and .github/workflows/ci.yml that runs ruff check . and pytest on every pull request.
Do not touch anything else. List the branch protection settings I should switch on in GitHub.
```

**Prompt B. Database and security rules**

```text
Use the supabase-postgres-best-practices skill. Using the data model in docs/requirements/00 (section "data model"), write SQL migrations in
supabase/migrations/ (numbered, one concern per file) for every table: primary keys, foreign keys with indexes, CHECK constraints
for anything that must never be negative or out of range.
Then a separate migration with Row Level Security for each role in the requirements (for example guest, customer, staff, owner),
with a one-sentence comment on every policy explaining who can do what and why.
Then tell me exactly how to apply these files to my Supabase DEV project (SQL editor or supabase CLI). Do not run anything yourself.
```

**Prompt C. The one "all or nothing" function, and sample data**

```text
Use the supabase-postgres-best-practices skill. Find in docs/requirements the one action that changes several tables at once and
must never half-succeed (for example placing an order, booking, or submitting an application). Write it as ONE Postgres function in a new migration
so everything happens in a single transaction, it can be safely repeated (idempotency key), and it returns a clear error when it cannot complete.
Then write supabase/seed/ sample data: realistic fictional records (about 12 items, categories, 3 demo accounts for the roles, a few sample records of the main transaction).
Never write real passwords into the repo. Put the demo account steps in docs/deployment/demo-accounts.md.
Add a short SQL test file that proves the function cannot over-book and cannot run twice for the same key.
```

**Prompt D. Config, database client, sign-in**

```text
Use the developing-with-streamlit skill. Create requirements.txt with streamlit>=1.57, supabase, pytest, ruff (pinned) and note Python 3.11+.
Write app/config settings that load SUPABASE_URL and SUPABASE_ANON_KEY from st.secrets or .env and stop with a clear message if missing.
Write app/services/supabase_client.py and app/services/auth.py with sign_in, sign_out, register, current_user and require_role.
Add a working sign-in page. Tokens stay in st.session_state, error messages are generic ("Email or password is wrong"), nothing personal is logged.
```

**Prompt E. App shell and empty stubs**

```text
Use developing-with-streamlit and ui-ux-pro-max (colors and tokens in my UI/UX doc win). Create app/streamlit_app.py with role-based navigation and a header.
Register EVERY screen in my sitemap as a page stub in app/pages/ that shows "Coming soon - <story id>" and checks the right role.
For every story in my work plan create the service function it needs in app/services/ with a signature, type hints, a docstring and
raise NotImplementedError, and list them in docs/architecture/service-contracts.md.
Create simple working versions of the shared UI pieces in app/components/ with their FINAL function signatures (for example item card, status badge, empty state, error state, access denied).
Stories must never need to edit streamlit_app.py after this.
Check my plan: tell me about any story that has no page or no service function.
```

**Prompt F. Tests and README**

```text
Create tests/conftest.py with a fake Supabase client and sample data, one example unit test for a service function,
and one example Streamlit AppTest for a page. Update README.md with exact Windows steps: clone, venv, pip install, .env, run, test.
Run ruff check . and python -m pytest tests/unit -q and show me the result.
```

After each prompt: **run the app and the tests, read the diff, then commit by file name on a branch and open a PR.** A teammate reviews it by running the branch.

### 3.4 Ready check (all must be true, then tag `foundation-v1`)

- [ ] A teammate does a **fresh clone** and gets the app running by following only the README
- [ ] Every page in the sitemap opens and shows "Coming soon" without an error
- [ ] The demo customer, staff and owner can sign in and see the right menu; the wrong role sees "access denied"
- [ ] The all-or-nothing function passes its SQL test on the dev project
- [ ] `ruff check .` and `python -m pytest tests/unit -q` pass; CI is green on `main`
- [ ] No `.env`, key or password in the repo: run `git ls-files` and look
- [ ] `docs/architecture/service-contracts.md` lists a function for every story
- [ ] The **cloud demo** Supabase project already has the migrations and seed applied, and email confirmation is off
- [ ] **Dry run:** the Lead builds the smallest story with Prompt 3 (Section 5) and times it. If it takes more than 30 minutes, simplify the story list

```text
Tag the current main as foundation-v1 and push the tag.
```

### 3.5 Trainer sign-off (24 hours before Session 1)

The trainer asks each team for the repo link and checks: the tag exists, CI is green, a fresh clone runs by the README, the three roles work, and every student has a story list (Section 4). A team that fails any item gets a call that day, not a surprise in class.

---

## 4. Who builds what

Each student builds **3 stories**. Pick them from your own work-division plan with these rules:

| Rule | Why |
|---|---|
| **Must** priority only | Nothing optional on a 4-hour clock |
| No unmet "Depends on" (a story can depend on an earlier story in the **same** student's list) | Nobody waits for a teammate |
| Each student's list touches **different page files** | Fewer merge conflicts |
| At least one story per student that reaches the database | Everyone sees every layer |
| One extra "if finished early" story each | Fast builders stay busy |
| Tech Lead: help, unblock, merge, deploy | |

Let Claude suggest the lists, then the team agrees:

```text
Read section 3 of docs/planning/work-division-plan.md and the priorities in docs/requirements/01.
For my team of 3 students, propose 3 Must stories each plus one extra each, following these rules:
no unmet dependencies across students, different page files per student, each student has at least one story that reads or writes the database.
Show a table: student, order, pick code, story ID, title, page file, service function, depends on. Do not edit files.
```

Example from the AI Training E-commerce plan (yours will differ):

| Student | Theme | Story 1 | Story 2 | Story 3 | If finished early |
|---|---|---|---|---|---|
| **User 1** | Browse | U1-03 US-101 Browse catalog (`courses.py`) | U1-04 US-201 Course details (`course_detail.py`) | U1-05 US-102 Keyword search (`courses.py`) | U1-14 Learning Paths page |
| **User 2** | Buy | U2-01 US-301 Add to cart | U2-02 US-302 View cart (`cart.py`) | U2-03 US-402 Place order (`checkout.py`) | U2-15 Order history |
| **User 3** | Account and admin | U3-05 US-501 Register (`register.py`) | U3-01 US-702 Admin course list (`admin_courses.py`) | U3-03 US-703 Create course (`admin_course_form.py`) | U3-06 Publish / unpublish |

Order inside a list matters when a later story builds on an earlier one (User 1: U1-05 after U1-03; User 2: U2-01, U2-02, U2-03 in order). Stories on different files can run in parallel (Section 6).

---

## 5. Session 1: Build (2 hours)

| Time | Activity |
|---|---|
| 0:00 - 0:15 | Start the app, take the layer tour (Prompt 1) |
| 0:15 - 0:30 | Plan your 3 stories (Prompt 2) |
| 0:30 - 1:30 | Build the 3 stories (Prompt 3), about 20 minutes each |
| 1:30 - 1:50 | Tests and quick check (Prompts 4 and 5) |
| 1:50 - 2:00 | Commit and push your branch (Prompt 6) |

**Rules:** about 20 minutes per story. Stuck for 10 minutes, ask the Tech Lead. A story not done at its time limit is parked, and you move on.

### Start

```powershell
cd C:\Projects\AITrainingEcommerce
git checkout main
git pull
git checkout -b user1-<theme>             # user2-<theme>, user3-<theme>
.\.venv\Scripts\Activate.ps1
streamlit run app/streamlit_app.py     # leave it running in one terminal
```

In a second terminal (venv active): `claude`

### Prompt 1. Layer tour (15 min)

```text
I am a high school student learning how a web app is built. Read CLAUDE.md and the folders app/, supabase/ and tests/.
Explain in plain English, with one small diagram, how ONE click travels through the layers:
page (app/pages) -> service (app/services) -> Supabase database table and its security rule (supabase/migrations).
Use one real button or form from our app as the example (pick the most important one) and name the real files and functions.
Then ask me 3 questions to check I understood. Do not change any files.
```

**Check:** you can answer: *Where does the page stop and the service start? What stops one user reading another user's data?*

### Prompt 2. Plan (15 min)

Press **Shift+Tab** until Claude shows plan mode (it cannot edit in this mode).

```text
I am User <1|2|3>. My stories this session are <pick codes and story IDs, in order>.
For each story read its row in docs/planning/work-division-plan.md, its acceptance criteria in doc 01,
and the matching stub in app/services and app/pages.
Give me a 5-line plan per story: files to change, functions to fill in, how I will see it in the app,
and one risk. List any file shared with another story. Do not write code.
```

**Check before you continue:** only your story files are named, and nothing in `streamlit_app.py` or `requirements.txt`. Then switch plan mode off (Shift+Tab).

### Prompt 3. Build one story (repeat for each, about 20 min)

```text
Build story <pick> (<US-id> <title>) end to end now, following the plan.
Use developing-with-streamlit for the page. Use ui-ux-pro-max for the layout (our colors and tokens in doc 02 section 3 win).
Use supabase-postgres-best-practices only if you must change SQL, and then only in a NEW migration file.
Fill in the existing service function and page; keep their signatures. Touch only this story's files.
Add 3 unit tests (happy path, error, edge case) using the fake client in tests/conftest.py.
Run ruff check . and the tests for this story. Then tell me in 5 lines: files changed,
how to see it in the app, which acceptance criteria are met, and what is not done.
```

Now **look at the app** (refresh the browser) and click it. If something is wrong, describe what you see:

```text
On the cart page the total does not change when I change the quantity (US-303 AC2).
Find why, fix it, and add a test that would have caught it.
```

**Ask one layer question per story** (this is where the learning happens): *"Show me the exact lines where this story reads from the database, and the security rule that allows it."*

### Prompt 4. Unit tests (10 min)

```text
Run ruff check . and python -m pytest tests/unit -q. If anything fails, tell me whether the test or the code is wrong
before you change anything. Never delete or weaken a test to make it pass.
```

You can run them yourself: `ruff check .` and `python -m pytest tests/unit -q`.

### Prompt 5. Quick manual check (10 min, you do it)

No generated test document. Use this checklist for each story, in the browser with the app running:

| # | Check |
|---|---|
| 1 | Do every acceptance criterion by hand. Tick it off |
| 2 | Try it signed out and as the wrong role. You must see "access denied" or a sign-in prompt |
| 3 | Try a bad input: empty, 0, 6 seats, very long text |
| 4 | Narrow the browser window (F12, then the phone icon). Nothing is cut off |
| 5 | Press Tab through the page. You can reach every button |
| 6 | Look in the Supabase dashboard (dev project). The row you expected is there |

Write failures down and fix them with a "what I saw" prompt.

### Prompt 6. Commit and push your branch (10 min)

```text
Show me git status and git diff --stat. Check that no .env, secrets.toml, keys or passwords are in my changes.
Then make one commit per story, adding files BY NAME (never git add -A), with messages like
"US-101: browse catalog page and list_courses". Push my branch with git push -u origin <branch>.
Do not push to main and do not open a pull request yet.
```

---

## 6. Going faster: two stories at once (optional)

Use only when the two stories edit **different** files (for example U1-03 and U1-04, or any two of User 3's stories). Not for U2-01, U2-02, U2-03, which build on each other, and not for two stories that both edit `courses.py` or `checkout.py`.

```text
Stories <pick A> and <pick B> touch different files. Build them in parallel with two sub-agents, one per story, using
the same instructions as the single-story build prompt. Each sub-agent may only edit its own story's files and must
not commit. When both finish, show me one table: story, files changed, tests, acceptance criteria met, open questions.
```

Teaching point to say out loud: *sub-agents are helpers with their own memory; if two helpers edit the same file they undo each other's work.* After they finish you review and test both, then commit by name (Prompt 6).

---

## 7. Session 2: Test, review, ship (2 hours)

| Time | Activity |
|---|---|
| 0:00 - 0:10 | Pull, run the app, finish any parked story |
| 0:10 - 0:35 | Swap-and-test: click through a teammate's pages (Section 7.1) |
| 0:35 - 1:05 | Open PRs, fresh-session review, fix, approve, merge (Sections 7.2 - 7.3) |
| 1:05 - 1:40 | Deploy (Section 8) |
| 1:40 - 2:00 | Smoke test the live site, recap, demo |

```powershell
git checkout user1-<theme>
git pull
git fetch origin
```

### 7.1 Swap-and-test (like a bug bash)

User 1 tests User 2's pages, User 2 tests User 3's, User 3 tests User 1's. Check out your teammate's branch, run the app, use the 6-point checklist from Prompt 5, and write bugs in a shared list (page, steps, expected, actual).

```powershell
git fetch
git checkout user2-<theme>
streamlit run app/streamlit_app.py
```

Owners fix their bugs with the "what I saw" prompt, commit, and push.

### 7.2 Pull request and fresh-session review

Author opens the PR (one per student):

```text
Open a pull request from my branch to main titled "<User N>: <stories done, e.g. US-101, US-201, US-102>".
Body: a 3-line summary, the acceptance criteria met per story, test results, and "Not done:" for anything parked.
Do not merge it.
```

**Reviewer: open a NEW terminal and a NEW Claude session** (not the one that wrote the code):

```powershell
gh pr checkout <PR number>
.\.venv\Scripts\Activate.ps1
claude --permission-mode plan
```

```text
You are an independent reviewer and did not write this code. Review PR <number> against the acceptance criteria
in docs/requirements/01-product-features-user-stories.md and CLAUDE.md. Do not edit anything. Check:
1) only the story files changed, 2) each acceptance criterion is met, with the file and line that proves it,
3) no keys or secrets, pages never call Supabase directly, roles checked, user text escaped,
4) tests would fail if the code were wrong, 5) the code is readable for beginners,
6) no fake timers, fake scarcity or random rewards.
Reply with: VERDICT (approve or changes requested), BLOCKERS, SHOULD FIX, and what you could not check.
```

The human reviewer also runs the app on that branch and repeats two acceptance criteria. Then on GitHub, approve or request changes, with `gh pr review <number> --approve` or `--request-changes --body "..."`.

### 7.3 Fix and merge

Author, in the original Claude session (`claude --continue`):

```text
The reviewer asked for these changes: <paste BLOCKERS and SHOULD FIX>. For each: say if you agree, fix it, run ruff and the tests.
```

Then commit, push. The Tech Lead merges (**Squash and merge**) one at a time. The nine stories do not depend on each other across students, so start with the PR that changes the fewest shared files (usually User 3, then User 1, then User 2). After each merge, the next author runs:

```text
Run git fetch and git rebase origin/main. If there are conflicts, show me the files and explain both sides before changing anything.
Then re-run ruff and the tests.
```

and pushes again with `git push --force-with-lease` (only your own branch).

**Check:** `main` runs the app with all nine stories, CI is green.

---

## 8. Deploy to Streamlit Community Cloud (35 min, Tech Lead drives, students take turns)

Vercel does not run Streamlit (it needs a long-running server). That is a good one-minute lesson.

| Step | Who | What |
|---|---|---|
| 1 | Lead | In a **new** Claude session ask: "Check that main has no .env or secrets (`git ls-files`), that requirements.txt is complete, and tell me anything that would break a deploy. Do not change files." |
| 2 | Student A | Streamlit Cloud: New app, repo `<org>/AITrainingEcommerce`, branch `main`, main file `app/streamlit_app.py` |
| 3 | Student B | Advanced settings, Secrets (trainer reads from the private note, **never type keys into Claude**): |

```toml
SUPABASE_URL = "https://<cloud-demo-project>.supabase.co"
SUPABASE_ANON_KEY = "<anon key only, never the service role key>"
```

| Step | Who | What |
|---|---|---|
| 4 | Everyone | Wait for the build log. If it fails, copy the last 20 lines into Claude: "Here is the Streamlit build log. What is wrong and what is the smallest fix?" Fix through a normal PR |
| 5 | Student C | Smoke test on the live URL: walk your product's main journey as the demo customer (for the store: browse, add to cart, place order, confirmation), then as staff or owner check the result appears, and confirm the customer cannot open admin pages |
| 6 | Lead | `git tag -a v1.0 -m "Demo v1.0"` then `git push origin v1.0` |

---

## 9. Recap (last 10 minutes)

Ask each student one question and answer it by showing the real file:

| Layer | Question |
|---|---|
| Idea and plan | Which document told us what to build? |
| Database | Which table holds the thing you built? What stops a customer reading admin data? |
| Service | Why does the page not talk to the database directly? |
| Page | Which part of your page is the user interface and which is logic? |
| Test | What would your test catch that clicking would miss, and the reverse? |
| Review | What did the fresh session find that the building session did not? |
| Deploy | What differs between your laptop and the live app? (Answer: only the secrets.) |

```text
Quiz me with 5 questions on how my stories fit the layers: page, service, database, test, review, deploy. Use my real files as examples.
Wait for my answer to each one before you tell me if I am right.
```

---

## 10. Troubleshooting (the six that will happen)

| Problem | Fix |
|---|---|
| "Missing SUPABASE_URL" | `.env` missing or empty. Copy it in |
| Streamlit skill prints `ERROR:` | Venv not active when `claude` started, or Streamlit older than 1.57. Activate venv, restart `claude` |
| Claude edits a file outside the story | `git restore <file>`, restate "only these files" |
| Tests pass on laptop, fail in CI | Missing package. Add to `requirements.txt` in your PR and tell the Lead |
| Rebase conflict | Ask Claude to explain both sides, choose, re-run tests |
| You committed a key | Tell the Lead **now**. The key must be replaced; deleting the file is not enough |

## 11. Cut list if time runs short

Drop in this order: swap-and-test (do a quick self-check), the optional "if finished early" stories, sub-agent parallel builds, the written PR body (one line is fine). Never drop: tests running, a person clicking through, the fresh-session review, and the secrets check.
