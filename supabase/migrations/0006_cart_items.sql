-- 0006_cart_items.sql
-- Saved carts for signed-in customers (guests keep their cart in the browser session only).
-- Doc 00 section 6, US-301 to US-307.

create table public.cart_items (
  user_id     uuid not null references public.profiles (id) on delete cascade,
  -- If staff delete a course, it simply disappears from carts.
  course_id   bigint not null references public.courses (id) on delete cascade,
  -- Seats per course: 1 to 5 (US-303, NFR-DATA-02).
  quantity    integer not null default 1 check (quantity between 1 and 5),
  added_at    timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  -- One row per course per user: adding the same course again raises the quantity instead.
  primary key (user_id, course_id)
);
-- The primary key starts with user_id, so it already serves "my cart" (NFR-PERF-06).
-- Separate index for the course_id foreign key.
create index cart_items_course_id_idx on public.cart_items (course_id);

create trigger cart_items_set_updated_at
  before update on public.cart_items
  for each row execute function public.set_updated_at();
