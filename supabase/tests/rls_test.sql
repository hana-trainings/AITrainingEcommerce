-- supabase/tests/rls_test.sql
-- RLS break test (L-01, NFR-SEC-05, US-701 AC3).
-- We pretend to be each kind of user and TRY to do things they must not do. The database's
-- security rules (GRANTs + Row Level Security policies + guard triggers) must stop every attempt,
-- even though no app page is involved. We also check the things each role SHOULD be able to do,
-- so the test can't pass just because "nobody can do anything".
--
--   0. RLS is switched on for every table in the public schema.
--   1. Guest    : sees published courses only; sees no cart, order, profile, XP, badge or email rows.
--   2. Customer : A cannot read or change B's cart, orders, order lines, XP, badges, emails or profile;
--                 cannot change own role, XP or level; cannot create orders, XP or badges directly;
--                 cannot change seats or prices.
--   3. Staff    : can manage courses and read all orders; cannot change roles or delete courses.
--   4. Owner    : can change roles (customer <-> staff) and delete a course that was never sold.
--   5. Afterwards (as postgres): B's data really is unchanged.
--
-- How to run: paste the whole file into the Supabase SQL editor (DEV project only) and click Run,
-- or: psql "$DEV_DB_URL" -v ON_ERROR_STOP=1 -f supabase/tests/rls_test.sql
-- Plain SQL, no extensions needed. Everything happens inside one transaction that ends with
-- ROLLBACK, so no test users, courses or orders are left behind.
-- Passing = you see "PASS" notices and no ERROR. Any failed check raises an ERROR starting with "FAIL".
--
-- How "acting as a user" works (the same thing Supabase does for every app request):
--   set local role anon / authenticated   -> which database role runs the query
--   set_config('request.jwt.claims', ...) -> who auth.uid() says is signed in
--
-- Test users (all rolled back at the end):
--   Customer A  00000000-0000-4000-8000-00000000a001
--   Customer B  00000000-0000-4000-8000-00000000b002
--   Staff       00000000-0000-4000-8000-00000000c003
--   Owner       00000000-0000-4000-8000-00000000d004

begin;

-- ---------------------------------------------------------------- helpers (temporary)
-- Small check functions so each test below is one readable line. They live in pg_temp, so they
-- disappear with this session. They are SECURITY INVOKER (the default): the SQL they run uses
-- the rights of whoever is "acting" at that moment (guest, customer, staff or owner).

-- PASS if the query (a "select count(*) ...") finds 0 rows.
-- "permission denied" also counts as 0: that role may not read the table at all.
create function pg_temp.expect_none(p_label text, p_count_sql text)
returns void
language plpgsql
as $$
declare
  v_count bigint;
begin
  begin
    execute p_count_sql into v_count;
  exception when insufficient_privilege then
    v_count := 0;
  end;
  if v_count <> 0 then
    raise exception 'FAIL %: expected to see 0 rows, saw %', p_label, v_count;
  end if;
  raise notice 'PASS %', p_label;
end;
$$;

-- PASS if the query (a "select count(*) ...") finds at least 1 row.
create function pg_temp.expect_some(p_label text, p_count_sql text)
returns void
language plpgsql
as $$
declare
  v_count bigint;
begin
  execute p_count_sql into v_count;
  if v_count < 1 then
    raise exception 'FAIL %: expected to see rows, saw none', p_label;
  end if;
  raise notice 'PASS %', p_label;
end;
$$;

-- PASS if a change is refused. Three ways the database can refuse:
--   a) "permission denied" (no GRANT), or "new row violates row-level security policy" (both 42501),
--   b) our guard triggers raise 'NOT_ALLOWED: ...',
--   c) the policy hides the target rows, so the statement runs but changes 0 rows.
create function pg_temp.expect_blocked(p_label text, p_sql text)
returns void
language plpgsql
as $$
declare
  v_rows bigint;
begin
  begin
    execute p_sql;
    get diagnostics v_rows = row_count;
  exception
    when insufficient_privilege then
      raise notice 'PASS % (refused: %)', p_label, sqlerrm;
      return;
    when raise_exception then
      if sqlerrm like 'NOT_ALLOWED%' then
        raise notice 'PASS % (refused: %)', p_label, sqlerrm;
        return;
      end if;
      raise;  -- some other error: show it, the test is broken
  end;
  if v_rows <> 0 then
    raise exception 'FAIL %: the change went through (% row(s))', p_label, v_rows;
  end if;
  raise notice 'PASS % (0 rows changed)', p_label;
end;
$$;

-- PASS if a change that this role IS allowed to make changes exactly p_expected rows.
create function pg_temp.expect_allowed(p_label text, p_sql text, p_expected bigint default 1)
returns void
language plpgsql
as $$
declare
  v_rows bigint;
begin
  execute p_sql;
  get diagnostics v_rows = row_count;
  if v_rows <> p_expected then
    raise exception 'FAIL %: expected % row(s) changed, got %', p_label, p_expected, v_rows;
  end if;
  raise notice 'PASS %', p_label;
end;
$$;

-- ---------------------------------------------------------------- test 0: RLS everywhere (as postgres)
do $$
declare
  v_missing text;
begin
  select string_agg(c.relname, ', ' order by c.relname) into v_missing
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public'
     and c.relkind in ('r', 'p')      -- normal and partitioned tables
     and not c.relrowsecurity;
  if v_missing is not null then
    raise exception 'FAIL test 0: RLS is OFF for: %', v_missing;
  end if;
  raise notice 'PASS test 0: RLS is enabled on every public table';
end;
$$;

-- ---------------------------------------------------------------- setup (as postgres)
-- Four fake users. Inserting into auth.users fires our sign-up trigger, which creates
-- each profile as a customer with 50 XP and the First Step badge.
insert into auth.users (id, email, raw_user_meta_data, aud, role)
values
  ('00000000-0000-4000-8000-00000000a001', 'rls-test-a@skillforge.test',     '{"display_name":"RLS Customer A"}', 'authenticated', 'authenticated'),
  ('00000000-0000-4000-8000-00000000b002', 'rls-test-b@skillforge.test',     '{"display_name":"RLS Customer B"}', 'authenticated', 'authenticated'),
  ('00000000-0000-4000-8000-00000000c003', 'rls-test-staff@skillforge.test', '{"display_name":"RLS Staff"}',      'authenticated', 'authenticated'),
  ('00000000-0000-4000-8000-00000000d004', 'rls-test-owner@skillforge.test', '{"display_name":"RLS Owner"}',      'authenticated', 'authenticated');

-- Roles are set here as postgres, exactly like the trainer does in demo-accounts.md.
update public.profiles set role = 'staff' where id = '00000000-0000-4000-8000-00000000c003';
update public.profiles set role = 'owner' where id = '00000000-0000-4000-8000-00000000d004';

do $$
declare
  v_cat_id bigint;
begin
  insert into public.categories (name, icon, sort_order)
  values ('RLS Test Category (rolled back)', '🧪', 99)
  returning id into v_cat_id;

  -- Two published courses and one unpublished draft.
  insert into public.courses (slug, title, summary, description, category_id, level,
                              duration_hours, price, seats_total, seats_available, is_published)
  values
    ('rls-test-published',   'RLS Test Published',   'Visible.', 'Used by the RLS test.', v_cat_id, 'Beginner', 1, 20.00, 10, 10, true),
    ('rls-test-published-2', 'RLS Test Published 2', 'Visible.', 'Used by the RLS test.', v_cat_id, 'Beginner', 1, 30.00, 10, 10, true),
    ('rls-test-draft',       'RLS Test Draft',       'Hidden.',  'Used by the RLS test.', v_cat_id, 'Beginner', 1, 40.00, 10, 10, false);

  -- One syllabus module on the draft: its "sneak peek" must not leak to guests either.
  insert into public.course_modules (course_id, position, title)
  select id, 1, 'Secret draft module' from public.courses where slug = 'rls-test-draft';
end;
$$;

-- Give A and B one real order each, made by the real checkout function.
do $$
declare
  v_course_id bigint := (select id from public.courses where slug = 'rls-test-published');
  v_user      uuid;
  v_result    jsonb;
begin
  foreach v_user in array array['00000000-0000-4000-8000-00000000a001',
                                '00000000-0000-4000-8000-00000000b002']::uuid[]
  loop
    insert into public.cart_items (user_id, course_id, quantity) values (v_user, v_course_id, 1);
    -- Pretend to be this user so auth.uid() inside place_order returns their id.
    perform set_config('request.jwt.claims',
                       json_build_object('sub', v_user, 'role', 'authenticated')::text, true);
    v_result := public.place_order(gen_random_uuid());

    -- A saved confirmation email for that order.
    insert into public.email_outbox (order_id, user_id, to_email, subject, html_body, file_name)
    values ((v_result ->> 'order_id')::bigint, v_user, 'rls-test@skillforge.test',
            'Your order is confirmed', '<p>Demo</p>', 'order_rls_test.html');

    -- Remember the order ids in settings that every role can read later.
    if v_user = '00000000-0000-4000-8000-00000000a001' then
      perform set_config('rlstest.a_order_id', v_result ->> 'order_id', true);
    else
      perform set_config('rlstest.b_order_id', v_result ->> 'order_id', true);
    end if;
  end loop;
  perform set_config('request.jwt.claims', '', true);
  -- place_order switched on its "this is checkout" flag for the rest of the transaction.
  -- Switch it off so the staff tests below behave like normal admin edits.
  perform set_config('skillforge.in_checkout', 'off', true);

  -- Both customers also have something in their cart right now (place_order emptied it).
  insert into public.cart_items (user_id, course_id, quantity)
  values ('00000000-0000-4000-8000-00000000a001', v_course_id, 1),
         ('00000000-0000-4000-8000-00000000b002', v_course_id, 1);

  raise notice 'PASS setup: 4 users, 3 courses, 2 orders, 2 emails, 2 carts';
end;
$$;

-- ================================================================ test 1: guest
set local role anon;
select set_config('request.jwt.claims', '{"role":"anon"}', true);

select pg_temp.expect_some('1.01 guest sees a published course',
  $q$select count(*) from public.courses where slug = 'rls-test-published'$q$);
select pg_temp.expect_none('1.02 guest cannot see the draft course',
  $q$select count(*) from public.courses where slug = 'rls-test-draft'$q$);
select pg_temp.expect_none('1.03 guest sees no unpublished course at all',
  $q$select count(*) from public.courses where not is_published$q$);
select pg_temp.expect_none('1.04 guest cannot see modules of a draft',
  $q$select count(*) from public.course_modules where title = 'Secret draft module'$q$);
select pg_temp.expect_none('1.05 guest sees no profiles',     $q$select count(*) from public.profiles$q$);
select pg_temp.expect_none('1.06 guest sees no cart rows',    $q$select count(*) from public.cart_items$q$);
select pg_temp.expect_none('1.07 guest sees no orders',       $q$select count(*) from public.orders$q$);
select pg_temp.expect_none('1.08 guest sees no order lines',  $q$select count(*) from public.order_items$q$);
select pg_temp.expect_none('1.09 guest sees no XP history',   $q$select count(*) from public.xp_events$q$);
select pg_temp.expect_none('1.10 guest sees no earned badges',$q$select count(*) from public.user_badges$q$);
select pg_temp.expect_none('1.11 guest sees no saved emails', $q$select count(*) from public.email_outbox$q$);
select pg_temp.expect_none('1.12 guest sees no audit log',    $q$select count(*) from public.audit_log$q$);
select pg_temp.expect_blocked('1.13 guest cannot change a price',
  $q$update public.courses set price = 0 where slug = 'rls-test-published'$q$);
select pg_temp.expect_blocked('1.14 guest cannot add to a saved cart',
  $q$insert into public.cart_items (user_id, course_id)
     select '00000000-0000-4000-8000-00000000b002', id from public.courses where slug = 'rls-test-published-2'$q$);
select pg_temp.expect_blocked('1.15 guest cannot place an order',
  $q$select public.place_order(gen_random_uuid())$q$);

reset role;

-- ================================================================ test 2: customer A
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-8000-00000000a001","role":"authenticated"}', true);

-- What A SHOULD be able to see and do (proves the test isn't passing because nothing works).
select pg_temp.expect_some('2.01 A sees own profile',
  $q$select count(*) from public.profiles where id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_some('2.02 A sees own order',
  $q$select count(*) from public.orders where id = current_setting('rlstest.a_order_id')::bigint$q$);
select pg_temp.expect_some('2.03 A sees own order lines',
  $q$select count(*) from public.order_items where order_id = current_setting('rlstest.a_order_id')::bigint$q$);
select pg_temp.expect_some('2.04 A sees own saved email',
  $q$select count(*) from public.email_outbox where user_id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_some('2.05 A sees own XP history',
  $q$select count(*) from public.xp_events where user_id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_allowed('2.06 A can rename own profile',
  $q$update public.profiles set display_name = 'RLS Customer A renamed'
      where id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_allowed('2.07 A can add a published course to own cart',
  $q$insert into public.cart_items (user_id, course_id)
     select '00000000-0000-4000-8000-00000000a001', id from public.courses where slug = 'rls-test-published-2'$q$);

-- A cannot READ B's rows.
select pg_temp.expect_none('2.10 A cannot see B''s profile',
  $q$select count(*) from public.profiles where id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_none('2.11 A cannot see B''s cart',
  $q$select count(*) from public.cart_items where user_id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_none('2.12 A cannot see B''s order',
  $q$select count(*) from public.orders where id = current_setting('rlstest.b_order_id')::bigint$q$);
select pg_temp.expect_none('2.13 A cannot see B''s order lines',
  $q$select count(*) from public.order_items where order_id = current_setting('rlstest.b_order_id')::bigint$q$);
select pg_temp.expect_none('2.14 A cannot see B''s XP history',
  $q$select count(*) from public.xp_events where user_id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_none('2.15 A cannot see B''s badges',
  $q$select count(*) from public.user_badges where user_id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_none('2.16 A cannot see B''s saved emails',
  $q$select count(*) from public.email_outbox where user_id = '00000000-0000-4000-8000-00000000b002'
                                          or order_id = current_setting('rlstest.b_order_id')::bigint$q$);
-- ... nor anybody else's (this also covers real demo data already in the database).
select pg_temp.expect_none('2.17 A sees no other profile at all',
  $q$select count(*) from public.profiles where id <> '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_none('2.18 A sees no other order at all',
  $q$select count(*) from public.orders where user_id <> '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_none('2.19 A sees no other cart row at all',
  $q$select count(*) from public.cart_items where user_id <> '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_none('2.20 A sees no other XP, badge or email row at all',
  $q$select (select count(*) from public.xp_events    where user_id <> '00000000-0000-4000-8000-00000000a001')
          + (select count(*) from public.user_badges  where user_id <> '00000000-0000-4000-8000-00000000a001')
          + (select count(*) from public.email_outbox where user_id <> '00000000-0000-4000-8000-00000000a001')$q$);
select pg_temp.expect_none('2.21 A cannot see the draft course',
  $q$select count(*) from public.courses where slug = 'rls-test-draft'$q$);
select pg_temp.expect_none('2.22 A cannot see the audit log', $q$select count(*) from public.audit_log$q$);

-- A cannot CHANGE B's rows.
select pg_temp.expect_blocked('2.30 A cannot change B''s cart quantity',
  $q$update public.cart_items set quantity = 5 where user_id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_blocked('2.31 A cannot empty B''s cart',
  $q$delete from public.cart_items where user_id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_blocked('2.32 A cannot add to B''s cart',
  $q$insert into public.cart_items (user_id, course_id)
     select '00000000-0000-4000-8000-00000000b002', id from public.courses where slug = 'rls-test-published-2'$q$);
select pg_temp.expect_blocked('2.33 A cannot cancel B''s order',
  $q$update public.orders set status = 'cancelled' where id = current_setting('rlstest.b_order_id')::bigint$q$);
select pg_temp.expect_blocked('2.34 A cannot delete B''s order',
  $q$delete from public.orders where id = current_setting('rlstest.b_order_id')::bigint$q$);
select pg_temp.expect_blocked('2.35 A cannot change B''s order lines',
  $q$update public.order_items set quantity = 5 where order_id = current_setting('rlstest.b_order_id')::bigint$q$);
select pg_temp.expect_blocked('2.36 A cannot rename B''s profile',
  $q$update public.profiles set display_name = 'Hacked' where id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_blocked('2.37 A cannot delete B''s XP history',
  $q$delete from public.xp_events where user_id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_blocked('2.38 A cannot delete B''s badges',
  $q$delete from public.user_badges where user_id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_blocked('2.39 A cannot change B''s saved email',
  $q$update public.email_outbox set subject = 'Hacked' where user_id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_blocked('2.40 A cannot save an email for B''s order (as B)',
  $q$insert into public.email_outbox (order_id, user_id, to_email, subject, html_body, file_name)
     values (current_setting('rlstest.b_order_id')::bigint, '00000000-0000-4000-8000-00000000b002',
             'x@skillforge.test', 'Fake', '<p>x</p>', 'fake.html')$q$);
select pg_temp.expect_blocked('2.41 A cannot save an email for B''s order (as A)',
  $q$insert into public.email_outbox (order_id, user_id, to_email, subject, html_body, file_name)
     values (current_setting('rlstest.b_order_id')::bigint, '00000000-0000-4000-8000-00000000a001',
             'x@skillforge.test', 'Fake', '<p>x</p>', 'fake.html')$q$);

-- Welcome email drafts (migration 0030): only for yourself, to your own address, once.
select pg_temp.expect_allowed('2.42 A can save their own welcome email draft',
  $q$insert into public.email_outbox (email_type, user_id, to_email, subject, html_body, file_name)
     values ('welcome', '00000000-0000-4000-8000-00000000a001', 'rls-test-a@skillforge.test',
             'Welcome', '<p>Hi</p>', 'welcome_rls_a.html')$q$);
do $$
begin
  insert into public.email_outbox (email_type, user_id, to_email, subject, html_body, file_name)
  values ('welcome', '00000000-0000-4000-8000-00000000a001', 'rls-test-a@skillforge.test',
          'Welcome again', '<p>Hi</p>', 'welcome_rls_a2.html');
  raise exception 'FAIL 2.43: a second welcome email was saved';
exception when unique_violation then
  raise notice 'PASS 2.43 A cannot save a second welcome email (refused: %)', sqlerrm;
end;
$$;
select pg_temp.expect_blocked('2.44 A cannot save a welcome email for B',
  $q$insert into public.email_outbox (email_type, user_id, to_email, subject, html_body, file_name)
     values ('welcome', '00000000-0000-4000-8000-00000000b002', 'rls-test-b@skillforge.test',
             'Fake', '<p>x</p>', 'fake.html')$q$);
select pg_temp.expect_blocked('2.45 A cannot send their welcome email to another address',
  $q$insert into public.email_outbox (email_type, user_id, to_email, subject, html_body, file_name)
     values ('welcome', '00000000-0000-4000-8000-00000000a001', 'someone-else@skillforge.test',
             'Fake', '<p>x</p>', 'fake.html')$q$);

-- A cannot raise their own role, XP or level.
select pg_temp.expect_blocked('2.50 A cannot make themselves staff',
  $q$update public.profiles set role = 'staff' where id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_blocked('2.51 A cannot make themselves owner',
  $q$update public.profiles set role = 'owner' where id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_blocked('2.52 A cannot change own XP',
  $q$update public.profiles set xp_total = 99999 where id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_blocked('2.53 A cannot change own level',
  $q$update public.profiles set level = 5 where id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_blocked('2.54 A cannot change own email copy',
  $q$update public.profiles set email = 'other@skillforge.test' where id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_blocked('2.55 A cannot give themselves XP',
  $q$insert into public.xp_events (user_id, action, points, reference_id)
     values ('00000000-0000-4000-8000-00000000a001', 'complete_path', 1000, 999)$q$);
select pg_temp.expect_blocked('2.56 A cannot give themselves a badge',
  $q$insert into public.user_badges (user_id, badge_code)
     values ('00000000-0000-4000-8000-00000000a001', 'collector')$q$);
select pg_temp.expect_blocked('2.57 A cannot call the private XP function',
  $q$select private.award_xp('00000000-0000-4000-8000-00000000a001', 'complete_path', 1000, 998)$q$);

-- A cannot skip checkout or touch the catalog.
select pg_temp.expect_blocked('2.60 A cannot insert an order directly',
  $q$insert into public.orders (user_id, idempotency_key, total)
     values ('00000000-0000-4000-8000-00000000a001', gen_random_uuid(), 0)$q$);
select pg_temp.expect_blocked('2.61 A cannot insert order lines directly',
  $q$insert into public.order_items (order_id, course_id, title_snapshot, unit_price, quantity)
     select current_setting('rlstest.a_order_id')::bigint, id, title, 0, 5
       from public.courses where slug = 'rls-test-published-2'$q$);
select pg_temp.expect_blocked('2.62 A cannot cancel own order (staff only)',
  $q$update public.orders set status = 'cancelled' where id = current_setting('rlstest.a_order_id')::bigint$q$);
select pg_temp.expect_blocked('2.63 A cannot change seats',
  $q$update public.courses set seats_available = 0 where slug = 'rls-test-published'$q$);
select pg_temp.expect_blocked('2.64 A cannot change a price',
  $q$update public.courses set price = 0 where slug = 'rls-test-published'$q$);
select pg_temp.expect_blocked('2.65 A cannot publish a draft',
  $q$update public.courses set is_published = true where slug = 'rls-test-draft'$q$);
select pg_temp.expect_blocked('2.66 A cannot create a course',
  $q$insert into public.courses (slug, title, summary, description, category_id, level,
                                 duration_hours, price, seats_total, seats_available)
     select 'rls-test-by-customer', 'X', 'X', 'X', id, 'Beginner', 1, 1, 1, 1
       from public.categories where name = 'RLS Test Category (rolled back)'$q$);
select pg_temp.expect_blocked('2.67 A cannot delete a course',
  $q$delete from public.courses where slug = 'rls-test-published-2'$q$);
select pg_temp.expect_blocked('2.68 A cannot write to the audit log',
  $q$select public.write_audit_log('fake', 'course', '1')$q$);

-- ================================================================ test 3: staff
select set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-8000-00000000c003","role":"authenticated"}', true);

select pg_temp.expect_some('3.01 staff sees the draft course',
  $q$select count(*) from public.courses where slug = 'rls-test-draft'$q$);
select pg_temp.expect_some('3.02 staff sees A''s order',
  $q$select count(*) from public.orders where id = current_setting('rlstest.a_order_id')::bigint$q$);
select pg_temp.expect_some('3.03 staff sees B''s order',
  $q$select count(*) from public.orders where id = current_setting('rlstest.b_order_id')::bigint$q$);
select pg_temp.expect_some('3.04 staff sees B''s order lines',
  $q$select count(*) from public.order_items where order_id = current_setting('rlstest.b_order_id')::bigint$q$);
select pg_temp.expect_some('3.05 staff sees B''s saved email',
  $q$select count(*) from public.email_outbox where order_id = current_setting('rlstest.b_order_id')::bigint$q$);
select pg_temp.expect_some('3.06 staff sees customer profiles (to know who ordered)',
  $q$select count(*) from public.profiles where id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_allowed('3.07 staff can create a course',
  $q$insert into public.courses (slug, title, summary, description, category_id, level,
                                 duration_hours, price, seats_total, seats_available)
     select 'rls-test-by-staff', 'Made by staff', 'X', 'X', id, 'Beginner', 1, 10, 5, 5
       from public.categories where name = 'RLS Test Category (rolled back)'$q$);
select pg_temp.expect_allowed('3.08 staff can change a price',
  $q$update public.courses set price = 25.00 where slug = 'rls-test-published'$q$);
select pg_temp.expect_allowed('3.09 staff can adjust seats',
  $q$update public.courses set seats_total = 12, seats_available = seats_available + 2
      where slug = 'rls-test-published'$q$);
select pg_temp.expect_allowed('3.10 staff can publish a draft',
  $q$update public.courses set is_published = true where slug = 'rls-test-draft'$q$);
select pg_temp.expect_allowed('3.11 staff can unpublish it again',
  $q$update public.courses set is_published = false where slug = 'rls-test-draft'$q$);
select pg_temp.expect_allowed('3.12 staff can cancel B''s order (US-408)',
  $q$update public.orders set status = 'cancelled' where id = current_setting('rlstest.b_order_id')::bigint$q$);

select pg_temp.expect_blocked('3.20 staff cannot make a customer staff',
  $q$update public.profiles set role = 'staff' where id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_blocked('3.21 staff cannot make themselves owner',
  $q$update public.profiles set role = 'owner' where id = '00000000-0000-4000-8000-00000000c003'$q$);
select pg_temp.expect_blocked('3.22 staff cannot change own role at all',
  $q$update public.profiles set role = 'customer' where id = '00000000-0000-4000-8000-00000000c003'$q$);
select pg_temp.expect_blocked('3.23 staff cannot rename a customer',
  $q$update public.profiles set display_name = 'Renamed' where id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_blocked('3.24 staff cannot change a customer''s XP',
  $q$update public.profiles set xp_total = 0 where id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_blocked('3.25 staff cannot delete a course',
  $q$delete from public.courses where slug = 'rls-test-draft'$q$);
select pg_temp.expect_blocked('3.26 staff cannot delete a category',
  $q$delete from public.categories where name = 'RLS Test Category (rolled back)'$q$);
select pg_temp.expect_blocked('3.27 staff cannot insert an order directly',
  $q$insert into public.orders (user_id, idempotency_key)
     values ('00000000-0000-4000-8000-00000000c003', gen_random_uuid())$q$);
select pg_temp.expect_blocked('3.28 staff cannot delete an order',
  $q$delete from public.orders where id = current_setting('rlstest.a_order_id')::bigint$q$);
select pg_temp.expect_blocked('3.29 staff cannot change an order total',
  $q$update public.orders set total = 0 where id = current_setting('rlstest.a_order_id')::bigint$q$);

-- ================================================================ test 4: owner
select set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-8000-00000000d004","role":"authenticated"}', true);

select pg_temp.expect_allowed('4.01 owner can promote a customer to staff',
  $q$update public.profiles set role = 'staff' where id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_allowed('4.02 owner can demote staff to customer',
  $q$update public.profiles set role = 'customer' where id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_blocked('4.03 owner cannot make another owner from the app (trainer job)',
  $q$update public.profiles set role = 'owner' where id = '00000000-0000-4000-8000-00000000c003'$q$);
select pg_temp.expect_blocked('4.04 owner cannot change a customer''s XP',
  $q$update public.profiles set xp_total = 0 where id = '00000000-0000-4000-8000-00000000b002'$q$);
select pg_temp.expect_some('4.05 owner sees the audit log (role changes were recorded)',
  $q$select count(*) from public.audit_log
      where action = 'role_change' and entity_id = '00000000-0000-4000-8000-00000000a001'$q$);
select pg_temp.expect_allowed('4.06 owner can delete a course that was never sold',
  $q$delete from public.courses where slug = 'rls-test-draft'$q$);

-- A course that has been sold is protected by a foreign key, even for the owner (NFR-DATA-05).
do $$
begin
  begin
    delete from public.courses where slug = 'rls-test-published';
    raise exception 'FAIL 4.07: the owner deleted a course that has orders';
  exception when foreign_key_violation then
    null;  -- expected
  end;
  raise notice 'PASS 4.07 a sold course cannot be deleted (unpublish it instead)';
end;
$$;

reset role;

-- ================================================================ test 5: nothing leaked through (as postgres)
-- "0 rows changed" above already proves it; this double-checks the real values.
do $$
begin
  if (select quantity from public.cart_items
       where user_id = '00000000-0000-4000-8000-00000000b002'
         and course_id = (select id from public.courses where slug = 'rls-test-published')) <> 1 then
    raise exception 'FAIL 5.01: B''s cart was changed';
  end if;
  if (select display_name from public.profiles where id = '00000000-0000-4000-8000-00000000b002')
       <> 'RLS Customer B' then
    raise exception 'FAIL 5.02: B''s profile was changed';
  end if;
  if not exists (select 1 from public.orders where id = current_setting('rlstest.b_order_id')::bigint) then
    raise exception 'FAIL 5.03: B''s order disappeared';
  end if;
  if (select role from public.profiles where id = '00000000-0000-4000-8000-00000000a001') <> 'customer' then
    raise exception 'FAIL 5.04: A''s role is not customer';
  end if;
  if (select xp_total from public.profiles where id = '00000000-0000-4000-8000-00000000a001')
       <> (select sum(points) from public.xp_events where user_id = '00000000-0000-4000-8000-00000000a001') then
    raise exception 'FAIL 5.05: A''s XP total does not match their XP history';
  end if;
  if (select price from public.courses where slug = 'rls-test-published') <> 25.00 then
    raise exception 'FAIL 5.06: price is not the 25.00 that staff set';
  end if;
  if (select role from public.profiles where id = '00000000-0000-4000-8000-00000000c003') <> 'staff' then
    raise exception 'FAIL 5.07: staff role was changed';
  end if;
  raise notice 'PASS test 5: other users'' data is unchanged';
  raise notice 'ALL RLS CHECKS PASSED';
end;
$$;

-- Throw away everything this test created.
rollback;
