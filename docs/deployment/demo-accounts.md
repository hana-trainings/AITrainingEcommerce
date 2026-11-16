# Demo accounts

The demo needs one account per role. **Passwords are never written in this repo** (NFR-SEC-04). The trainer picks them and shares them with the class separately (for example on the whiteboard or in the trainer guide).

| Role | Suggested email | Display name |
|---|---|---|
| Customer | `customer@skillforge.example` | Demo Learner |
| Staff | `staff@skillforge.example` | Demo Staff |
| Owner | `owner@skillforge.example` | Demo Owner |
| Customer (optional second) | `learner2@skillforge.example` | Second Learner |

`.example` addresses can never receive real mail, which is what we want. If your project refuses them, use any training address you control, and change the emails in the SQL below and at the bottom of `supabase/seed/02_sample_orders.sql`.

## Before you start

All migrations must already be applied ([apply-database.md](apply-database.md)). The sign-up trigger from migration 0011 creates each user's profile automatically, so users created **before** the migrations will have no profile.

## Step 1: create the users (Supabase dashboard)

1. Open your **DEV** project.
2. **Authentication > Sign In / Providers > Email:** turn **Confirm email** off.
3. **Authentication > Users > Add user > Create new user** for each row in the table:
   - Email: from the table.
   - Password: the trainer's chosen password (at least 8 characters with a letter and a number).
   - Tick **Auto Confirm User**.
4. Each new user starts as a `customer` with 50 XP and the "First Step" badge. That is correct: new accounts are always customers (NFR-SEC-01).

The display name falls back to the part of the email before `@` (for example `staff`). Step 2 sets nicer names.

## Step 2: set roles and names (SQL editor)

Open **SQL Editor > New query**, paste this and click **Run**. It runs as the database owner, which is the only way to create an owner (the app lets the owner switch people only between customer and staff).

```sql
-- Give each demo account its role and a friendly display name.
update public.profiles set role = 'owner', display_name = 'Demo Owner'
 where lower(email) = 'owner@skillforge.example';

update public.profiles set role = 'staff', display_name = 'Demo Staff'
 where lower(email) = 'staff@skillforge.example';

update public.profiles set display_name = 'Demo Learner'
 where lower(email) = 'customer@skillforge.example';

update public.profiles set display_name = 'Second Learner'
 where lower(email) = 'learner2@skillforge.example';

-- Check the result: you should see owner, staff and customer.
select email, display_name, role, xp_total, level
  from public.profiles
 where email like '%@skillforge.example'
 order by role;
```

If a row is missing, that user was probably created before the migrations ran. Delete the user in **Authentication > Users** and create it again.

## Step 3: sample orders

Run `supabase/seed/02_sample_orders.sql` (after `01_catalog.sql`). It finds the demo customers by email and places their sample orders through the real checkout function. Missing users are skipped with a notice.

## Resetting after a class

To remove a learner's test account, delete the user in **Authentication > Users**. Their profile, cart, orders, XP and badges are removed with it. The last owner can't be demoted, so to replace the owner, promote the new owner first in SQL, then demote the old one.
