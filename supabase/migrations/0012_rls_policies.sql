-- 0012_rls_policies.sql
-- Row Level Security: the database itself decides who may see or change each row,
-- so hiding a page in the app is never the only protection (NFR-SEC-05, NFR-SEC-06, US-701 AC3).
--
-- Roles in Supabase:
--   anon          = guest (not signed in)
--   authenticated = any signed-in user; profiles.role then says customer, staff or owner
-- Two layers work together:
--   GRANTs   say which tables/columns a role may touch at all.
--   POLICIES say which ROWS inside those tables.
-- Tip: "(select auth.uid())" is wrapped in a select so Postgres works it out once per query,
-- not once per row (much faster on big tables).

-- ---------------------------------------------------------------------------
-- Step 1: turn RLS on for every table. With RLS on and no policy, nobody sees anything.
-- ---------------------------------------------------------------------------
alter table public.profiles              enable row level security;
alter table public.categories            enable row level security;
alter table public.courses               enable row level security;
alter table public.course_modules        enable row level security;
alter table public.badges                enable row level security;
alter table public.user_badges           enable row level security;
alter table public.xp_events             enable row level security;
alter table public.learning_paths        enable row level security;
alter table public.learning_path_courses enable row level security;
alter table public.cart_items            enable row level security;
alter table public.orders                enable row level security;
alter table public.order_items           enable row level security;
alter table public.email_outbox          enable row level security;
alter table public.audit_log             enable row level security;

-- ---------------------------------------------------------------------------
-- Step 2: table and column privileges (least privilege).
-- Supabase grants everything to anon/authenticated by default; we start from nothing instead.
-- ---------------------------------------------------------------------------
revoke all on all tables in schema public from anon, authenticated;

-- Guests may only read the public catalog.
grant select on public.categories, public.courses, public.course_modules,
                public.learning_paths, public.learning_path_courses, public.badges
  to anon;

-- Signed-in users: read access; policies below narrow it to the right rows.
grant select on all tables in schema public to authenticated;

-- Catalog editing (policies limit this to staff/owner).
grant insert, update, delete on public.categories, public.courses, public.course_modules,
                                public.learning_paths, public.learning_path_courses, public.badges
  to authenticated;

-- Own cart.
grant insert, update, delete on public.cart_items to authenticated;

-- Own confirmation email copy (written by the app right after place_order).
grant insert on public.email_outbox to authenticated;

-- Profiles: only these columns can ever be changed from the app. xp_total, level, email, id are left out.
-- "role" is allowed here but the guard trigger (0011) lets only the owner change it.
grant update (display_name, avatar, interests, reduce_motion, role) on public.profiles to authenticated;

-- Orders: staff may change the status only (cancel, US-408). Orders are created by place_order.
grant update (status) on public.orders to authenticated;

-- Identity columns need their sequence when staff create catalog rows.
grant usage on all sequences in schema public to authenticated;

-- ---------------------------------------------------------------------------
-- Step 3: policies, one table at a time.
-- ---------------------------------------------------------------------------

-- ===== profiles =====
-- Each user can see their own profile, so the header can show their name, level and XP.
create policy profiles_select_own on public.profiles
  for select to authenticated
  using (id = (select auth.uid()));

-- Staff and owner can see all profiles, to look up who placed an order and to manage staff.
create policy profiles_select_staff on public.profiles
  for select to authenticated
  using ((select public.is_staff()));

-- Users can edit their own profile; column grants and the guard trigger block role/XP/level changes.
create policy profiles_update_own on public.profiles
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));

-- Only the owner can update other people's profiles, which is how roles are changed (US-709).
create policy profiles_update_owner on public.profiles
  for update to authenticated
  using ((select public.is_owner()))
  with check ((select public.is_owner()));

-- ===== categories =====
-- Everyone, including guests, can read categories because they are needed to browse the catalog.
create policy categories_select_all on public.categories
  for select to anon, authenticated
  using (true);

-- Staff and owner can add categories to keep the catalog organised (US-711).
create policy categories_insert_staff on public.categories
  for insert to authenticated
  with check ((select public.is_staff()));

-- Staff and owner can rename or reorder categories (US-711).
create policy categories_update_staff on public.categories
  for update to authenticated
  using ((select public.is_staff()))
  with check ((select public.is_staff()));

-- Only the owner can delete a category, matching the owner-only delete rule for the catalog.
create policy categories_delete_owner on public.categories
  for delete to authenticated
  using ((select public.is_owner()));

-- ===== courses =====
-- Guests and customers see only published courses; staff and owner also see drafts (US-702 AC3).
create policy courses_select_published_or_staff on public.courses
  for select to anon, authenticated
  using (is_published or (select public.is_staff()));

-- Staff and owner can create courses (US-703).
create policy courses_insert_staff on public.courses
  for insert to authenticated
  with check ((select public.is_staff()));

-- Staff and owner can edit, publish and adjust seats (US-704 to US-706).
create policy courses_update_staff on public.courses
  for update to authenticated
  using ((select public.is_staff()))
  with check ((select public.is_staff()));

-- Only the owner can permanently delete a course; sold courses are protected by a foreign key (US-710).
create policy courses_delete_owner on public.courses
  for delete to authenticated
  using ((select public.is_owner()));

-- ===== course_modules =====
-- Anyone can read the syllabus of a course they are allowed to see (the "sneak peek", US-202).
create policy course_modules_select_visible on public.course_modules
  for select to anon, authenticated
  using (exists (
    select 1 from public.courses c
     where c.id = course_modules.course_id
       and (c.is_published or (select public.is_staff()))
  ));

-- Staff and owner can add modules while building a course (US-703).
create policy course_modules_insert_staff on public.course_modules
  for insert to authenticated
  with check ((select public.is_staff()));

-- Staff and owner can edit modules (US-704).
create policy course_modules_update_staff on public.course_modules
  for update to authenticated
  using ((select public.is_staff()))
  with check ((select public.is_staff()));

-- Staff and owner can remove a module from a syllabus; this edits a course, it doesn't delete one.
create policy course_modules_delete_staff on public.course_modules
  for delete to authenticated
  using ((select public.is_staff()));

-- ===== learning_paths =====
-- Everyone can read learning paths because the skill tree is shown to guests too (US-604).
create policy learning_paths_select_all on public.learning_paths
  for select to anon, authenticated
  using (true);

-- Staff and owner can create paths (US-711).
create policy learning_paths_insert_staff on public.learning_paths
  for insert to authenticated
  with check ((select public.is_staff()));

-- Staff and owner can edit paths (US-711).
create policy learning_paths_update_staff on public.learning_paths
  for update to authenticated
  using ((select public.is_staff()))
  with check ((select public.is_staff()));

-- Only the owner can delete a whole path, matching the owner-only delete rule for the catalog.
create policy learning_paths_delete_owner on public.learning_paths
  for delete to authenticated
  using ((select public.is_owner()));

-- ===== learning_path_courses =====
-- Anyone can see which visible courses are in a path, so drafts don't leak into the skill tree.
create policy learning_path_courses_select_visible on public.learning_path_courses
  for select to anon, authenticated
  using (exists (
    select 1 from public.courses c
     where c.id = learning_path_courses.course_id
       and (c.is_published or (select public.is_staff()))
  ));

-- Staff and owner can add a course to a path (US-711).
create policy learning_path_courses_insert_staff on public.learning_path_courses
  for insert to authenticated
  with check ((select public.is_staff()));

-- Staff and owner can reorder courses in a path (US-711).
create policy learning_path_courses_update_staff on public.learning_path_courses
  for update to authenticated
  using ((select public.is_staff()))
  with check ((select public.is_staff()));

-- Staff and owner can take a course out of a path; this edits the path, it deletes no course.
create policy learning_path_courses_delete_staff on public.learning_path_courses
  for delete to authenticated
  using ((select public.is_staff()));

-- ===== badges =====
-- Everyone can read badge definitions, so locked badges can be shown as hints (US-603 AC1).
create policy badges_select_all on public.badges
  for select to anon, authenticated
  using (true);

-- Staff and owner can create a badge for a new learning path (US-711 AC2).
create policy badges_insert_staff on public.badges
  for insert to authenticated
  with check ((select public.is_staff()));

-- Staff and owner can edit badge names and hints (US-711).
create policy badges_update_staff on public.badges
  for update to authenticated
  using ((select public.is_staff()))
  with check ((select public.is_staff()));

-- Only the owner can delete a badge, because that also removes it from every learner.
create policy badges_delete_owner on public.badges
  for delete to authenticated
  using ((select public.is_owner()));

-- ===== user_badges ===== (no insert/update/delete policy: only database functions award badges)
-- A user can see only their own badges, so nobody can compare or rank other learners (US-606).
create policy user_badges_select_own on public.user_badges
  for select to authenticated
  using (user_id = (select auth.uid()));

-- Staff and owner can see all awarded badges for support.
create policy user_badges_select_staff on public.user_badges
  for select to authenticated
  using ((select public.is_staff()));

-- ===== xp_events ===== (no write policy: only database functions award XP, US-601 AC2)
-- A user can see only their own XP history.
create policy xp_events_select_own on public.xp_events
  for select to authenticated
  using (user_id = (select auth.uid()));

-- Staff and owner can see all XP history for support.
create policy xp_events_select_staff on public.xp_events
  for select to authenticated
  using ((select public.is_staff()));

-- ===== cart_items =====
-- Each signed-in user can see only their own saved cart (US-305).
create policy cart_items_select_own on public.cart_items
  for select to authenticated
  using (user_id = (select auth.uid()));

-- Users can add only to their own cart, and only courses that are published (US-301).
create policy cart_items_insert_own on public.cart_items
  for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (select 1 from public.courses c where c.id = cart_items.course_id and c.is_published)
  );

-- Users can change quantities only in their own cart (US-303).
create policy cart_items_update_own on public.cart_items
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- Users can remove items only from their own cart (US-304).
create policy cart_items_delete_own on public.cart_items
  for delete to authenticated
  using (user_id = (select auth.uid()));

-- ===== orders ===== (no insert/delete policy: only place_order creates orders)
-- Customers can see only their own orders (US-407).
create policy orders_select_own on public.orders
  for select to authenticated
  using (user_id = (select auth.uid()));

-- Staff and owner can see all orders to support customers (US-707).
create policy orders_select_staff on public.orders
  for select to authenticated
  using ((select public.is_staff()));

-- Staff and owner can change an order's status (cancel, US-408); column grants allow only "status".
create policy orders_update_staff on public.orders
  for update to authenticated
  using ((select public.is_staff()))
  with check ((select public.is_staff()));

-- ===== order_items =====
-- Customers see lines of their own orders; staff and owner see all lines.
create policy order_items_select_own_or_staff on public.order_items
  for select to authenticated
  using (exists (
    select 1 from public.orders o
     where o.id = order_items.order_id
       and (o.user_id = (select auth.uid()) or (select public.is_staff()))
  ));

-- ===== email_outbox =====
-- Customers can read only the confirmation emails for their own orders (US-407 AC2).
create policy email_outbox_select_own on public.email_outbox
  for select to authenticated
  using (user_id = (select auth.uid()));

-- Staff and owner can read all saved emails to help customers (US-707 AC3).
create policy email_outbox_select_staff on public.email_outbox
  for select to authenticated
  using ((select public.is_staff()));

-- A user can save an email copy only for an order that is really theirs (US-406 AC3).
create policy email_outbox_insert_own_order on public.email_outbox
  for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.orders o
       where o.id = email_outbox.order_id
         and o.user_id = (select auth.uid())
    )
  );

-- ===== audit_log ===== (no write policy: only triggers and write_audit_log() add entries)
-- Staff and owner can read the audit log; customers and guests cannot.
create policy audit_log_select_staff on public.audit_log
  for select to authenticated
  using ((select public.is_staff()));
