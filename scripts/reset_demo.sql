-- scripts/reset_demo.sql
-- Demo reset (L-02, NFR-PRIV-07): wipe what learners created during a class, keep the shop.
--
-- WHO RUNS IT: the trainer, in the Supabase SQL editor (or psql), on the DEMO/DEV project.
-- WHEN: after a class, before the next one. See scripts/README.md.
--
-- REMOVES
--   * every account that is NOT a demo account and NOT an owner (their profile, cart, orders,
--     XP and badges go with it)
--   * ALL orders, order lines, saved confirmation emails and saved carts (demo accounts too)
--   * all XP and badges except the sign-up ones (+50 XP "register" and the "First Step" badge)
--   * the audit log (it only describes what happened during the class)
-- RESTORES
--   * demo accounts: their role and display name from the list below, XP back to 50 (level 1),
--     avatar and interests cleared so the Learner Passport can be demonstrated again
--   * seats of the 14 seed courses back to their seed values (see STEP 0c for why not "all full")
--   * order numbers start again at ...-0001
-- KEEPS
--   * the catalog: categories, courses (also ones made in class), modules, learning paths, badges
--   * demo accounts and owner accounts, and their passwords
--   * course images in Storage (see scripts/README.md to remove uploaded ones)
--
-- SAFE BY DEFAULT: as written, this file is a DRY RUN. It changes nothing and the last table
-- it shows lists how many rows WOULD be removed. To really reset, change 'NO' to 'YES' in
-- STEP 0a and run it again. After a real reset, the same table shows what is left (all 0).
--
-- After a real reset, run supabase/seed/02_sample_orders.sql to put the sample orders back.

-- ======================================================================== STEP 0: settings

-- 0a. The safety switch. 'NO' = dry run (nothing changes). 'YES' = really reset.
select set_config('skillforge.reset_confirm', 'NO', false);

-- 0b. Demo accounts to KEEP, with the role and name they should have
--     (same list as docs/deployment/demo-accounts.md; change it if you used other emails).
--     Owner accounts are always kept, even if they are not in this list.
-- (The "drop ... if exists" lines let you run this file twice in the same SQL editor session.
--  "pg_temp." means only this session's temporary objects can be dropped, never a real table.)
drop view if exists pg_temp.reset_kept_profiles;
drop table if exists pg_temp.reset_keep_accounts;
create temporary table reset_keep_accounts (
  email         text primary key,
  demo_role     text not null check (demo_role in ('customer', 'staff', 'owner')),
  display_name  text not null
);
insert into reset_keep_accounts (email, demo_role, display_name) values
  ('customer@skillforge.example', 'customer', 'Demo Learner'),
  ('learner2@skillforge.example', 'customer', 'Second Learner'),
  ('staff@skillforge.example',    'staff',    'Demo Staff'),
  ('owner@skillforge.example',    'owner',    'Demo Owner');

-- 0c. Seats of the seed courses, copied from supabase/seed/01_catalog.sql.
--     Not every course goes back to "full": the seed deliberately has one course with only
--     3 seats left and one that is sold out, so those demo moments still work after a reset.
drop table if exists pg_temp.reset_seed_seats;
create temporary table reset_seed_seats (
  slug             text primary key,
  seats_total      integer not null,
  seats_available  integer not null
);
insert into reset_seed_seats (slug, seats_total, seats_available) values
  ('prompt-engineering-fundamentals', 200, 200),
  ('ai-ethics-for-everyone',          150, 150),
  ('building-chatbots-with-python',    60,   3),  -- "only 3 seats left" demo
  ('intro-to-computer-vision',         40,  40),
  ('intro-to-machine-learning',       120, 120),
  ('intro-to-neural-networks',         80,  80),
  ('model-evaluation-essentials',     100,   0),  -- "sold out" demo
  ('deploying-ml-models',              50,  50),
  ('python-for-data-beginners',       250, 250),
  ('sql-for-analysts',                180, 180),
  ('data-visualization-storytelling', 120, 120),
  ('data-pipelines-101',               90,  90),
  ('data-quality-and-testing',        100, 100),
  ('cloud-data-warehousing-basics',    60,  60);

-- Which profiles survive the reset: demo accounts and owners. Used by every step below.
create or replace temporary view reset_kept_profiles as
select p.id
  from public.profiles p
 where lower(p.email) in (select lower(k.email) from reset_keep_accounts k)
    or p.role = 'owner';

-- ======================================================================== STEP 1: dry run, per account
-- Read-only. To see this list in the SQL editor, highlight just this SELECT and click Run.
-- Check the DELETE rows carefully before switching STEP 0a to 'YES'.
select p.email,
       p.role,
       p.display_name,
       case
         when lower(p.email) in (select lower(k.email) from reset_keep_accounts k) then 'KEEP (demo account, tidied)'
         when p.role = 'owner' then 'KEEP (owner)'
         else 'DELETE (account and all its data)'
       end as what_happens
  from public.profiles p
 order by what_happens, p.email;

-- ======================================================================== STEP 2: the reset
-- One DO block = one all-or-nothing step: if anything fails, nothing at all is changed.
do $$
declare
  v_rows integer;
begin
  if current_setting('skillforge.reset_confirm', true) is distinct from 'YES' then
    raise notice 'DRY RUN: nothing was changed. Set STEP 0a to ''YES'' to really reset.';
    return;
  end if;

  -- 2a. Delete learner accounts. Deleting the Auth user also deletes their profile, and the
  --     profile's cascade rules delete their cart, orders, order lines, emails, XP and badges.
  delete from auth.users u
   where u.id in (select p.id from public.profiles p)
     and u.id not in (select k.id from reset_kept_profiles k);
  get diagnostics v_rows = row_count;
  raise notice 'Deleted % learner account(s)', v_rows;

  -- 2b. Everything demo and owner accounts bought or saved during the class.
  delete from public.email_outbox;
  get diagnostics v_rows = row_count;
  raise notice 'Deleted % saved email(s)', v_rows;

  delete from public.order_items;
  delete from public.orders;
  get diagnostics v_rows = row_count;
  raise notice 'Deleted % order(s)', v_rows;

  delete from public.cart_items;
  get diagnostics v_rows = row_count;
  raise notice 'Deleted % cart row(s)', v_rows;

  -- 2c. XP and badges back to "just signed up": keep only +50 for registering and First Step.
  delete from public.xp_events where action <> 'register';
  delete from public.user_badges where badge_code <> 'first_step';

  -- 2d. Demo and owner profiles: XP and level from what is left, Passport cleared.
  --     Allowed here because the profile guard trusts the database owner (SQL editor).
  update public.profiles p
     set xp_total      = coalesce(x.points, 0),
         level         = public.level_for_xp(coalesce(x.points, 0)),
         avatar        = null,
         interests     = '{}',
         reduce_motion = false
    from (select pr.id,
                 (select sum(e.points)::integer from public.xp_events e where e.user_id = pr.id) as points
            from public.profiles pr) x
   where x.id = p.id;

  -- Put demo roles and names back, in case the owner promoted or renamed someone in class.
  -- Promote first, then demote, so there is always at least one owner (LAST_OWNER rule).
  update public.profiles p
     set role = k.demo_role, display_name = k.display_name
    from reset_keep_accounts k
   where lower(p.email) = lower(k.email)
     and k.demo_role = 'owner';
  update public.profiles p
     set role = k.demo_role, display_name = k.display_name
    from reset_keep_accounts k
   where lower(p.email) = lower(k.email)
     and k.demo_role <> 'owner';

  -- 2e. Seats of the seed courses back to their seed values. Both columns are set together,
  --     so the "available <= total" rule is never broken in between.
  update public.courses c
     set seats_total = s.seats_total,
         seats_available = s.seats_available
    from reset_seed_seats s
   where c.slug = s.slug
     and (c.seats_total, c.seats_available) is distinct from (s.seats_total, s.seats_available);
  get diagnostics v_rows = row_count;
  raise notice 'Restored seats on % seed course(s)', v_rows;

  -- 2f. Order numbers start again at ORD-<date>-0001 (safe: there are no orders left).
  perform setval('public.order_number_seq', 1, false);

  -- 2g. Last, so the seat changes above don't leave entries behind either.
  delete from public.audit_log;

  raise notice 'RESET DONE. Next: run supabase/seed/02_sample_orders.sql';
end;
$$;

-- ======================================================================== STEP 3: summary
-- Dry run: how many rows WOULD be removed or changed. After a real reset: what is left (all 0).
select current_setting('skillforge.reset_confirm', true) as reset_confirm, item, how_many
from (values
  (1, 'Learner accounts to delete',
      (select count(*) from public.profiles p where p.id not in (select k.id from reset_kept_profiles k))),
  (2, 'Orders',                      (select count(*) from public.orders)),
  (3, 'Order lines',                 (select count(*) from public.order_items)),
  (4, 'Saved confirmation emails',   (select count(*) from public.email_outbox)),
  (5, 'Saved cart rows',             (select count(*) from public.cart_items)),
  (6, 'XP events (not sign-up)',     (select count(*) from public.xp_events where action <> 'register')),
  (7, 'Badges (not First Step)',     (select count(*) from public.user_badges where badge_code <> 'first_step')),
  (8, 'Audit log entries',           (select count(*) from public.audit_log)),
  (9, 'Seed courses with changed seats',
      (select count(*) from public.courses c join reset_seed_seats s on s.slug = c.slug
        where (c.seats_total, c.seats_available) is distinct from (s.seats_total, s.seats_available))),
  (10, 'Demo accounts to tidy (role, name, XP, Passport)',
      (select count(*) from public.profiles p join reset_keep_accounts k on lower(k.email) = lower(p.email)
        where p.role <> k.demo_role or p.display_name <> k.display_name
           or p.avatar is not null or p.interests <> '{}'
           or p.xp_total <> coalesce((select sum(e.points) from public.xp_events e
                                       where e.user_id = p.id and e.action = 'register'), 0)))
) as summary(sort_order, item, how_many)
order by sort_order;
