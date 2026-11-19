-- supabase/tests/place_order_test.sql
-- Proves that public.place_order:
--   1. refuses a guest (NOT_SIGNED_IN),
--   2. cannot over-book (asking for more seats than exist fails and changes nothing),
--   3. sells the last seats correctly,
--   4. cannot run twice for the same idempotency key (second call returns the same order),
--   5. refuses another buyer once seats are gone (NOT_ENOUGH_SEATS),
--   6. and the database itself blocks negative seats (CHECK constraint).
--
-- How to run: paste the whole file into the Supabase SQL editor (DEV project only) and click Run,
-- or: psql "$DEV_DB_URL" -v ON_ERROR_STOP=1 -f supabase/tests/place_order_test.sql
-- Plain SQL, no extensions needed. Everything happens inside one transaction that ends with
-- ROLLBACK, so no test users, courses or orders are left behind.
-- Passing = you see "PASS" notices and no ERROR. Any failed check raises an ERROR starting with "FAIL".

begin;

-- ---------------------------------------------------------------- setup (as postgres)
-- Two fake users. Inserting into auth.users fires our trigger, which creates their profiles.
insert into auth.users (id, email, raw_user_meta_data, aud, role)
values
  ('00000000-0000-4000-8000-0000000000a1', 'test-buyer-a@skillforge.test', '{"display_name":"Buyer A"}', 'authenticated', 'authenticated'),
  ('00000000-0000-4000-8000-0000000000b2', 'test-buyer-b@skillforge.test', '{"display_name":"Buyer B"}', 'authenticated', 'authenticated');

do $$
declare
  v_cat_id bigint;
begin
  insert into public.categories (name, icon, sort_order)
  values ('Test Category (rolled back)', '🧪', 99)
  returning id into v_cat_id;

  -- A published course with exactly 2 seats.
  insert into public.courses (slug, title, summary, description, category_id, level,
                              duration_hours, price, seats_total, seats_available, is_published)
  values ('test-two-seat-course', 'Test Two-Seat Course', 'Only two seats.', 'Used by the test.',
          v_cat_id, 'Beginner', 1, 10.00, 2, 2, true);

  -- Profiles were created by the sign-up trigger.
  if (select count(*) from public.profiles
       where id in ('00000000-0000-4000-8000-0000000000a1', '00000000-0000-4000-8000-0000000000b2')
         and role = 'customer') <> 2 then
    raise exception 'FAIL setup: sign-up trigger did not create two customer profiles';
  end if;
  raise notice 'PASS setup: sign-up trigger created customer profiles';
end;
$$;

-- ---------------------------------------------------------------- test 1: guest
-- Act like a guest: the "anon" role and no user in the token.
set local role anon;
select set_config('request.jwt.claims', '{"role":"anon"}', true);

do $$
begin
  begin
    perform public.place_order(gen_random_uuid());
    raise exception 'FAIL test 1: a guest was able to call place_order';
  exception when others then
    -- anon has no EXECUTE right at all, or the function itself says NOT_SIGNED_IN: both are a pass.
    if sqlerrm not like 'NOT_SIGNED_IN%' and sqlerrm not like 'permission denied%' then
      raise;
    end if;
  end;
  raise notice 'PASS test 1: guests cannot place orders';
end;
$$;

reset role;

-- ---------------------------------------------------------------- tests 2-4: buyer A
-- Act like signed-in Buyer A, exactly as the app's requests do.
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-8000-0000000000a1","role":"authenticated"}', true);

do $$
declare
  v_course_id bigint := (select id from public.courses where slug = 'test-two-seat-course');
  v_key       uuid := '00000000-0000-4000-8000-00000000c0de';
  v_first     jsonb;
  v_second    jsonb;
begin
  -- Test 2: ask for 3 seats when only 2 exist.
  insert into public.cart_items (user_id, course_id, quantity)
  values ('00000000-0000-4000-8000-0000000000a1', v_course_id, 3);

  begin
    perform public.place_order(gen_random_uuid());
    raise exception 'FAIL test 2: over-booking was allowed';
  exception when others then
    if sqlerrm not like 'NOT_ENOUGH_SEATS: Test Two-Seat Course%' then
      raise;
    end if;
  end;

  if (select seats_available from public.courses where id = v_course_id) <> 2 then
    raise exception 'FAIL test 2: seats changed after a failed order';
  end if;
  if exists (select 1 from public.orders) then
    raise exception 'FAIL test 2: an order row was created by a failed checkout';
  end if;
  if not exists (select 1 from public.cart_items where course_id = v_course_id) then
    raise exception 'FAIL test 2: the cart was cleared by a failed checkout';
  end if;
  raise notice 'PASS test 2: cannot over-book, and nothing changed';

  -- Test 3: ask for exactly the 2 seats left.
  update public.cart_items set quantity = 2 where course_id = v_course_id;
  v_first := public.place_order(v_key);

  if (v_first ->> 'already_existed')::boolean then
    raise exception 'FAIL test 3: first call said already_existed';
  end if;
  if (select seats_available from public.courses where id = v_course_id) <> 0 then
    raise exception 'FAIL test 3: seats were not deducted to 0';
  end if;
  if (v_first ->> 'total')::numeric <> 20.00 then
    raise exception 'FAIL test 3: expected total 20.00, got %', v_first ->> 'total';
  end if;
  if exists (select 1 from public.cart_items) then
    raise exception 'FAIL test 3: cart was not cleared';
  end if;
  if (v_first ->> 'xp_awarded')::int <> 100 then
    raise exception 'FAIL test 3: expected 100 XP for one course, got %', v_first ->> 'xp_awarded';
  end if;
  raise notice 'PASS test 3: order % placed, seats now 0', v_first ->> 'order_number';

  -- Test 4: same key again (double click). Must return the SAME order and create nothing.
  v_second := public.place_order(v_key);

  if not (v_second ->> 'already_existed')::boolean then
    raise exception 'FAIL test 4: second call did not report already_existed';
  end if;
  if v_second ->> 'order_id' <> v_first ->> 'order_id' then
    raise exception 'FAIL test 4: second call returned a different order';
  end if;
  if (select count(*) from public.orders) <> 1 then
    raise exception 'FAIL test 4: expected exactly 1 order, found %', (select count(*) from public.orders);
  end if;
  if (select xp_total from public.profiles where id = '00000000-0000-4000-8000-0000000000a1') <> 150 then
    -- 50 for registering + 100 for the course; the repeat call must not add more.
    raise exception 'FAIL test 4: XP was awarded twice';
  end if;
  raise notice 'PASS test 4: same idempotency key returns the same order, no duplicate';
end;
$$;

-- ---------------------------------------------------------------- test 5: buyer B, sold out
select set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-8000-0000000000b2","role":"authenticated"}', true);

do $$
declare
  v_course_id bigint := (select id from public.courses where slug = 'test-two-seat-course');
begin
  insert into public.cart_items (user_id, course_id, quantity)
  values ('00000000-0000-4000-8000-0000000000b2', v_course_id, 1);

  begin
    perform public.place_order(gen_random_uuid());
    raise exception 'FAIL test 5: sold a seat that does not exist';
  exception when others then
    if sqlerrm not like 'NOT_ENOUGH_SEATS:%' then
      raise;
    end if;
  end;
  raise notice 'PASS test 5: a second buyer cannot take seats that are gone';
end;
$$;

reset role;

-- ---------------------------------------------------------------- test 6: the constraint itself
do $$
begin
  begin
    update public.courses set seats_available = -1 where slug = 'test-two-seat-course';
    raise exception 'FAIL test 6: seats_available went below 0';
  exception when check_violation then
    null;  -- expected: the CHECK constraint stopped it
  end;
  raise notice 'PASS test 6: the database refuses negative seats';
end;
$$;

-- Throw away everything this test created.
rollback;
