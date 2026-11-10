---
name: implement-story
description: Use when asked to build a story by pick code (for example U2-03 or US-402). Reads the story, plans, then implements only that story's files, with tests, following the team's rules.
---

# Implement one story

Input: a pick code (e.g. `U2-03`) or story ID (e.g. `US-402`).

## Steps

1. **Find the story.** Look it up in `docs/planning/work-division-plan.md` (files, depends on, size) and in `docs/requirements/01-product-features-user-stories.md` (acceptance criteria AC1, AC2 ...). Also read the UI screen in doc 02 if the story has a screen.
2. **Check it is allowed to start.** Every story in "Depends on" must be merged to `main`. If not, stop and tell the user which story to do first.
3. **Check the branch.** The current branch must be `feature/<pick>-<story>-<short-name>`. If it is `main`, stop and ask the user to create the branch (see `git-pr-workflow`).
4. **Plan before coding.** Write a short plan: files to change, service functions to fill in, components to use, tests to write, one line per acceptance criterion. Show it and wait for approval.
5. **Load the matching skills.**
   - Streamlit pages and components: `developing-with-streamlit`.
   - Any SQL, migration, RLS: `supabase-postgres-best-practices`.
   - Any look-and-feel decision: `ui-ux-pro-max` (follow the tokens in doc 02 section 3).
6. **Implement.** Fill in the existing stubs. Keep the stub signatures. Pages call services only. Use the existing components.
7. **Write tests** with the `write-tests` skill, one test group per acceptance criterion.
8. **Run** `ruff check .` and `python -m pytest tests/unit -q`. Fix until both pass.
9. **Write a manual test plan** with the `manual-test-plan` skill and save it as `docs/testing/<pick>-manual-test.md`.
10. **Report** in 5 lines or fewer: what changed, which AC are covered, test results, anything not done, anything that needs the Lead.

## Stop and ask if
- The story needs a change to a service signature, a component signature, `app/streamlit_app.py`, `requirements.txt`, or an existing migration.
- An acceptance criterion is unclear or two documents disagree.
- You would need to touch files that are not listed for the story.

## Never
- Commit, push, or open a PR (the user does that with `git-pr-workflow`).
- Work on a second story in the same branch.
- Read or print `.env` or secrets.
