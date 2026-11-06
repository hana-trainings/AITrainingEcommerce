# Prompt Playbook: From Idea to GitHub

These are the prompts used so far to build this project with **Claude Code**, cleaned up so you can repeat each step yourself. Run them in order, inside the project folder, in Claude Code (VS Code extension or terminal).

> **How to use this page:** copy a prompt, paste it into Claude Code, read what Claude produces, and check the result before moving to the next step. Change the words in `<angle brackets>` to fit your own project.

| Step | What you get | Output |
|---|---|---|
| 0 | Tools installed | Your computer |
| 1 | Empty project skeleton | Folders, README, `.gitignore` |
| 2 | Features and user stories | `docs/requirements/01-...md` |
| 3 | UI / UX requirements | `docs/requirements/02-...md` |
| 4 | Non-functional requirements | `docs/requirements/03-...md` |
| 5 | One-page consolidated summary | `docs/requirements/00-...md` |
| 6 | Team work plan (story mapping) | `docs/planning/work-division-plan.md` |
| 7 | Agent skills installed | `.claude/skills/` |
| 8 | Code on GitHub | GitHub repo |
| 9 | GitHub labels and milestones | GitHub repo settings |

---

## Step 0. Install the tools (once)

| Tool | Why | Check it works |
|---|---|---|
| VS Code + Claude Code extension | Where you type the prompts | Claude panel opens in VS Code |
| Python 3.11+ | Runs the Streamlit app | `python --version` |
| Node.js (LTS) | Needed for `npx skills add` | `node --version` |
| Git | Version control | `git --version` |
| GitHub CLI | Create the repo from the terminal | `gh --version` |
| A GitHub account | Where the code lives | You can sign in at github.com |

Create an empty folder (for example `C:\Projects\AITrainingEcommerce`) and open it in VS Code.

---

## Step 1. Project skeleton

```text
Create a project skeleton for a demo e-commerce web app for training purposes.
Stack: Streamlit for the UI and Supabase for the database, sign-in and file storage.
It should also be usable as an example for deploying to Streamlit Community Cloud.

Create only folders and starter files, no application code yet:
- app/ with pages, components, services, models, utils, config
- assets/ (images, styles), docs/ (requirements, architecture, deployment, planning)
- supabase/ (migrations, seed), tests/ (unit, integration), scripts/, .streamlit/
- README.md explaining the folder structure
- .gitignore that blocks .env and .streamlit/secrets.toml
- .env.example and .streamlit/secrets.toml.example with empty Supabase values
Keep empty folders with a .gitkeep file.
```

**Check:** no real keys anywhere. Only `.example` files.

---

## Step 2. Product features and user stories

```text
Write docs/requirements/01-product-features-user-stories.md for this app.

The store sells fictional AI and Data training courses. It is a demo:
no real payments and no real emails.

Roles: guest, customer, staff, owner.

Features (one epic each):
E1 Product search and catalog
E2 Product detail
E3 Add to cart
E4 Checkout and order confirmation (confirmation email saved to an outbox, not sent)
E5 Customer register / sign in
E6 Gamification (XP, levels, badges, learning-path skill tree), ethical, no pressure tactics
E7 Owner and staff product management

For each epic write user stories with IDs (US-101, US-102 ...), a priority
(Must / Should / Could), and numbered acceptance criteria (AC1, AC2 ...).
Also include: key domain terms, seed data for demos, and an out-of-scope list.
Use simple, clear English.
```

**Check:** every story has an ID, a priority, and testable acceptance criteria.

---

## Step 3. UI / UX requirements

```text
Write docs/requirements/02-ui-ux-requirements.md for a UI/UX designer.

Vision: "Professional, yet gamified. It should create curiosity to buy the course."

Include:
1. What each word of the vision means for the design, and what it does NOT mean
2. Design principles
3. Visual direction: mood, suggested color tokens, typography, icons
4. How gamification appears in the UI (ethical: no fake timers or fake scarcity)
5. Sitemap and navigation
6. Key user flows
7. Screen-by-screen requirements (S1 Home ... S16 system states)
8. Accessibility and mobile
9. Content and tone
10. What is and isn't possible in Streamlit, so designs can be built
11. A list of deliverables the designer must hand over
Link each screen to the user stories in doc 01.
```

---

## Step 4. Non-functional requirements

```text
Write docs/requirements/03-non-functional-requirements.md.

It is a classroom demo, so keep targets small, but use real security practices
so learners see how it should be done.

Sections: authentication, security (including Supabase Row Level Security and
never committing keys), privacy and child safety, data integrity (no overselling
seats, no double orders), performance, usability and accessibility, reliability
and error handling, maintainability and code quality, logging, deployment and
environments, scalability limits, constraints and assumptions.

Give each requirement an ID (NFR-SEC-01 ...) and a priority (Must / Should / Could).
```

---

## Step 5. Consolidated summary

```text
Read docs/requirements/01, 02 and 03 and write
docs/requirements/00-consolidated-requirements.md as the one-page starting point:
goals, users and roles, feature summary, UI/UX summary, non-functional summary,
logical data model (tables and key fields), scope, open questions with a default
answer for each, suggested build order, and a traceability table linking
features → stories → screens → NFRs.
Also add docs/requirements/README.md listing the four documents.
```

**Check:** read the open questions. Decide the answers as a class.

---

## Step 6. Team work plan (story mapping)

This was done in three rounds. Each round improved the plan. Running all three shows students how to give Claude feedback.

### 6a. First version

```text
Using the documents in docs/requirements, create docs/planning/work-division-plan.md
for a team of 6 working together on GitHub. Split the work by feature area,
assign every story to a member with a reviewer, give a sprint plan, file ownership
rules to avoid merge conflicts, the GitHub workflow (issues, branches, PRs,
definition of done), meetings and risks.
```

### 6b. Remove the dependencies: foundation first, then stories

```text
Update the plan. Right now there are too many dependencies between members.
Reorganize it so that:
1. The Tech Lead builds the foundation first (repo setup, CI, database schema,
   security rules, seed data, sign-in, app shell with every page as a stub,
   service function stubs, shared components, test setup) and pushes it to GitHub.
2. After that, participants split the stories and work on one story at a time:
   branch, build, test, pull request, review, merge, then the next story.
3. At the end, everything is merged, tested and released.
For each story show the files it touches, what it depends on, and its size.
```

### 6c. Give each participant their own list

```text
Organize the stories by User 1, User 2 and User 3 so each participant can
name their stories directly. Give every story a pick code (for example U2-03),
keep each user's list in a working order, balance the workload, keep most
dependencies inside the same user's list, and show the few cross-user
dependencies separately.
```

**Check:** in the final plan, each user's first story has no dependencies, so everyone can start on day one.

---

## Step 7. Install agent skills

Skills give Claude Code expert guidance for a specific tool. Run these in the VS Code terminal from the project folder (or paste them into Claude Code and ask it to run them).

```bash
# Streamlit: building, styling, caching, deploying Streamlit apps
npx skills add https://github.com/streamlit/agent-skills --skill developing-with-streamlit

# Supabase / Postgres: schema, migrations, Row Level Security, indexes, functions
npx skills add https://github.com/supabase/agent-skills --skill supabase-postgres-best-practices

# UI/UX: styles, palettes, fonts, accessibility, design systems
npx skills add https://github.com/nextlevelbuilder/ui-ux-pro-max-skill --skill ui-ux-pro-max
```

Skills install into `.claude/skills/` and are recorded in `skills-lock.json`. Start a new Claude Code session so it picks them up.

> **Safety habit:** skills run with full agent permissions. Before using one, ask Claude: *"Review the skill files in .claude/skills/<name> and tell me if any script downloads files, calls the internet, or deletes anything."*

---

## Step 8. Publish to GitHub

```text
Push the current code to GitHub as a new public repository named
AITrainingEcommerce. Make sure no .env or secrets file is committed.
```

What Claude does (you can also type these yourself):

```bash
git init -b main
git add -A
git status            # check: no .env, no secrets.toml
git commit -m "Initial project skeleton, requirements, and work division plan"

gh auth login --web   # opens github.com/login/device; enter the one-time code shown
gh repo create AITrainingEcommerce --public --source . --remote origin --push
```

**Check:** open the repo on github.com and confirm the docs are there.

---

## Step 9. GitHub labels and milestones

```text
Set up the GitHub repo to match section 7 of the work division plan:
create the labels (user:1/2/3/lead, epic:E1-E7, type, priority, size,
schema-change, blocked) and the milestones Foundation, Stories, Release v1.0.
```

---

## What's next

| Next step | Prompt idea |
|---|---|
| Create story Issues | *"Create one GitHub Issue per story in the work division plan, with the pick code in the title, acceptance criteria as a checklist, labels, milestone and Depends on."* |
| Protect `main` | *"Protect main: require a pull request with 1 approval; let admins bypass during the foundation phase."* |
| Start the foundation | *"Start foundation item F8: write the Supabase migrations for all tables in doc 00 section 6."* |

## Tips for writing good prompts

- **Say the goal and the output file.** "Write docs/requirements/03-...md" is better than "write some NFRs".
- **Give the context.** Mention it's a demo, the stack, and who will read the document.
- **Ask for IDs and priorities.** They make stories easy to trace and plan.
- **Review, then correct.** Step 6 shows this: the first plan was fine, and two short feedback prompts made it much better.
- **Never paste keys or passwords into a prompt.** Use `.env` files that are never committed.
