-- 0007_orders.sql
-- Orders and their lines. Rows are only created by public.place_order (migration 0014).
-- Doc 00 section 6, US-403 to US-408, NFR-DATA-01 to NFR-DATA-05.

-- A counter used to build readable order numbers like ORD-20261115-0042 (US-405 AC1).
-- A sequence never hands out the same number twice, even when two orders happen at once.
create sequence public.order_number_seq start 1;

create table public.orders (
  id               bigint generated always as identity primary key,
  order_number     text not null unique
                   default ('ORD-' || to_char(now() at time zone 'utc', 'YYYYMMDD') || '-'
                            || lpad(nextval('public.order_number_seq')::text, 4, '0')),
  user_id          uuid not null references public.profiles (id) on delete cascade,
  status           text not null default 'confirmed' check (status in ('confirmed', 'cancelled')),
  total            numeric(10,2) not null default 0 check (total >= 0),
  -- A random id the app makes once per checkout attempt. Same key again = same order (NFR-DATA-04).
  idempotency_key  uuid not null,
  -- What this order earned, saved so a repeated call and the confirmation email show the same numbers.
  xp_awarded       integer not null default 0 check (xp_awarded >= 0),
  badges_awarded   text[] not null default '{}',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint orders_user_idempotency_key unique (user_id, idempotency_key)
);

-- "My orders, newest first" (US-407, NFR-PERF-06). Also serves the user_id foreign key.
create index orders_user_id_created_at_idx on public.orders (user_id, created_at desc);
-- Staff order list filters by date and status (US-707, US-708).
create index orders_created_at_idx on public.orders (created_at desc);
create index orders_status_idx on public.orders (status);

create trigger orders_set_updated_at
  before update on public.orders
  for each row execute function public.set_updated_at();

create table public.order_items (
  order_id        bigint not null references public.orders (id) on delete cascade,
  -- "restrict": a course that has been sold cannot be hard-deleted, only unpublished (NFR-DATA-05).
  course_id       bigint not null references public.courses (id) on delete restrict,
  -- Copies taken at purchase time, so later edits to the course don't change old orders (NFR-DATA-03).
  title_snapshot  text not null,
  unit_price      numeric(10,2) not null check (unit_price >= 0),
  quantity        integer not null check (quantity between 1 and 5),
  primary key (order_id, course_id)
);
-- Foreign key index for course_id (dashboard "top courses by seats sold", US-708).
create index order_items_course_id_idx on public.order_items (course_id);

-- Guard for updates coming from the app (staff cancelling an order, US-408).
-- Column privileges (migration 0012) already limit the app to the "status" column;
-- this trigger adds the business rule: confirmed -> cancelled only, never back.
create or replace function public.orders_guard_status_change()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.status is distinct from old.status then
    if old.status = 'cancelled' then
      raise exception 'ORDER_ALREADY_CANCELLED: % cannot be changed', old.order_number;
    end if;
  end if;
  return new;
end;
$$;

create trigger orders_guard_status_change
  before update on public.orders
  for each row execute function public.orders_guard_status_change();

-- When an order is cancelled, give its seats back to the courses (US-408 AC2).
-- SECURITY DEFINER so the seats are returned even though the update came through the app.
-- XP and badges are NOT taken away: no penalties (US-606 AC2).
create or replace function private.orders_return_seats()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if old.status = 'confirmed' and new.status = 'cancelled' then
    update public.courses c
       -- least(): never above seats_total, in case staff lowered the total since the order.
       set seats_available = least(c.seats_total, c.seats_available + oi.quantity)
      from public.order_items oi
     where oi.order_id = new.id
       and c.id = oi.course_id;
  end if;
  return null;
end;
$$;

create trigger orders_return_seats
  after update of status on public.orders
  for each row execute function private.orders_return_seats();
