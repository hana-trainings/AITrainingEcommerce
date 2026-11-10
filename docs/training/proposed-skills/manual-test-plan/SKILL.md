---
name: manual-test-plan
description: Use to create a click-through manual test checklist for a story, built from its acceptance criteria, for desktop and mobile, with demo accounts and expected results.
---

# Manual test plan

Input: a pick code or story ID.

## Steps
1. Read the story's acceptance criteria in doc 01 and its screen in doc 02.
2. Create `docs/testing/<pick>-manual-test.md` with this layout:

```
# Manual test: <pick> <story id> <title>
Tester: ____   Date: ____   Branch: ____   Env: local + dev Supabase

## Setup
- App running: streamlit run app/streamlit_app.py
- Accounts: demo customer / staff / owner (ask the Lead for the demo logins; never write passwords in this file)
- Data needed: <seed courses, items in cart, etc.>

## Test cases
| # | AC | Role | Steps | Expected result | Pass / Fail | Notes |

## Negative and edge cases
(wrong role, signed out, empty data, double click, back button, refresh, very long text)

## Mobile check (resize window to about 390 px wide)
(layout does not break, buttons reachable, nothing cut off)

## Accessibility quick check
(keyboard Tab order, visible focus, text is readable, no information shown by color alone, Reduce motion honoured)

## Ethical gamification check (only if the story shows XP, badges, or levels)
(no fake timer, no fake scarcity, no random reward, no leaderboard, no penalty wording)

## Result
Passed ___ / ___   Bugs found: <Issue numbers>
```

3. Every AC must appear in at least one test case. Steps are numbered, short, and use exact button and page names.
4. Include at least 2 negative cases and 1 mobile case.

## Never
Write real passwords, keys, or personal emails into the file.
