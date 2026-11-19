-- 0014_place_order.sql
-- The one "all or nothing" action: checkout (US-403, US-404, US-601 to US-603, NFR-DATA-01 to 04).
--
-- A Postgres function runs inside ONE transaction. If any step raises an error, EVERYTHING
-- in it is undone: no order, no seats taken, cart untouched, no XP. That is what keeps the
-- shop honest when two people buy the last seat at the same moment.
--
-- How the app calls it (supabase-py):
--   client.rpc("place_order", {"p_idempotency_key": "<uuid made once per checkout attempt>"}).execute()
-- Returns jsonb:
--   { order_id, order_number, total, xp_awarded, new_level, level_up, new_badges, already_existed }
-- Errors (message starts with one of these, so the app can show friendly text):
--   NOT_SIGNED_IN | INVALID_REQUEST | CART_EMPTY | COURSE_UNAVAILABLE: <title> | NOT_ENOUGH_SEATS: <title>
--   For NOT_ENOUGH_SEATS the error DETAIL is 'seats_available=<n>' (US-404 AC1).

create or replace function public.place_order(p_idempotency_key uuid)
returns jsonb
language plpgsql
-- Runs with the owner's rights so it can write orders, seats and XP, which customers cannot
-- touch directly. It therefore checks auth.uid() itself and only ever uses the caller's own cart.
security definer
set search_path = ''
as $$
declare
  v_user_id       uuid := (select auth.uid());
  v_level_before  integer;
  v_existing      public.orders%rowtype;
  v_item          record;
  v_path          record;
  v_order_id      bigint;
  v_order_number  text;
  v_total         numeric(10,2);
  v_xp            integer := 0;
  v_new_badges    text[] := '{}';
  v_owned_count   integer;
  v_new_level     integer;
begin
  -- 1. Who is buying? Never trust a user id sent by the app.
  if v_user_id is null then
    raise exception 'NOT_SIGNED_IN';
  end if;
  if p_idempotency_key is null then
    raise exception 'INVALID_REQUEST: an idempotency key is required';
  end if;

  -- 2. Lock this user's profile row. A double click sends two calls; the second one waits here
  --    until the first has finished, then sees the finished order in step 3.
  select level into v_level_before
    from public.profiles
   where id = v_user_id
     for update;
  if not found then
    raise exception 'NOT_SIGNED_IN';
  end if;

  -- 3. Same key as before? Then this checkout already happened: return that order, create nothing.
  select * into v_existing
    from public.orders
   where user_id = v_user_id
     and idempotency_key = p_idempotency_key;
  if found then
    return jsonb_build_object(
      'order_id',        v_existing.id,
      'order_number',    v_existing.order_number,
      'total',           v_existing.total,
      'xp_awarded',      v_existing.xp_awarded,
      'new_level',       v_level_before,
      'level_up',        false,
      'new_badges',      to_jsonb(v_existing.badges_awarded),
      'already_existed', true
    );
  end if;

  -- 4. Nothing to buy?
  if not exists (select 1 from public.cart_items where user_id = v_user_id) then
    raise exception 'CART_EMPTY';
  end if;

  -- Tell the course triggers "this is checkout" (not an admin edit) for this transaction only.
  perform set_config('skillforge.in_checkout', 'on', true);

  -- 5. Lock the course rows in the cart, ALWAYS in id order. Two checkouts that lock in the same
  --    order can't wait for each other in a circle (no deadlock). Other buyers of the same course
  --    now wait until we commit, so they will see the seats we take.
  perform 1
     from public.courses c
    where c.id in (select ci.course_id from public.cart_items ci where ci.user_id = v_user_id)
    order by c.id
      for update;

  -- 6. Check every line with fresh, locked data (prices and seats come from the database, never the app).
  for v_item in
    select c.id, c.title, c.is_published, c.seats_available, ci.quantity
      from public.cart_items ci
      join public.courses c on c.id = ci.course_id
     where ci.user_id = v_user_id
     order by c.id
  loop
    if not v_item.is_published then
      raise exception 'COURSE_UNAVAILABLE: %', v_item.title;
    end if;
    if v_item.seats_available < v_item.quantity then
      raise exception 'NOT_ENOUGH_SEATS: %', v_item.title
        using detail = format('seats_available=%s', v_item.seats_available);
    end if;
  end loop;

  -- 7. Create the order (order_number comes from the column default, e.g. ORD-20261115-0042).
  insert into public.orders (user_id, status, idempotency_key)
  values (v_user_id, 'confirmed', p_idempotency_key)
  returning id, order_number into v_order_id, v_order_number;

  -- 8. Order lines with a snapshot of title and price (later course edits won't change this order).
  insert into public.order_items (order_id, course_id, title_snapshot, unit_price, quantity)
  select v_order_id, c.id, c.title, c.price, ci.quantity
    from public.cart_items ci
    join public.courses c on c.id = ci.course_id
   where ci.user_id = v_user_id;

  select coalesce(sum(unit_price * quantity), 0) into v_total
    from public.order_items
   where order_id = v_order_id;

  -- 9. Take the seats. The CHECK (seats_available >= 0) is a final safety net under step 6.
  update public.courses c
     set seats_available = c.seats_available - ci.quantity
    from public.cart_items ci
   where ci.user_id = v_user_id
     and c.id = ci.course_id;

  -- 10. XP per course (not per seat), only the first time this user buys that course (US-601).
  for v_item in
    select c.id, c.xp_reward
      from public.cart_items ci
      join public.courses c on c.id = ci.course_id
     where ci.user_id = v_user_id
     order by c.id
  loop
    v_xp := v_xp + private.award_xp(v_user_id, 'purchase_course', v_item.xp_reward, v_item.id);
  end loop;

  -- 11. Badges (US-603). award_badge returns true only when the badge is new.
  if private.award_badge(v_user_id, 'first_unlock') then
    v_new_badges := array_append(v_new_badges, 'first_unlock'::text);
  end if;

  -- "Owned" = in any confirmed order of this user (this new order included).
  select count(distinct oi.course_id) into v_owned_count
    from public.order_items oi
    join public.orders o on o.id = oi.order_id
   where o.user_id = v_user_id
     and o.status = 'confirmed';

  if v_owned_count >= 5 and private.award_badge(v_user_id, 'collector') then
    v_new_badges := array_append(v_new_badges, 'collector'::text);
  end if;

  if exists (
       select 1
         from public.learning_path_courses lpc
         join public.order_items oi on oi.course_id = lpc.course_id
         join public.orders o on o.id = oi.order_id
        where o.user_id = v_user_id and o.status = 'confirmed'
     ) and private.award_badge(v_user_id, 'path_starter') then
    v_new_badges := array_append(v_new_badges, 'path_starter'::text);
  end if;

  -- Completed paths: the path has courses, and none of them is missing from what the user owns.
  for v_path in
    select lp.id, lp.bonus_xp, lp.badge_code
      from public.learning_paths lp
     where exists (select 1 from public.learning_path_courses x where x.path_id = lp.id)
       and not exists (
             select 1
               from public.learning_path_courses lpc
              where lpc.path_id = lp.id
                and not exists (
                      select 1
                        from public.order_items oi
                        join public.orders o on o.id = oi.order_id
                       where o.user_id = v_user_id
                         and o.status = 'confirmed'
                         and oi.course_id = lpc.course_id
                    )
           )
     order by lp.id
  loop
    v_xp := v_xp + private.award_xp(v_user_id, 'complete_path', v_path.bonus_xp, v_path.id);
    if v_path.badge_code is not null and private.award_badge(v_user_id, v_path.badge_code) then
      v_new_badges := array_append(v_new_badges, v_path.badge_code::text);
    end if;
  end loop;

  -- 12. Empty the cart: those courses are bought now.
  delete from public.cart_items where user_id = v_user_id;

  -- 13. Save the totals on the order, so a repeat call (step 3) and the email show the same numbers.
  update public.orders
     set total = v_total,
         xp_awarded = v_xp,
         badges_awarded = v_new_badges
   where id = v_order_id;

  select level into v_new_level from public.profiles where id = v_user_id;

  return jsonb_build_object(
    'order_id',        v_order_id,
    'order_number',    v_order_number,
    'total',           v_total,
    'xp_awarded',      v_xp,
    'new_level',       v_new_level,
    'level_up',        v_new_level > v_level_before,
    'new_badges',      to_jsonb(v_new_badges),
    'already_existed', false
  );
end;
$$;

-- Only signed-in users may call it. Supabase grants new functions to anon by default, so remove that.
revoke execute on function public.place_order(uuid) from public, anon;
grant execute on function public.place_order(uuid) to authenticated;
