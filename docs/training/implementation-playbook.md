# Implementation Playbook: From Plan to Live App

This is the second playbook. The first one ([prompt-playbook.md](prompt-playbook.md)) took the idea to a plan on GitHub. This one takes the plan to **working, tested, reviewed, deployed code**, using Claude Code the same way a professional team would.

> **How to use this page:** work top to bottom. Copy a prompt, paste it into Claude Code, read the answer, run the check, then move on. Change words in `<angle brackets>`. Pick codes (U2-03), story IDs (US-402) and file names come from [work-division-plan.md](../planning/work-division-plan.md).

| Part | Who | What you get |
|---|---|---|
| 0 | Everyone | The big picture: 3 sessions, the story cycle, ground rules |
| 1 | Everyone | Skills review: what we have, what is missing |
| 2 | Tech Lead, once | Team toolkit installed (skills, agents, rules, safety settings) |
| 3 | Tech Lead | Foundation prompts (F1 - F21), tag `foundation-v1` |
| 4 | Users 1, 2, 3, once | Personal setup on your computer |
| 5 | Users 1, 2, 3 | **The story cycle**: build, unit test, manual test, push, review, merge |
| 6 | Users 1, 2, 3 | Several stories at the same time with sub-agents or worktrees |
| 7 | Everyone, then Lead | Integration, bug bash, deployment, release `v1.0` |
| 8 | Everyone | Cheat sheet and fixes for common problems |

---

## Part 0. The big picture

### 0.1 Three kinds of Claude Code session

The most important habit in this playbook: **the AI that wrote the code must not be the one that approves it.** A fresh session has no memory of the shortcuts and guesses made while building, so it sees the code the way a reviewer will.

| Session | Opened by | Purpose | Allowed to |
|---|---|---|---|
| **BUILD** | The story owner | Write code, unit tests, manual test plan for **one** story | Edit files, run tests, commit when you say so |
| **REVIEW** | A **new** terminal, ideally the reviewer | Check a PR against the acceptance criteria and rules | Read and run tests only. **Never edits.** Reports findings |
| **DEPLOY** | Tech Lead only | Release checks, deployment, smoke test, tag | Touches secrets and hosting settings, so nobody else uses it |

How to start a new session: open a new terminal tab, `cd` to the project, run `claude`. Do **not** reuse the BUILD terminal and just type `/clear`. Use a separate window so you can see that it is separate.

### 0.2 The story cycle (Part 5) in one picture

```
 BUILD session                                              REVIEW session (new)
 ┌─────────────────────────────────────────────────────┐   ┌───────────────────────────────┐
 │ 1 pick + branch                                     │   │ 9  AI review (read-only)      │
 │ 2 plan  →  you approve                              │   │ 10 human review: run the      │
 │ 3 build                                             │   │    branch, click through      │
 │ 4 unit tests + ruff                                 │   │ 11 approve or request changes │
 │ 5 manual test plan  →  YOU click through it         │   └──────────────┬────────────────┘
 │ 6 commit (by name) + rebase                         │                  │ changes requested
 │ 7 push + pull request   ──────────────────────────► │ ◄────────────────┘ back to BUILD (step 12)
 └─────────────────────────────────────────────────────┘
                                   approve → 13 squash merge → pull main → next story
```

### 0.3 Ground rules (they are in `CLAUDE.md` too)

| Rule | Why |
|---|---|
| One story per branch and per PR | Small PRs are reviewed faster and break less |
| Add files **by name**, never `git add -A` | That is how `.env` files get leaked |
| Never push to `main`; never merge your own PR | Branch protection plus peer review |
| Never paste keys into a prompt or an Issue | Claude sessions and GitHub history are not secret stores |
| Read the plan Claude shows you before saying "go" | You are the engineer, Claude is the assistant |
| If a test fails, find out whether the test or the code is wrong | Never delete a test just to get green |
| Ask Claude to explain anything you do not understand | This is a training project, not a race |

### 0.4 What must exist before Part 5

The repo today holds the plan, the requirements and 3 skills, but **no app code yet** (`app/` has only `.gitkeep` files, `requirements.txt` is empty). Users start stories only after the Lead finishes Parts 2 and 3 and tags `foundation-v1`. While you wait, do Part 4 and the "What participants do during Phase 1" tasks in plan section 2.6.

> **One change to the plan.** Plan section 1 says "one story in progress at a time". Part 6 adds an *optional* exception: up to 3 **independent** stories at once, each with its own branch, worktree, and PR. The Lead decides when a team is ready for it (suggested: after each person has merged their first story the normal way).

---

## Part 1. Skills review

### 1.1 What is installed

| Skill | Good for | Notes before you rely on it |
|---|---|---|
| `developing-with-streamlit` | Pages, layout, session state, caching, theming, custom components, deployment | Its helper script reads docs **from the installed Streamlit package (>= 1.57)**. Pin `streamlit>=1.57` in `requirements.txt` (foundation F13) and `pip install` it **before** using the skill, or it prints an `ERROR:` block. |
| `supabase-postgres-best-practices` | Tables, indexes, RLS, functions, migrations, locking | The name says "performance", but its description covers schema, migrations, RLS, and RLS tests. Use it for F8 - F12, L-01, and any `db/` story. It does **not** teach the Python client, Auth, or Storage. |
| `ui-ux-pro-max` | Colors, type, spacing, accessibility checks, UX rules | Written for general web and mobile stacks and has **no Streamlit stack**. Use `--domain ux`, `color`, `typography` searches, not `--stack`. **Our tokens in doc 02 section 3 win** over anything it suggests. Its `SKILL.md` shows the script path with `${CLAUDE_PLUGIN_ROOT}`, which may not be set for a project skill. If it fails, tell Claude to run `python .claude/skills/ui-ux-pro-max/scripts/search.py` from the project root (or `py -3` on Windows). |

**Safety habit (from the first playbook):** these skills run scripts. Before first use, ask Claude to read the skill folder and report any script that downloads, calls the internet, or deletes files.

### 1.2 What is missing

Existing skills teach *tools*. Nothing yet teaches *our team's way of working*, so each student would invent their own. Proposed additions (drafts are in [`proposed-skills/`](proposed-skills/)):

| New item | Type | What it does | Used in |
|---|---|---|---|
| `CLAUDE.md` | Project rules file | Architecture rules, commands, "never" list. Claude reads it every session | Everywhere |
| `implement-story` | Skill | Pick code → read story → check dependencies → plan → build only listed files → tests → report | Part 5 steps 2 - 4 |
| `write-tests` | Skill | pytest for services, Streamlit `AppTest` for pages, fake Supabase client, naming tests after AC | Part 5 step 4 |
| `manual-test-plan` | Skill | Turns acceptance criteria into a click-through checklist with negative, mobile, accessibility and ethics checks | Part 5 step 5 |
| `review-pr` | Skill | Read-only review checklist and report format | Part 5 steps 9 - 11 |
| `git-pr-workflow` | Skill | Branch names, commit by name, secret check, rebase, push, PR body | Part 5 steps 6 - 7, 13 |
| `deploy-streamlit-cloud` | Skill | Pre-deploy checklist, deploy, smoke test, rollback | Part 7 |
| `story-builder` | Sub-agent | Builds one story in its **own worktree**; does not commit | Part 6 |
| `pr-reviewer` | Sub-agent | Read-only reviewer with no edit tools | Part 5 step 9 |

Also worth knowing about, but not drafted: a general Supabase skill for Auth/Storage/client code (look in the same `supabase/agent-skills` repo), and a dedicated accessibility checker. The manual test plan and `review-pr` already cover the basics.

> **Training idea:** let students write one of these skills themselves with the `skill-creator` approach: "Draft a skill that does X, then test it on U1-03." Then compare with the draft.

---

## Part 2. Team toolkit setup (Tech Lead, once)

Do this on a branch `chore/team-toolkit` and open a small PR. Nobody starts stories before it is merged.

**2.1 Install the drafts**

```text
Install the team toolkit from docs/training/proposed-skills/:
- copy CLAUDE.md to the project root
- copy each skill folder (implement-story, write-tests, manual-test-plan, review-pr, git-pr-workflow, deploy-streamlit-cloud) into .claude/skills/
- copy agents/story-builder.md and agents/pr-reviewer.md into .claude/agents/
Then review every file you copied, tell me if any instruction is unsafe, unclear, or
conflicts with docs/planning/work-division-plan.md, and fix only what is wrong.
```

**2.2 Shared safety settings**

```text
Create .claude/settings.json (shared with the team) that:
- denies reading .env and .streamlit/secrets.toml
- denies git push --force and any push to main
- denies deleting files outside the project
Explain each rule in plain English. Then tell me how to confirm the rules are active.
```

Confirm with `/permissions` inside Claude Code. **Check:** the deny list shows the rules.

**2.3 Git housekeeping for parallel work (used in Part 6)**

```text
1. Add .claude/worktrees/ to .gitignore.
2. Create a .worktreeinclude file that lists .env and .streamlit/secrets.toml, so
   new worktrees get a copy of my local config files.
3. Create docs/testing/.gitkeep.
Do not touch any other file.
```

**2.4 Commit and PR**

```text
Use the git-pr-workflow skill. Branch chore/team-toolkit, add the new files by name,
run the secret check, commit, push, and open a PR to main titled
"Team toolkit: CLAUDE.md, skills, agents, settings". Show me the diff summary first.
```

**Check:** another person (any user) reviews and merges. Everyone runs `git pull`. Start a **new** Claude session and type `/skills` and `/agents` to see the new entries.

---

## Part 3. Foundation prompts (Tech Lead)

These cover plan items F1 - F21. Run each as its own BUILD session and PR (or direct commits to `main` while branch protection still lets admins bypass). Each prompt says which skill to use.

| Prompt | Plan items | Skills |
|---|---|---|
| 3.1 Repo process | F1 - F7 | `git-pr-workflow` |
| 3.2 Database | F8 - F9, F11 | `supabase-postgres-best-practices` |
| 3.3 Checkout function | F10 | `supabase-postgres-best-practices` |
| 3.4 Seed data | F12 | `supabase-postgres-best-practices` |
| 3.5 Config, client, auth | F13 - F15 | `developing-with-streamlit` |
| 3.6 App shell and page stubs | F16, F19 | `developing-with-streamlit`, `ui-ux-pro-max` |
| 3.7 Service and component stubs | F17 - F18 | `developing-with-streamlit` |
| 3.8 Tests and README | F20 - F21 | `write-tests` |

**3.1 Repo process (F1 - F7)**

```text
Using docs/planning/work-division-plan.md sections 2.1, 4, 7:
1. Create .github/ISSUE_TEMPLATE, .github/pull_request_template.md (use the checklist in plan 4.1),
   .github/CODEOWNERS (plan F5), CONTRIBUTING.md (the workflow in plan section 4),
   and .github/workflows/ci.yml running ruff check . and pytest on every pull request.
2. Create one GitHub Issue per story in plan section 3 with gh issue create: title starts with the
   pick code ("U2-03 US-402 Review and place order"), acceptance criteria copied from doc 01 as a
   checklist, labels (user:N, epic, type, priority, size), the Stories milestone, and a "Depends on" line.
   Show me the first 3 issues before creating all of them.
3. Write docs/architecture/decisions.md answering Q1 - Q6 from doc 00 section 8 using the defaults.
Do not turn on branch protection yet; list the exact settings so I can apply them in GitHub.
```

**Check:** CI file passes on a test PR; the board shows all Issues with pick codes. Turn on branch protection per plan F1 once the foundation is merged.

**3.2 Database (F8, F9, F11)**

```text
Use the supabase-postgres-best-practices skill. Write SQL migrations in supabase/migrations/
(numbered, one concern per file) for every table in docs/requirements/00-consolidated-requirements.md
section 6, with primary keys, foreign keys, foreign-key indexes, CHECK constraints
(seats_available >= 0, quantity 1 - 5), and the indexes in NFR-PERF-06.
Then a separate migration with RLS policies for guest, customer, staff, owner (NFR-SEC-05/06),
an audit_log table with a helper function (NFR-SEC-18), and the storage bucket policies for
course images (NFR-SEC-16). Explain each RLS policy in one sentence in a comment.
Do not run anything against a database yet.
```

**3.3 Checkout function (F10)**

```text
Use the supabase-postgres-best-practices skill. Write place_order(idempotency_key) as a Postgres
function in a new migration. In ONE transaction it must: read the signed-in user's cart, lock the
course rows, fail the whole order if any course lacks seats (return the course names and seats left),
deduct seats, create the order and order_items with a price snapshot, write the email_outbox row,
clear the cart, award XP and badges, and return the existing order if the same idempotency_key
is used twice. Cover US-403, US-601 to US-603 (server side), NFR-DATA-01 to 04.
Then write a short SQL test script in supabase/tests/ that proves: no oversell, no double order,
seats never negative.
```

**3.4 Seed data (F12)**

```text
Write supabase/seed/ files for: 4 categories, 12 - 16 fictional courses with levels, prices ($0 - $499),
seats and modules, 3 learning paths, the badges, and demo accounts (customer, staff, owner) plus
a few sample orders. Do not write real passwords into the repo: the demo account creation steps
go in docs/deployment/demo-accounts.md and passwords are shared privately.
```

**3.5 Config, client, auth (F13 - F15)**

```text
Use developing-with-streamlit. Pin Python 3.11+ and add streamlit>=1.57, supabase, pytest, ruff to requirements.txt.
Write app/config settings loading from st.secrets or environment variables with a clear fail-fast error
when SUPABASE_URL or SUPABASE_ANON_KEY is missing (NFR-SEC-11/12), basic logging in app/utils that never logs
personal data, app/services/supabase_client.py, and app/services/auth.py with sign_in, sign_out,
current_user, require_role (US-502, US-503, NFR-AUTH). Add a working app/pages/sign_in.py.
Tokens live only in st.session_state. Errors are generic ("Email or password is wrong").
```

**3.6 App shell and page stubs (F16, F19)**

```text
Use developing-with-streamlit and ui-ux-pro-max (design tokens from doc 02 section 3 win).
Create app/streamlit_app.py with role-based navigation (guest, customer, staff, owner), a header, and a
demo ribbon. Register EVERY page from the sitemap in doc 02 section 5.1 as a stub in app/pages/ that shows
"Coming soon - US-xxx" and calls the right access check. Add .streamlit/config.toml with the color tokens.
Stories must never need to edit streamlit_app.py after this.
```

**3.7 Service and component stubs (F17, F18)**

```text
Use developing-with-streamlit. For every story in plan section 3, create the service functions it needs in
app/services/ with a signature, type hints, a docstring (inputs, return shape, errors), and
raise NotImplementedError. Write docs/architecture/service-contracts.md listing all of them.
Then create working plain-Streamlit components in app/components/ with their FINAL signatures: course card,
seat meter, XP pill, XP bar, level chip, badge, path node map, empty / error / access-denied states.
Check the two lists against plan section 2.4 and tell me about any story whose function is missing.
```

**3.8 Tests and README (F20, F21)**

```text
Use the write-tests skill. Create tests/conftest.py with a fake Supabase client and sample data,
one example unit test, and one example AppTest page test. Add one integration test that calls place_order
against the TEST Supabase project and is skipped when no test keys are set. Then update README.md with exact
local setup steps for Windows (clone, venv, pip install, .env, run, test).
```

**Foundation exit** (plan 2.5): clean clone runs by README, every page opens, three demo roles work, `place_order` test passes, CI is green, Issues assigned. Then:

```text
Tag the current main as foundation-v1 and push the tag. Then write a 10-line summary of how a user
starts a story, for the walkthrough meeting.
```

---

## Part 4. Personal setup (Users 1, 2, 3, once)

PowerShell, from the folder where you keep projects:

```powershell
git clone https://github.com/<org>/AITrainingEcommerce.git
cd AITrainingEcommerce
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
copy .env.example .env              # then edit .env with the DEV anon key from the Lead (private channel)
streamlit run app/streamlit_app.py  # opens the app; Ctrl+C to stop
python -m pytest tests/unit -q
ruff check .
gh auth login --web                 # once
```

**Check:** the app opens, sign in works with the demo customer, pytest and ruff pass. Always **activate the venv before you start `claude`**, so Claude's commands use it.

First prompt in your first session (once):

```text
Read CLAUDE.md and docs/planning/work-division-plan.md. Then tell me in 8 lines or fewer:
what my pick-code list is (I am User <1|2|3>), which of my stories can start now,
and what I need before each of the others. Do not change any files.
```

---

## Part 5. The story cycle

Worked example used below: **User 2, story U2-03 (US-402 Review and place order)**. Replace the pick code, story ID and names with yours.

### Step 1. Pick the story and make the branch

Say it in stand-up: "User 2, starting U2-03". Move the Issue to **In progress**. In PowerShell:

```powershell
git checkout main
git pull
git checkout -b feature/U2-03-US-402-place-order
```

**Check:** `git branch --show-current` shows your feature branch, and `git status` is clean.

### Step 2. Open the BUILD session and ask for a plan

```powershell
.\.venv\Scripts\Activate.ps1
claude
```

```text
BUILD session for story U2-03 (US-402 Review and place order).
Use the implement-story skill.
Read: the U2-03 row in the work division plan, US-402 acceptance criteria in doc 01,
screen S7 in doc 02, and the orders.place_order contract in docs/architecture/service-contracts.md.
First give me a plan: files to change, functions to fill in, components to reuse, tests per
acceptance criterion, and anything unclear. Do NOT write code yet.
```

**Check the plan before you say "go":**

- Only the files listed for your story? (If it wants `streamlit_app.py` or `requirements.txt`, stop.)
- Every acceptance criterion (AC1 to AC4) appears?
- Pages call services only, not Supabase?
- Dependencies (U2-02) already merged? (`git log --oneline origin/main`)

### Step 3. Build, invoking the right skills

Skills load when the request matches their description. Say the skill name so there is no guessing:

| You are doing | Say |
|---|---|
| Streamlit page, widgets, session state, caching | "Use the developing-with-streamlit skill" |
| SQL, migration, RLS, database function | "Use the supabase-postgres-best-practices skill" |
| Layout, colors, spacing, accessibility | "Use the ui-ux-pro-max skill; tokens in doc 02 section 3 win; search with --domain ux" |
| Tests | "Use the write-tests skill" |

```text
Go. Build U2-03 following the plan.
- Use developing-with-streamlit for app/pages/checkout.py.
- Use ui-ux-pro-max for the order summary layout and the demo notice (doc 02 S7).
- Fill in orders.place_order by calling the database function; keep the stub's signature.
- Keep functions short and add a comment for every "why" that is not obvious.
Stop and ask me if you need to touch any file outside the plan.
```

Run the app yourself while Claude builds: `streamlit run app/streamlit_app.py`. Look at it. If something looks wrong, say what you see:

```text
On the checkout page the Place order button is still enabled before I tick the demo box (AC3).
Find why, fix it, and add a test that would have caught it.
```

### Step 4. Unit tests

```text
Use the write-tests skill. For U2-03 write unit tests, one group per acceptance criterion (AC1 to AC4),
with a happy path, an error path, and an edge case each. Use the fake Supabase client in tests/conftest.py.
Run ruff check . and python -m pytest tests/unit -q and show me the result.
```

You can run them yourself any time (venv active):

```powershell
ruff check .                                   # style and obvious bugs
python -m pytest tests/unit -q                 # all unit tests
python -m pytest tests/unit/test_orders.py -q  # one file
python -m pytest -k us402 -q                   # only tests with "us402" in the name
ruff check . --fix                             # let ruff fix simple things, then read the diff
```

If a test fails:

```text
The test test_us402_ac3_... failed. Before changing anything, tell me whether the test or the code is wrong,
and why. Then fix the right one. Do not delete or weaken the test.
```

Integration tests (checkout, no oversell, double submit) run **only against the test Supabase project**: `python -m pytest tests/integration -q`. Ask the Lead for the test keys; never run them on shared dev data.

**Check:** ruff is clean, all unit tests pass, and each AC has at least one test or is listed as "manual only".

### Step 5. Manual validation

Automated tests miss how it *feels*. Always click through your own story.

```text
Use the manual-test-plan skill for U2-03. Save it as docs/testing/U2-03-manual-test.md.
Cover every acceptance criterion, at least 2 negative cases, 1 mobile case, and the accessibility quick check.
```

Now **you** run the plan with the app open (`streamlit run app/streamlit_app.py`) and fill in Pass / Fail. What to cover on every story:

| Check | How |
|---|---|
| Each AC | Do the steps exactly; mark Pass / Fail |
| Roles | Try as guest, customer, staff, owner. Wrong roles must see "access denied" |
| Negative cases | Empty cart, double click, refresh mid-way, Back button, very long text, 0 and 6 seats |
| Mobile | In the browser press **F12**, then the device toolbar, choose a phone width about 390 px |
| Keyboard | Tab through the page. You can reach every button and see the focus outline |
| Ethics (gamification stories) | No fake timers, fake scarcity, random rewards, leaderboards, or penalty wording |
| Data | In the Supabase dashboard (dev project) check the order, order_items and seats really changed |
| Screenshots | **Win + Shift + S**, one desktop and one mobile, for the PR |

For each failure:

```text
Manual test case 4 failed: <what I did, what I expected, what happened>. Find the cause, fix it,
add a unit test if possible, and update the manual test file.
```

**Check:** the manual test file has no open Fail rows.

### Step 6. Commit (by name) and sync

```text
Use the git-pr-workflow skill. Show git status and git diff for my changes.
Check for secrets. Then stage ONLY these files by name: <list>, and commit as
"US-402: place order button and order summary". Do not push yet.
```

Then sync with main:

```text
Run git fetch and git rebase origin/main. If there are conflicts, show me the files, explain both sides,
propose the fix, and wait for me. After the rebase, re-run ruff and the unit tests.
```

**Check:** `git log --oneline -3` shows your commit on top of the latest `main`, and tests still pass.

### Step 7. Push and open the pull request

```text
Use the git-pr-workflow skill. Push the branch and open a PR to main titled
"U2-03 US-402 Review and place order". Body: "Closes #<issue number>", a 3-line summary,
which acceptance criteria are met, test results, a link to docs/testing/U2-03-manual-test.md,
and the PR checklist from plan section 4.1. Remind me to add screenshots (desktop and mobile).
```

Add the screenshots on github.com, move the Issue to **In review**, and say the pick code in the channel. Equivalent commands if you prefer to type them:

```powershell
git push -u origin feature/U2-03-US-402-place-order
gh pr create --base main --title "U2-03 US-402 Review and place order" --body-file pr-body.md
gh pr checks          # watch CI
```

**Check:** CI turns green. If it fails, read the log (`gh run view --log-failed`), fix in the BUILD session, commit, push.

### Steps 8 - 11. Review (a different session, and a different person)

Rotation (plan 4.3): User 1's PR is reviewed by User 2, User 2's by User 3, User 3's by User 1.

**Step 8. AI review in a NEW session (reviewer's computer)**

```powershell
git fetch
gh pr checkout <PR number>
.\.venv\Scripts\Activate.ps1
claude --permission-mode plan
```

(Plan mode means Claude can read and think but cannot edit. If your version does not accept the flag, press **Shift+Tab** until it shows plan mode.)

```text
REVIEW session. You did not write this code. Use the review-pr skill on PR <number>.
Check scope, every acceptance criterion of US-402, security and privacy, maintainability, and UI/ethics.
Report only: VERDICT, BLOCKERS, SHOULD FIX, NICE TO HAVE, AC RESULT, NOT CHECKED.
Do not edit any file.
```

**Step 9. Human review: run the branch**

The reviewer does not just trust the AI report:

1. `streamlit run app/streamlit_app.py` on the checked-out branch.
2. Open the author's `docs/testing/U2-03-manual-test.md` and repeat at least the AC cases and two negative cases.
3. Read the diff on GitHub yourself. Ask Claude to explain any part you do not follow: "Explain lines 40 - 80 of checkout.py like I am new to Streamlit."
4. Compare your findings with the AI report. Where they disagree, trust what you saw, and say so.

**Step 10. Leave the review**

```text
Turn my notes and the review report into a GitHub review: group by BLOCKER / SHOULD FIX / NICE TO HAVE,
each with file and line and one sentence of why. Show me the text first. Do not post it.
```

Post it yourself on GitHub, or:

```powershell
gh pr review <number> --approve --body "Checked AC1-AC4 locally. Manual test passed."
gh pr review <number> --request-changes --body-file review.md
```

**Step 11. Be a kind reviewer.** Comment on the code, not the person. Say what is good too. Review within half a day.

### Step 12. Fix review comments (back in the BUILD session)

Return to the author's terminal. If you closed it, type `claude --continue` (or `claude --resume` to pick a session).

```text
The reviewer asked for changes on PR <number>: <paste the BLOCKERS and SHOULD FIX>.
For each one: say if you agree, fix it, and add or update a test. One commit per fix, message
"US-402: address review - <what>". Re-run ruff, unit tests and the affected manual test cases.
```

Then `git fetch && git rebase origin/main`, push (`git push --force-with-lease` is needed after a rebase on your own feature branch), and re-request review. A fresh REVIEW session checks the fixes.

### Step 13. Merge, clean up, next story

When CI is green, you have one approval, and the branch is up to date: **Squash and merge** on GitHub (author or Lead).

```powershell
git checkout main
git pull
git branch -d feature/U2-03-US-402-place-order
```

Close the Issue (the `Closes #` does it), move it to **Done**, tick the story in your list, and go back to Step 1 for the next one. If the next story is blocked, skip to the next unblocked story on **your own** list.

---

## Part 6. Several stories at once: sub-agents and worktrees

### 6.1 When this is allowed

| Rule | Detail |
|---|---|
| Independent stories only | Different page files, no "Depends on" between them |
| Same file means in order | Two stories that edit the same file (for example `courses.py`) are **never** parallel |
| Maximum 3 | More than 3 is hard to review and slower overall |
| Separate everything | Own branch, own worktree, own tests, own manual test, own PR |
| Reviews do not change | Each PR still gets its own REVIEW session and human review |
| Lead says yes | Try it only after you have merged one story the normal way |

### 6.2 Which stories are safe together?

Ask Claude to compute it from the plan so you learn how:

```text
Read section 3 of docs/planning/work-division-plan.md. For User <N>, look at the stories that are not yet
Done and whose "Depends on" stories are merged. Group them into sets of at most 3 that touch DIFFERENT
page files and different service functions. Show a table: set, pick codes, files, and any shared file
(services/*.py, components/*.py) that could cause a merge conflict. Recommend the best first set.
```

Starting suggestions from the plan's file columns (Claude should confirm them):

| User | First parallel set | Why it is safe | Keep in order (same file) |
|---|---|---|---|
| 1 | U1-03 (`courses.py`), U1-04 (`course_detail.py`), U1-14 (`learning_paths.py`) | Three different pages | U1-05 to U1-08 all edit `courses.py`; U1-10 to U1-12 all edit `course_detail.py` |
| 2 | U2-01 (`cart` service), U2-04 (`checkout.py`), U2-15 (`my_orders.py`) | Different pages and services | U2-03, U2-04, U2-07 all edit `checkout.py`. Do U2-01 first for U1-15 |
| 3 | U3-01 (`admin_courses.py`), U3-04 (`passport.py`), U3-05 (`register.py`) | Different pages | U3-05 and U3-15 both change `auth.py`; U3-06 to U3-08 edit `admin_courses.py` |

The shared services (`catalog.py`, `admin.py`) hold several stories' functions. Because each story fills a different stub, Git usually merges them, but merge in order and rebase (6.6).

### 6.3 One-time setup (done in Part 2.3)

`.claude/worktrees/` is git-ignored and `.worktreeinclude` lists `.env` and `.streamlit/secrets.toml`, so each worktree gets your local config. A worktree is a second folder with its own branch that shares the same Git history. Start Claude **from the main project folder with the venv active** so every worktree reuses it.

### 6.4 Method A: sub-agents inside one session

One "boss" session starts one `story-builder` sub-agent per story. Each sub-agent works in its own worktree (the agent file says `isolation: worktree`). They cannot start other sub-agents, so the boss session does all the starting.

```text
I want to build these 3 independent stories in parallel: U2-01, U2-04, U2-15.
Use the story-builder sub-agent once per story, each in its own worktree, all running at the same time.
Give each one: its pick code, the plan row, its acceptance criteria, and the rule to touch only its listed files.
They must NOT commit or push. When they finish, give me one table: pick code, branch, worktree path,
files changed, AC covered, test result, open questions.
```

What happens next is on you, **for each worktree** (path comes from the table):

```powershell
cd .claude\worktrees\<name>
git branch --show-current                      # should be feature/<pick>-...; rename with git branch -m if not
streamlit run app/streamlit_app.py --server.port 8502   # use 8502, 8503 ... so ports do not clash
python -m pytest tests/unit -q
ruff check .
```

Then run Part 5 steps 5 to 7 in that worktree (manual test, commit by name, push, PR). Open a **new Claude session inside the worktree folder** for the manual test plan and PR work, so each story has its own clean context.

### 6.5 Method B: separate terminals, one per story (best the first time)

Same idea, but you can watch each session. Three terminal tabs:

```powershell
# tab 1, from the main project folder, venv active
claude --worktree U2-01-US-301-cart-add
# tab 2
claude --worktree U2-04-US-401-signin-gate
# tab 3
claude --worktree U2-15-US-407-order-history
```

In each tab, use the normal Step 2 prompt for that pick code (BUILD session). Inside a worktree session, first run `git branch -m feature/<pick>-<story>-<short-name>` if the branch has an automatic name.

If your Claude Code version has no `--worktree` flag, make worktrees by hand and start `claude` inside each:

```powershell
git fetch origin
git worktree add ..\wt-U2-04 -b feature/U2-04-US-401-signin-gate origin/main
copy .env ..\wt-U2-04\.env
cd ..\wt-U2-04
claude
```

### 6.6 Merging parallel PRs

1. Open one PR per story as usual (Part 5 step 7).
2. Review and merge **one at a time**: smallest or most shared first (cart service before pages that call it).
3. After each merge, every other worktree runs:

```text
Run git fetch and git rebase origin/main in this branch. If there are conflicts, show me the files and explain
both sides before changing anything. After the rebase, re-run ruff and the unit tests and tell me the result.
```

4. Force-push only your own branch, with `git push --force-with-lease`.

### 6.7 Clean up

```powershell
git worktree list
git worktree remove .claude\worktrees\<name>     # after the PR is merged
git branch -d feature/<pick>-...
git worktree prune
```

### 6.8 Mistakes to avoid

| Mistake | What goes wrong | Do this instead |
|---|---|---|
| Two stories editing `checkout.py` | Conflicts and lost work | Same file: one after the other |
| One PR with three stories | Cannot be reviewed or reverted | Three PRs |
| Sub-agents committing for you | You never read the diff | You review, then you commit |
| Skipping the manual test "because it is parallel" | Bugs go to the reviewer | Manual test each worktree |
| 5 stories at once | Nobody can keep up | Maximum 3 |
| Same session reviews what it built | Misses its own mistakes | New REVIEW session each time |

---

## Part 7. Integration, bug bash, deployment, release

### 7.1 Smoke test and bug bash (Phase 3)

Start when all **Must** stories are Done. Pull `main` and use a **new** session for each task.

```text
Use the manual-test-plan skill to write docs/testing/e2e-smoke-test.md for the full journey:
find a course, add to cart, sign in, checkout, seats go down, confirmation, My Orders, staff sees the order.
Add role checks (customer cannot open admin pages) and a mobile pass.
```

Bug bash: test an area you did **not** build (plan section 5). Log each bug as an Issue with label `type:bug`, steps, expected, actual, and a screenshot. The area's owner fixes it with the normal cycle (Part 5), one bug per PR.

```text
Draft a bug Issue from these notes: <what I did, what I expected, what happened>. Use the Issue template.
Do not create it until I approve the text.
```

### 7.2 Whole-repo review (Lead, REVIEW session)

```text
REVIEW session. Use the review-pr skill on the whole repository against docs/requirements/03-non-functional-requirements.md.
Focus on NFR-SEC and NFR-PRIV. Search the entire git history for keys, .env files, and anything that
looks like a secret. Report only. Do not edit.
```

Run the RLS break test (story L-01) with every role. If your Claude Code version has `/security-review`, run it as well and treat its output as advice, not proof.

### 7.3 Deployment (Lead, DEPLOY session)

Open a **new** terminal and a new `claude` session used only for this.

```text
DEPLOY session. Use the deploy-streamlit-cloud skill. Run the pre-deploy checklist against a clean clone
of main and show me every item as pass / fail with the evidence. Do not deploy yet.
```

Then, in the browser, follow the skill: create the Supabase **cloud demo** project, apply migrations and seed, disable email confirmation for the demo, deploy from `main` on Streamlit Community Cloud with `app/streamlit_app.py` as the main file, and paste the secrets in the app settings. **Never paste keys into Claude.**

```text
The deploy finished. Here is the live URL: <url>. Write the smoke test steps as a table I can follow
and tell me what to check in the Streamlit logs if any step fails. Then draft docs/deployment/README.md
(steps used, Supabase project name without keys, how to reset demo data, known limits).
```

Vercel does not run Streamlit (it needs a long-running server), which makes a good short lesson (NFR-DEP-03).

### 7.4 Release `v1.0`

```text
Use the git-pr-workflow skill. After the deployment docs are merged, create an annotated tag v1.0 on main,
push it, and draft GitHub release notes listing shipped stories by epic, known limits, and the live URL.
Show me the notes before creating the release.
```

```powershell
git checkout main; git pull
git tag -a v1.0 -m "SkillForge Academy demo v1.0"
git push origin v1.0
gh release create v1.0 --notes-file release-notes.md
```

Each user then writes the demo script for their area (`docs/demo-script.md`): what to click, what to say.

---

## Part 8. Cheat sheet and fixes

### 8.1 Daily commands

| Task | Command |
|---|---|
| Start work | `git checkout main; git pull; git checkout -b feature/<pick>-<story>-<name>` |
| Activate venv | `.\.venv\Scripts\Activate.ps1` |
| Run app | `streamlit run app/streamlit_app.py` |
| Lint | `ruff check .` |
| Unit tests | `python -m pytest tests/unit -q` |
| Integration tests | `python -m pytest tests/integration -q` (test project only) |
| What changed | `git status`, `git diff` |
| Stage by name | `git add path\to\file.py` |
| Sync | `git fetch; git rebase origin/main` |
| Push | `git push -u origin <branch>` |
| Open PR | `gh pr create --base main --title "<pick> <US-id> <title>"` |
| CI status | `gh pr checks` |
| Check out a PR to review | `gh pr checkout <number>` |
| List skills / agents | `/skills`, `/agents` inside Claude Code |

### 8.2 Prompt patterns that work

| Pattern | Example |
|---|---|
| Name the story and the skill | "BUILD session for U2-03. Use implement-story." |
| Plan first, code second | "Give me a plan. Do NOT write code yet." |
| Limit the files | "Touch only the files in the plan. Ask if you need another." |
| Ask for evidence | "Show the test output" and "Which line proves AC3?" |
| Ask why | "Explain this function like I am new to Streamlit." |
| Say what you saw | "On mobile the button is cut off at 390 px wide." |
| Fix, then guard | "Fix it and add a test that would have caught it." |

### 8.3 Common problems

| Problem | Likely cause | Fix |
|---|---|---|
| Skill says `ERROR:` for Streamlit | Streamlit not installed in the active venv, or older than 1.57 | Activate venv, `pip install -r requirements.txt`, restart `claude` |
| ui-ux-pro-max script not found | `${CLAUDE_PLUGIN_ROOT}` is not set | Ask Claude to run `python .claude/skills/ui-ux-pro-max/scripts/search.py` from the project root |
| "Missing SUPABASE_URL" at start | `.env` missing (new clone or new worktree) | Copy `.env` in; check `.worktreeinclude` |
| Claude edits a file outside the story | The plan was not checked | `git restore <file>`, re-state the allowed files, ask again |
| Tests pass locally, fail in CI | Different Python version or missing dependency | Match the pinned version; add the package to `requirements.txt` in your PR (Lead reviews) |
| Rebase conflict | Someone merged a nearby change | Ask Claude to explain both sides; choose; re-run tests |
| `git push` rejected after rebase | History changed on your own branch | `git push --force-with-lease` (your branch only, never `main`) |
| Port already in use | Another Streamlit is running | Add `--server.port 8502` |
| PR blocked "branch not up to date" | `main` moved | `git fetch; git rebase origin/main; git push --force-with-lease` |
| You committed a key | Skipped `git status` | Tell the Lead **now**. The key must be rotated; deleting the file is not enough |
| Reviewer session changed files | It was not read-only | `git restore .`, restart with `--permission-mode plan` |
| Need a DB change in a story | Schema is missing something | New migration file in your PR, label `schema-change`, Lead reviews. Never edit a merged migration |

### 8.4 End-of-story checklist

- [ ] Branch name has the pick code; one story only
- [ ] Plan was read and approved before coding
- [ ] `ruff check .` clean; unit tests pass; each AC covered
- [ ] Manual test file complete, no open Fail rows; screenshots (desktop + mobile)
- [ ] `git status` showed no `.env` or secrets; files added by name
- [ ] PR title `U2-03 US-402 ...`, body has `Closes #`, CI green
- [ ] Reviewed in a **new** session and by another **person**
- [ ] Squash merged, local branch deleted, Issue Done
