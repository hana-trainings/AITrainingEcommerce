---
name: write-tests
description: Use when writing or running unit tests for a story. Covers pytest for services, Streamlit AppTest for pages, the fake Supabase client, and ruff.
---

# Write and run tests

## Where tests go
- Service and validation logic: `tests/unit/test_<module>.py`
- Page behaviour (no browser): `tests/unit/test_page_<name>.py` using `streamlit.testing.v1.AppTest`
- Database behaviour (RPC, RLS, no oversell): `tests/integration/` against the **test** Supabase project only. Never run integration tests against shared dev data unless the Lead says so.

## Rules
1. One test group per acceptance criterion. Name tests after the AC: `test_us402_ac3_place_order_disabled_until_checkbox_ticked`.
2. For each story write at least: one happy path, one error path, one edge case (empty, zero, maximum, wrong role).
3. Use the fake Supabase client and sample data from `tests/conftest.py`. Do not call the real network in unit tests.
4. Use `AppTest.from_file("app/views/<page>.py")` for pages. Set `session_state` to fake a signed-in role. Assert on widgets, text, and disabled state.
5. Tests must not depend on each other or on test order.
6. Never put real keys, emails, or passwords in tests.

## Commands (run in the project venv)
```
ruff check .
python -m pytest tests/unit -q
python -m pytest tests/unit/test_orders.py -q      # one file
python -m pytest -k us402 -q                       # one story
python -m pytest tests/unit --cov=app -q           # coverage, if pytest-cov is installed
```

## When a test fails
Say whether the **test** or the **code** is wrong and why, before changing anything. Do not weaken or delete a test just to get green.

## Finish
Report: tests added (count), result line from pytest, and which ACs have no automated test (these go to the manual test plan).
