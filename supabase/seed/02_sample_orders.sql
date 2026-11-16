-- supabase/seed/02_sample_orders.sql
-- A few sample orders for the demo customers, so "My Orders", the admin orders list and the
-- dashboard are not empty on day one.
--
-- Run AFTER 01_catalog.sql AND after creating the demo users (docs/deployment/demo-accounts.md).
-- Users are looked up by email, never by a hard-coded id. If a demo user doesn't exist yet,
-- their orders are skipped with a NOTICE instead of failing.
-- Orders are created through the real public.place_order function, so seats, XP and badges
-- follow exactly the same rules as in the app. Each sample order has a fixed idempotency key,
-- so running this file twice does NOT create duplicate orders.
--
-- If you used different demo emails, change them in the list at the bottom of this file.

begin;

create temporary table seed_sample_orders (
  email            text,
  idempotency_key  uuid,
  course_slug      text,
  quantity         integer
) on commit drop;

insert into seed_sample_orders values
  -- Demo customer: two orders.
  ('customer@skillforge.example', '5eed0000-0000-4000-8000-000000000001', 'python-for-data-beginners', 1),
  ('customer@skillforge.example', '5eed0000-0000-4000-8000-000000000001', 'sql-for-analysts',          2),
  ('customer@skillforge.example', '5eed0000-0000-4000-8000-000000000002', 'prompt-engineering-fundamentals', 1),
  -- Optional second demo customer: one order.
  ('learner2@skillforge.example', '5eed0000-0000-4000-8000-000000000003', 'intro-to-machine-learning', 1);

do $$
declare
  v_order   record;
  v_user_id uuid;
  v_result  jsonb;
begin
  for v_order in
    select distinct email, idempotency_key from seed_sample_orders order by idempotency_key
  loop
    select id into v_user_id from public.profiles where lower(email) = lower(v_order.email);

    if v_user_id is null then
      raise notice 'Skipping sample order %: no demo user with email % yet.', v_order.idempotency_key, v_order.email;
      continue;
    end if;

    if exists (select 1 from public.orders
                where user_id = v_user_id and idempotency_key = v_order.idempotency_key) then
      raise notice 'Sample order % already exists, skipping.', v_order.idempotency_key;
      continue;
    end if;

    -- Start from an empty cart, then fill it with this sample order's lines.
    delete from public.cart_items where user_id = v_user_id;
    insert into public.cart_items (user_id, course_id, quantity)
    select v_user_id, c.id, s.quantity
      from seed_sample_orders s
      join public.courses c on c.slug = s.course_slug
     where s.idempotency_key = v_order.idempotency_key;

    -- Pretend to be this user for the rest of the transaction, so auth.uid() inside
    -- place_order returns their id (this is how Supabase passes the signed-in user).
    perform set_config('request.jwt.claims',
                       json_build_object('sub', v_user_id, 'role', 'authenticated')::text, true);

    v_result := public.place_order(v_order.idempotency_key);
    raise notice 'Created sample order % for %', v_result ->> 'order_number', v_order.email;
  end loop;

  -- Stop pretending.
  perform set_config('request.jwt.claims', '', true);
end;
$$;

commit;
