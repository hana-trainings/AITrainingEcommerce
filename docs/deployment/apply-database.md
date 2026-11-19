# Apply the database to the Supabase DEV project

This guide sets up every table, security rule, function and the image bucket in your **DEV** Supabase project, then loads sample data. Never run these steps against a production project during class.

## What is in `supabase/`

| File | What it does |
|---|---|
| `migrations/0001_profiles.sql` | `profiles` table (one row per user) and the `set_updated_at` trigger helper |
| `migrations/0002_role_helpers.sql` | `current_role_name()`, `is_staff()`, `is_owner()` and the `private` schema |
| `migrations/0003_catalog.sql` | `categories`, `courses`, `course_modules` with all CHECK rules |
| `migrations/0004_gamification_tables.sql` | `badges` (plus the 5 core badges), `user_badges`, `xp_events` |
| `migrations/0005_learning_paths.sql` | `learning_paths`, `learning_path_courses` |
| `migrations/0006_cart_items.sql` | Saved carts |
| `migrations/0007_orders.sql` | `orders`, `order_items`, order numbers, cancel rules (seats go back) |
| `migrations/0008_email_outbox.sql` | Saved copies of confirmation emails |
| `migrations/0009_audit_log.sql` | `audit_log`, automatic audit triggers, `write_audit_log()` |
| `migrations/0010_gamification_functions.sql` | XP, level and badge helpers, `claim_profile_completion()` |
| `migrations/0011_auth_user_trigger_and_profile_guard.sql` | Profile created on sign-up (+50 XP, First Step badge); users can't change their own role, XP or level |
| `migrations/0012_rls_policies.sql` | Row Level Security for guest, customer, staff, owner |
| `migrations/0013_storage_course_images.sql` | `course-images` bucket: public read, staff write, JPG/PNG/WebP, 2 MB |
| `migrations/0014_place_order.sql` | The checkout function `place_order(p_idempotency_key)` |
| `migrations/0020_email_outbox_one_per_order.sql` | One confirmation email per order (unique `order_id`), so a customer can't add a fake second email |
| `migrations/0025_admin_save_children.sql` | Admin functions that save a course's modules and path steps, and a path's course list, in one transaction |
| `migrations/0030_email_drafts.sql` | Turns `email_outbox` into the app's own email service: every email (order confirmation, welcome) is saved as a draft and never sent. One welcome email per user, only to their own address |
| `seed/01_catalog.sql` | 4 categories, 14 courses with modules, 3 learning paths, path badges |
| `seed/02_sample_orders.sql` | Sample orders for the demo customers (needs the demo users first) |
| `tests/place_order_test.sql` | Proves checkout cannot over-book or run twice (rolls everything back) |
| `tests/rls_test.sql` | Security-rule break test: tries every role against every table (rolls everything back) |
| `../scripts/reset_demo.sql` | Resets learner data between classes; dry run by default (see `scripts/README.md`) |

The order matters: each file uses things made by the files before it.

## Option A: Supabase SQL editor (easiest)

1. Open the Supabase dashboard and pick your **DEV** project. Check the project name at the top before you continue.
2. Go to **SQL Editor** and click **New query**.
3. For each file in `supabase/migrations/`, **in number order (0001 to 0014, then 0020, 0025 and 0030)**:
   1. Open the file in VS Code, select all, copy.
   2. Paste into the SQL editor and click **Run**.
   3. Wait for "Success. No rows returned". If you get an error, stop and read it. Do not skip a file.
4. Go to **Authentication > Sign In / Providers > Email** and turn **Confirm email** off. Supabase must send no emails: the app's own email service saves every email as a draft instead (migration 0030, admin page **Email drafts**). Set the minimum password length to 8.
5. Create the demo users and set their roles: follow [demo-accounts.md](demo-accounts.md).
6. Run `supabase/seed/01_catalog.sql` in the SQL editor.
7. Run `supabase/seed/02_sample_orders.sql`. The "Messages" tab shows which sample orders were created or skipped.
8. Run `supabase/tests/place_order_test.sql`, then `supabase/tests/rls_test.sql`. You should see only `PASS` notices and no `ERROR`. It ends with `ROLLBACK`, so it leaves nothing behind.

Running a migration twice gives "already exists" errors. That is expected: each migration is meant to be applied once. The seed files are safe to run again.

## Option B: Supabase CLI

Use this if you already have the CLI installed and logged in (`supabase login`).

```bash
# Link this repo folder to your DEV project once (the project ref is in the dashboard URL).
supabase link --project-ref <your-dev-project-ref>

# See what will be applied, then apply all migrations in order.
supabase db push --dry-run
supabase db push
```

The CLI remembers which migrations it has applied, so later you only push new files.

Then do steps 4 to 8 of Option A (auth settings, demo users, seed files, test). You can run the seed and test files with `psql` using the DEV database connection string from **Project Settings > Database**, for example:

```bash
psql "<dev-connection-string>" -v ON_ERROR_STOP=1 -f supabase/seed/01_catalog.sql
psql "<dev-connection-string>" -v ON_ERROR_STOP=1 -f supabase/seed/02_sample_orders.sql
psql "<dev-connection-string>" -f supabase/tests/place_order_test.sql
```

Keep the connection string out of the repo and out of chat: it contains the database password.

## Check that it worked

- **Table Editor:** every table shows a "RLS enabled" label.
- **Storage:** a public bucket called `course-images` exists.
- **Database > Functions:** `place_order`, `is_staff`, `is_owner`, `current_role_name`, `claim_profile_completion`, `write_audit_log`, `level_for_xp`.
- The test file prints six `PASS` lines.

## Changing the database later

Never edit a migration that has already been applied and merged. Add a new numbered file instead (for example `0015_add_course_language.sql`) and apply only that file.
