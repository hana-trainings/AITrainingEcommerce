# Trainer scripts

Scripts in this folder are for the **trainer only**. The app never runs them, and students don't need them.

| File | What it does |
|---|---|
| `reset_demo.sql` | Clears everything learners created during a class and puts the shop back to its starting state (NFR-PRIV-07). |

## `reset_demo.sql`: reset the demo between classes

### When to run it

- After a class, so the next group starts with an empty order list and fresh demo accounts.
- Before a live demo, so the admin dashboard and "My orders" show only the sample data.
- On the **demo or dev** Supabase project only. Check the project name at the top of the dashboard first.

### What it removes and what it keeps

| Removed | Kept |
|---|---|
| Accounts that learners registered in class, with everything they own | The four demo accounts and any owner account (passwords unchanged) |
| All orders, order lines, saved confirmation emails and saved carts | Categories, courses (including ones made in class), modules, learning paths, badges |
| XP and badges, except the sign-up ones (+50 XP and "First Step") | Course images in Storage |
| The audit log | |

It also puts things back:

- Demo accounts get their role and display name back (in case the owner promoted someone in class) and their Learner Passport is cleared, so you can demo "complete your profile" again.
- The 14 seed courses get their starting seats back. Two are not full on purpose: "Building Chatbots with Python" has 3 seats left and "Model Evaluation Essentials" is sold out, so those demo moments keep working.
- Order numbers start again at `-0001`.

### How to run it (Supabase SQL editor)

1. Open the **demo/dev** project, then **SQL Editor > New query**.
2. Paste the whole of `scripts/reset_demo.sql` and click **Run**. Nothing is changed yet: the file starts in **dry-run** mode.
3. Read the summary table at the bottom of the results. It shows how many rows **would** be removed.
4. To see exactly which accounts would be deleted, highlight only the STEP 1 `select` and click **Run**. Every learner account shows `DELETE`, and the demo accounts and owners show `KEEP`.
5. If it looks right, change `'NO'` to `'YES'` in STEP 0a and click **Run** again. The SQL editor may ask you to confirm a destructive query; say yes.
6. The summary table now shows what is left. Every row should be `0`.
7. Run `supabase/seed/02_sample_orders.sql` to put the sample orders back.
8. Change STEP 0a back to `'NO'` if you saved the query in the editor, so nobody runs a real reset by accident.

With psql instead: `psql "<dev-connection-string>" -v ON_ERROR_STOP=1 -f scripts/reset_demo.sql` (dry run), then edit STEP 0a and run it again. Keep the connection string out of the repo and out of chat.

The real reset is one all-or-nothing step: if anything goes wrong, nothing is changed and you see an error.

### If you used other demo emails

Edit the list in STEP 0b so it matches `docs/deployment/demo-accounts.md`. Any account that is not in that list and is not an owner **will be deleted**, so check the dry run.

### Things the script does not do

- **Course images:** images uploaded in class stay in the `course-images` bucket. Delete them in **Storage > course-images** if you want.
- **Courses made in class:** they are kept, because the catalog is kept. To find them, run:
  ```sql
  select slug, title, is_published, created_at from public.courses order by created_at desc;
  ```
  The owner can delete one from the admin area if it was never sold.
- **Seed course details:** if someone changed a price or title of a seed course, re-running `01_catalog.sql` won't change it back (it skips courses that already exist). Fix it in the admin area.

## Confirmation emails on a laptop (`outbox/`)

When you run the app locally, every order also writes an HTML file to the `outbox/` folder. These are only demo copies: no email is ever sent. To clear them, **just delete the files** (or the whole `outbox/` folder; the app creates it again when needed). The folder is git-ignored, so the files are never committed.

On Streamlit Community Cloud the `outbox/` files disappear by themselves when the app restarts. The copy that matters is in the `email_outbox` table, and the reset script clears it.
