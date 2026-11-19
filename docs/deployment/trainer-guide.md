# Trainer guide

Everything the trainer does around a class: get the demo ready, share access safely, show each role, and clean up afterwards. For the full first-time setup, see [apply-database.md](apply-database.md), [demo-accounts.md](demo-accounts.md) and [streamlit-cloud.md](streamlit-cloud.md).

## The day before class

1. **Wake everything up.** Free Supabase projects pause after about a week without use, and Streamlit Cloud apps fall asleep. Open the Supabase dashboard (restore the project if it says paused) and open the app URL once.
2. **Reset the demo data** if a previous class used it: [Resetting between classes](#resetting-between-classes).
3. **Run the security tests** in the SQL editor: `supabase/tests/rls_test.sql` and `supabase/tests/place_order_test.sql`. Only `PASS` lines, no `ERROR`.
4. **Do the smoke test** from [streamlit-cloud.md](streamlit-cloud.md#step-3-smoke-test-the-live-app) (5 minutes).
5. Check that the sold-out course ("Model Evaluation Essentials") and the "only 3 seats left" course ("Building Chatbots with Python") look right. They are useful demo moments.
6. Have [../demo-script.md](../demo-script.md) open.

## Demo accounts: share them privately

There is one account per role (customer, staff, owner, plus an optional second customer). The emails are in [demo-accounts.md](demo-accounts.md). **Passwords are never written in the repo** (NFR-SEC-04).

- Write the passwords on the whiteboard, or give them out on paper or in a private class channel. Not in GitHub Issues, PRs, commit messages or screenshots.
- Usually only the **customer** password is shared with the whole class. Learners can also register their own accounts.
- Keep the **owner** password to yourself. Share **staff** only for the admin part of the lesson.
- To change a demo password between groups, delete that user in **Authentication > Users**, create it again with the new password, and re-run the role `update` from [demo-accounts.md](demo-accounts.md) step 2. (Password reset emails are off in this demo.)
- Learners should register with made-up names. Remind them not to use their real full name or school email (NFR-PRIV-01). Any address works because no email is ever sent.
- "Forgot password?" in the app says **"Ask your trainer"** (decision Q3). To help, delete that learner's account in **Authentication > Users** and let them register again.

## What each role can show

| Role | Sign in as | What to show | Teaching point |
|---|---|---|---|
| Guest | Nobody (private window) | Browse, search, filters, course detail with locked modules, add to cart | Guests can only read the published catalog; the database itself hides drafts |
| Customer | Demo customer (or a new account) | Cart (1 to 5 seats per course), checkout, confirmation with XP and badges, My orders, confirmation email, Learner Passport, skill map | Checkout is one database transaction: seats, order, XP and cart change together or not at all |
| Staff | Demo staff | Dashboard, course list with drafts, create/edit/publish a course, adjust seats with a reason, all orders, cancel an order (seats come back) | Staff can manage the shop but cannot change roles or delete courses |
| Owner | Demo owner | Everything staff can do, plus Manage staff (promote a customer to staff and back) and delete a course that was never sold | The owner can't remove the last owner; every role change is in the audit log |

Good "try to break it" moments:

- As a customer, open an admin page by typing its URL: "You don't have access".
- Two learners each put all 3 remaining seats of "Building Chatbots with Python" in their cart and place the order at the same time: one succeeds, the other gets a clear "not enough seats" message, and seats never go below 0.
- Double-click "Place order": still only one order.
- Run `supabase/tests/rls_test.sql` live and read the `PASS` lines together: the database blocks customer A from reading customer B's orders, even without the app.

## Resetting between classes

Learners' accounts, orders and XP pile up. Before the next group:

1. Run `scripts/reset_demo.sql` in the SQL editor. It starts as a **dry run** that changes nothing and shows what would be removed. Follow [../../scripts/README.md](../../scripts/README.md) to switch it to a real reset.
2. Run `supabase/seed/02_sample_orders.sql` to put the sample orders back.
3. If you changed demo passwords, share the new ones privately.

The reset keeps the catalog and the demo accounts, deletes learner accounts and everything they created, and puts seats and XP back to the starting values.

**On a laptop:** confirmation emails are also written as files to the `outbox/` folder. Just delete the files. In the cloud they disappear on their own when the app restarts.

## If something goes wrong in class

| Problem | Quick fix |
|---|---|
| App asleep or very slow | Open the URL and wait a minute; tell learners to refresh |
| Signed out after refreshing the browser tab | Expected (NFR-AUTH-06). Sign in again |
| A learner forgot their password | Delete their user in Supabase **Authentication > Users**; they register again |
| Someone promoted the wrong user | Sign in as owner and switch them back on Manage staff; or run the reset |
| Data looks messy mid-lesson | Run the reset (it takes seconds), then `02_sample_orders.sql` |
| A course was deleted or broken by staff practice | Re-run `supabase/seed/01_catalog.sql`: it adds back missing seed courses and skips existing ones |
