---
name: review-pr
description: Use in a NEW, read-only session to review a pull request or branch against the story's acceptance criteria, the NFRs, and the team rules. Reports findings, never edits code.
---

# Review a PR (read-only)

Input: a PR number (`gh pr view <n>`) or a branch name.

## Rules for the reviewer
- You did not write this code. Do not edit, fix, commit, or push. Report only.
- Judge against the documents, not against your taste.

## Steps
1. Read the PR description and the Issue it closes. Get the diff: `gh pr diff <n>` and `gh pr view <n> --json files`.
2. Read the story's acceptance criteria (doc 01) and the plan row (files, depends on).
3. Run the checks below. Run `ruff check .` and `python -m pytest tests/unit -q` if you can.
4. Write the report in the format at the end.

## Checklist
**A. Scope and process**
- Exactly one story. Pick code in the title. Only the story's files changed (extra files explained).
- No change to a merged migration, service signature, component signature, `app/streamlit_app.py`, or `requirements.txt` unless explained and Lead-approved.
- Branch is up to date with `main`; commit messages carry the story ID.

**B. Acceptance criteria**
- For each AC: met / not met / cannot tell, with the file and line that proves it.

**C. Correctness**
- Error paths handled; empty and edge inputs handled; no obvious crash.
- Tests exist per AC and would fail if the code were wrong (not just checking that code runs).

**D. Security and privacy (NFR-SEC, NFR-PRIV)**
- No keys, `.env`, or secrets in the diff (search the diff for `key`, `secret`, `password`, `eyJ`).
- Pages do not call Supabase directly. No service role key. Inputs validated. User text is escaped before HTML output.
- Role checks use `require_role()`; RLS not bypassed. No personal data logged.

**E. Maintainability (NFR-MNT)**
- Readable by learners: clear names, short functions, comments explain *why*. Type hints on service functions.

**F. UI, accessibility, ethics (only if UI changed)**
- Uses design tokens and shared components. Labels on inputs. Not color-only. Reduce motion honoured.
- No fake timers, fake scarcity, random rewards, leaderboards, or penalty wording.

## Report format
```
VERDICT: APPROVE | CHANGES REQUESTED
BLOCKERS (must fix): numbered, each with file:line and why
SHOULD FIX: numbered
NICE TO HAVE: numbered
AC RESULT: AC1 met / AC2 not met ...
NOT CHECKED: what you could not verify (for example needs a browser)
```
Keep each finding to two lines. If you are not sure, say "not sure" instead of guessing.
