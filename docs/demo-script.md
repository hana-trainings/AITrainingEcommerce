# Demo script: the main journey in 10 minutes

A click-by-click walk through SkillForge Academy, from browsing as a guest to the owner managing staff. Use it for the final demo, an open day, or to check a deployment end to end.

**Before you start**

- The demo data is fresh: `scripts/reset_demo.sql` and then `supabase/seed/02_sample_orders.sql` have been run (see [deployment/trainer-guide.md](deployment/trainer-guide.md)).
- You know the demo customer, staff and owner passwords (shared privately, never in the repo).
- Open the app in a **private browser window**, so you start as a guest.
- Pick one course to buy. This script uses **SQL for Analysts** (Beginner, $59.00, plenty of seats). Note its seats left before you start.

| Time | Step | Role |
|---|---|---|
| 0:00 | 1. Home and browse | Guest |
| 1:00 | 2. Search and filter | Guest |
| 2:00 | 3. Course detail | Guest |
| 3:00 | 4. Cart | Guest |
| 4:00 | 5. Checkout asks you to sign in | Guest to customer |
| 5:00 | 6. Place the order | Customer |
| 6:00 | 7. Confirmation | Customer |
| 7:00 | 8. My orders and the email | Customer |
| 8:00 | 9. Staff sees the order | Staff |
| 9:00 | 10. Owner manages staff | Owner |

## 1. Home and browse (Guest, 1 min)

- **Click:** nothing yet; the app opens on **Home**.
- **Show:** featured courses and learning paths. Every card shows price, level and the XP you would earn.
- **Say:** "This is a demo store. The courses are fictional and no money ever changes hands."

## 2. Search and filter (Guest, 1 min)

- **Click:** **Courses** in the sidebar. Type `sql` in the search box. Then filter by category **Data Analytics** and level **Beginner**.
- **Show:** results update; sort by price.
- **Try:** search for `zzz`: the friendly "no results" message with a way back.
- **Say:** "Guests can only ever see published courses. Drafts are hidden by the database, not just by the page."

## 3. Course detail (Guest, 1 min)

- **Click:** **SQL for Analysts**.
- **Show:** description, outcomes, the **seat meter** (real seats left, no fake scarcity), the **locked module preview**, and where the course sits in the **Data Analyst Path**.
- **Optional:** open **Model Evaluation Essentials** to show a sold-out course: you can't add it to the cart.

## 4. Cart (Guest, 1 min)

- **Click:** **Add to cart** on SQL for Analysts, then **Cart** in the sidebar.
- **Do:** change the seats from 1 to 2 (the limit is 5 per course).
- **Show:** the total updates and the "unlock preview" shows the XP you would earn.
- **Say:** "As a guest the cart lives only in this browser session."

## 5. Checkout asks you to sign in (Guest to customer, 1 min)

- **Click:** **Checkout**. You are asked to sign in or register.
- **Do:** sign in with the **demo customer** account.
- **Show:** you come back to checkout and the cart is still there. The header now shows the name, level and XP bar.
- **Optional:** type a wrong password first: the message is just "Email or password is incorrect", so nobody can find out which emails have accounts.

## 6. Place the order (Customer, 1 min)

- **Show:** items, seats, total, XP to earn, the email the confirmation "goes" to, and the notice **"Demo store: no payment is taken."**
- **Do:** tick **"I understand this is a demo order"**, then click **Place order** once.
- **Say:** "One database function does everything in one transaction: checks seats, creates the order, takes the seats, awards XP and empties the cart. If any part fails, nothing happens at all. The button is disabled after one click, and even a double click can't make two orders."

## 7. Confirmation (Customer, 1 min)

- **Show:** the order number (`ORD-YYYYMMDD-XXXX`), date, items, total, the XP earned, any new badge such as **First Unlock**, and **Next in your path**.
- **Say:** "XP and badges are worked out by the database, never sent by the browser, so nobody can give themselves points. No timers, no random rewards, no leaderboards."

## 8. My orders and the email (Customer, 1 min)

- **Click:** **My orders**.
- **Show:** the new order at the top (newest first), with the two sample orders below it. Open it and click **View confirmation email**.
- **Say:** "No email was sent. A copy was saved as a file in `outbox/` and in the database. In the cloud, files disappear on restart, so the database copy is the one you see here."
- **Optional:** open **Learner Passport** to show XP, level and earned versus locked badges.
- **Do:** **Sign out**.

## 9. Staff sees the order (Staff, 1 min)

- **Do:** sign in as the **demo staff** account. The **Admin** section appears in the sidebar.
- **Click:** **Orders**. Search for the order number from step 7. Open it to see the items and the email preview.
- **Click:** **Manage courses**. Find SQL for Analysts: seats available went down by 2.
- **Optional:** **Dashboard** shows total orders, revenue (demo), seats sold and charts.
- **Try:** type the **Staff** page's address into the browser: "You don't have access". Staff can't change roles.
- **Do:** **Sign out**.

## 10. Owner manages staff (Owner, 1 min)

- **Do:** sign in as the **demo owner**.
- **Click:** **Staff**. Find the demo customer and change their role to **staff**. Then change it back to **customer**.
- **Show:** each change is recorded in the audit log, and the owner can't remove the last owner.
- **Say:** "The menu hides admin pages, but that is only convenience. The real protection is Row Level Security in the database: we prove it with `supabase/tests/rls_test.sql`, which tries every role against every table."

## After the demo

- Sign out.
- To make the demo repeatable, run `scripts/reset_demo.sql` (dry run first) and then `supabase/seed/02_sample_orders.sql`.

## If something doesn't match

| You see | Why | What to do |
|---|---|---|
| Signed out after refreshing the tab | Known limitation: a refresh starts a new session | Sign in again |
| "Not enough seats" at checkout | Someone else bought the seats first | Good moment: show the cart message, lower the seats and retry |
| No sample orders in My orders | `02_sample_orders.sql` not run after the last reset | Run it in the SQL editor |
| App asleep | Free hosting sleeps when unused | Wake it a few minutes before the demo |
