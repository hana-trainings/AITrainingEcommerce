---
name: git-pr-workflow
description: Use to create a story branch, make clean commits, sync with main, run the secret check, push, and open a pull request. Never pushes to main.
---

# Git and pull request workflow

## Branch (start of a story)
```
git checkout main
git pull
git checkout -b feature/<pick>-<story>-<short-name>      # e.g. feature/U2-03-US-402-place-order
```
Prefixes: `feature/`, `fix/`, `design/`, `db/`.

## Commit (during the story)
- Add files **by name**: `git add app/pages/checkout.py tests/unit/test_checkout.py`. Never `git add -A` or `git add .`.
- Message: `<story id>: <what changed>` (for example `US-402: disable Place order until demo box is ticked`).
- Small commits, each one passing tests.

## Before pushing: safety checks
1. `git status`: no `.env`, `secrets.toml`, `outbox/`, `.venv/`.
2. `git diff --cached`: read it. Look for keys, tokens, passwords, real emails.
3. `ruff check .` and `python -m pytest tests/unit -q` pass.
If anything looks like a secret: stop, unstage it, tell the user. If a secret was ever committed, tell the Lead at once so the key can be rotated. Deleting it in a later commit is not enough.

## Sync
```
git fetch origin
git rebase origin/main
```
If there are conflicts: show the conflicting files, explain both sides, propose a fix, and wait for the user. Never use `git push --force` (use `--force-with-lease` only on your own feature branch after a rebase, and only if the user agrees).

## Push and PR
```
git push -u origin feature/<pick>-<story>-<short-name>
gh pr create --base main --title "<pick> <story id> <title>" --body-file <body.md>
```
PR body contains: `Closes #<issue>`, a summary of 3 lines or fewer, which AC are met, test results, manual test plan link, screenshots (desktop and mobile) for UI changes, the PR checklist from plan section 4.1, and `schema-change` label if a migration is included.

## After merge
```
git checkout main
git pull
git branch -d feature/<pick>-<story>-<short-name>
```

## Never
Push to `main`, merge your own PR, rewrite shared history, commit generated files or secrets.
