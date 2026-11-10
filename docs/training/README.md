# Start Here: How to Read and Use the Training Files

There are several files in this folder. This page tells you **which to read, in what order, and which to copy where**. Read it first (5 minutes).

## 1. The files in one table

| File | What it is | Use it for the 4-hour class? |
|---|---|---|
| `README.md` (this page) | Reading order and file placement | Yes, read first |
| [prompt-playbook.md](prompt-playbook.md) | **Playbook 1.** Idea to plan on GitHub: requirements, plan, skills, first push | Yes, already done by each team. Step 7 (install skills) is needed again in every team repo |
| [fast-track-playbook.md](fast-track-playbook.md) | **The classroom playbook.** Pre-class foundation, Session 1 (build), Session 2 (test, review, deploy) | **Yes. This is the main file** |
| [fast-track-CLAUDE.md](fast-track-CLAUDE.md) | Rules file for Claude Code. Becomes `CLAUDE.md` in the repo root | **Yes. Must be copied** |
| [implementation-playbook.md](implementation-playbook.md) | Full, detailed version (worktrees, review skills, story-by-story PRs) | No. Reference for a longer course |
| [proposed-skills/](proposed-skills/) | Draft extra skills and sub-agents used only by the full version | No. Skip for 4 hours |

**Which one do I follow?**

```
Class is 2 sessions x 2 hours (4 hours total)  ->  fast-track-playbook.md
Course runs for weeks                           ->  implementation-playbook.md (+ proposed-skills/)
```

## 2. Reading order

### Everyone (about 35 minutes, do this before anything else)

| Order | Read | Time | What to understand before moving on |
|---|---|---|---|
| 1 | This page | 5 min | Which files matter and where they go |
| 2 | Your team's own `docs/planning/work-division-plan.md`, sections 1 and 3 | 10 min | The approach (foundation first, then stories) and **your** story list |
| 3 | `fast-track-playbook.md`, Sections 1 and 2 | 10 min | Why the class is built this way, and the AIDLC map |
| 4 | `fast-track-playbook.md`, the section for your role (table below) | 10 min | Exactly what you do and when |

### Then, by role

| Role | Read next | When |
|---|---|---|
| **Trainer** | `fast-track-playbook.md` start to finish; skim `implementation-playbook.md` Part 3 | A week before class |
| **Tech Lead** | `fast-track-playbook.md` Section 3 (pre-class foundation: accounts, Prompts A to F, ready check), then Sections 7.3 and 8 (merge and deploy) | As soon as the team starts |
| **Users 1, 2, 3** | Section 3.1 and 3.2 (setup and reviewing the Lead's PRs), Section 4 (your stories), Section 5 (Session 1), Section 7 (Session 2) | Setup now; Sections 5 and 7 the day before each session |

### How to read a playbook page

- **Tables** say who does what and when. Read them first.
- **Code blocks marked `text`** are prompts. Copy them into Claude Code and change the words in `<angle brackets>`.
- **Code blocks marked `powershell`** are commands you type in the terminal.
- **"Check:" lines** tell you how to know the step worked. Do not skip them.
- Text in **bold** inside a step is a rule that matters (for example: never commit keys).

## 3. Which files to move where

Each team has its own product and its own repo. The training files live in the trainer's template folder (`C:\Projects\AITrainingEcommerce`). Copy these into **every team repo**. Do it once, on a branch, and merge it with a small pull request.

### 3.1 Required (4-hour class)

| Copy this | From (trainer folder) | To (team repo) | Then |
|---|---|---|---|
| Classroom playbook | `docs\training\fast-track-playbook.md` | `docs\training\fast-track-playbook.md` | Nothing |
| Rules file | `docs\training\fast-track-CLAUDE.md` | **`CLAUDE.md`** in the repo root (new name) | Replace the first line with one sentence about your product |
| This reading guide | `docs\training\README.md` | `docs\training\README.md` | Nothing |
| Playbook 1 (for the skill install step) | `docs\training\prompt-playbook.md` | `docs\training\prompt-playbook.md` | Optional, for reference |
| The 3 skills | `.claude\skills\` (3 folders) and `skills-lock.json` | Same paths in the team repo | See below; this step is **required** |

**The 3 skills** are `developing-with-streamlit`, `supabase-postgres-best-practices` and `ui-ux-pro-max`. Choose one way:

```powershell
# Way 1 (recommended): install them fresh, from the team repo folder
npx skills add https://github.com/streamlit/agent-skills --skill developing-with-streamlit
npx skills add https://github.com/supabase/agent-skills --skill supabase-postgres-best-practices
npx skills add https://github.com/nextlevelbuilder/ui-ux-pro-max-skill --skill ui-ux-pro-max

# Way 2: copy the folders from the trainer folder
xcopy /E /I C:\Projects\AITrainingEcommerce\.claude\skills <team repo>\.claude\skills
copy C:\Projects\AITrainingEcommerce\skills-lock.json <team repo>\skills-lock.json
```

Before first use, ask Claude to check the skill scripts (safety habit from Playbook 1, Step 7).

Copy commands for the files (from the trainer folder):

```powershell
$T = "C:\Projects\AITrainingEcommerce"
$R = "<path to team repo>"
mkdir "$R\docs\training" -Force
copy "$T\docs\training\README.md"               "$R\docs\training\"
copy "$T\docs\training\fast-track-playbook.md"  "$R\docs\training\"
copy "$T\docs\training\prompt-playbook.md"     "$R\docs\training\"
copy "$T\docs\training\fast-track-CLAUDE.md"    "$R\docs\training\"
copy "$T\docs\training\fast-track-CLAUDE.md"    "$R\CLAUDE.md"
```

Then, in the team repo, add by name (never `git add -A`) and open a PR:

```powershell
git checkout -b chore/training-files
git add CLAUDE.md docs/training skills-lock.json .claude/skills
git status          # check: no .env, no keys
git commit -m "Add training playbooks, CLAUDE.md and skills"
git push -u origin chore/training-files
gh pr create --base main --title "Add training playbooks, CLAUDE.md and skills" --body "Training files for the 4-hour class."
```

### 3.2 Do not copy for the 4-hour class

| Leave in the trainer folder | Why |
|---|---|
| `docs\training\implementation-playbook.md` | Full version; too much for 4 hours. Share only with teams running a longer course |
| `docs\training\proposed-skills\` (all of it) | Extra skills and sub-agents for the full version. Not needed in class |
| This product's `docs\requirements\`, `docs\planning\` | These belong to the AI Training E-commerce example. Each team has its own |

### 3.3 Only if you run the full version later

| Copy this | To |
|---|---|
| `proposed-skills\CLAUDE.md` | repo root `CLAUDE.md` (**instead of** the fast-track one) |
| `proposed-skills\<skill-name>\` folders (6) | `.claude\skills\` |
| `proposed-skills\agents\*.md` | `.claude\agents\` |

Details are in `implementation-playbook.md`, Part 2.

### 3.4 What a team repo looks like when it is ready

```
<team repo>/
├── CLAUDE.md                          <- from fast-track-CLAUDE.md, product line edited
├── skills-lock.json
├── .claude/skills/
│   ├── developing-with-streamlit/
│   ├── supabase-postgres-best-practices/
│   └── ui-ux-pro-max/
├── docs/
│   ├── requirements/                  <- the team's own docs from Playbook 1
│   ├── planning/work-division-plan.md <- the team's own plan
│   └── training/
│       ├── README.md
│       ├── fast-track-playbook.md
│       └── prompt-playbook.md
└── (app/, supabase/, tests/ ... created in the pre-class foundation)
```

## 4. Check you understood (before you start)

Answer these without looking. If you cannot, re-read the section named.

1. How many sessions are there and what does each one do? (`fast-track-playbook.md` Sections 5 and 7)
2. What must be finished **before** Session 1, and who does it? (Section 3)
3. Which stories are mine, and why can I start them without waiting for a teammate? (Section 4)
4. Why does the code that Claude wrote get reviewed by a **different** session? (Section 7.2)
5. What are the four things we never skip, even when rushed? (Section 11)
6. Which file becomes `CLAUDE.md`, and what do I edit in it? (Section 3.1 above)

Or let Claude check you. Open Claude Code in your team repo and paste:

```text
Read docs/training/README.md and docs/training/fast-track-playbook.md. Do not change any files.
First, explain in 8 lines or fewer what my team does before Session 1, in Session 1, and in Session 2.
Then ask me the 6 questions in README section 4, one at a time, wait for my answer, and tell me if I am right.
```

## 5. Trainer checklist (one page)

- [ ] Every team repo has `CLAUDE.md` (product line edited), the 3 skills, and `docs/training/` with the 3 files above
- [ ] Every student has read this page and passed the Section 4 check
- [ ] Each team has finished the pre-class foundation and passed the ready check (`fast-track-playbook.md` Section 3.4)
- [ ] You have signed off each team 24 hours before Session 1 (Section 3.5)
