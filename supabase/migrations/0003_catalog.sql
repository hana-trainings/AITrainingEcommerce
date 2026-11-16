-- 0003_catalog.sql
-- The things we sell: categories, courses and each course's syllabus (modules).
-- Doc 00 section 6, US-101 to US-205, US-703, NFR-DATA-02, NFR-DATA-07, NFR-PERF-06.

create table public.categories (
  id          bigint generated always as identity primary key,
  name        text not null unique check (char_length(name) between 1 and 60),
  icon        text not null default '📘' check (char_length(icon) <= 40),
  sort_order  integer not null default 0 check (sort_order >= 0),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create trigger categories_set_updated_at
  before update on public.categories
  for each row execute function public.set_updated_at();

create table public.courses (
  id               bigint generated always as identity primary key,
  -- Slug is the URL-friendly name, e.g. "sql-for-analysts". Must be unique (NFR-DATA-02).
  slug             text not null unique check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' and char_length(slug) <= 80),
  title            text not null check (char_length(title) between 1 and 120),
  summary          text not null check (char_length(summary) between 1 and 200),
  description      text not null check (char_length(description) between 1 and 5000),
  -- "restrict": a category that still has courses cannot be deleted by accident.
  category_id      bigint not null references public.categories (id) on delete restrict,
  level            text not null check (level in ('Beginner', 'Intermediate', 'Advanced')),
  duration_hours   numeric(5,1) not null check (duration_hours > 0 and duration_hours <= 500),
  -- Money is numeric(10,2), never float, so cents never get lost (NFR-DATA-07). USD.
  price            numeric(10,2) not null check (price >= 0 and price <= 9999),
  seats_total      integer not null check (seats_total between 1 and 10000),
  -- The two rules that make over-booking impossible at the database level (US-403 AC2).
  seats_available  integer not null,
  constraint courses_seats_available_not_negative check (seats_available >= 0),
  constraint courses_seats_available_max check (seats_available <= seats_total),
  instructor_name  text check (instructor_name is null or char_length(instructor_name) <= 80),
  outcomes         text[] not null default '{}',
  prerequisites    text[] not null default '{}',
  tags             text[] not null default '{}',
  image_url        text check (image_url is null or char_length(image_url) <= 500),
  -- XP a customer earns the first time they buy this course (US-601). Read by place_order, never from the client.
  xp_reward        integer not null default 100 check (xp_reward between 0 and 1000),
  -- New courses are hidden until staff publish them (US-703 AC4).
  is_published     boolean not null default false,
  is_featured      boolean not null default false,
  -- Who last changed the course (US-704 AC3). Filled in automatically by a trigger below.
  updated_by       uuid references public.profiles (id) on delete set null,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

comment on table public.courses is 'The products. seats_available is the inventory and can never go below 0.';

-- Indexes for the catalog filters (NFR-PERF-06) and for every foreign key.
create index courses_is_published_idx on public.courses (is_published);
create index courses_category_id_idx on public.courses (category_id);
create index courses_updated_by_idx on public.courses (updated_by);
-- Tag filter uses "tags @> array['sql']", which a GIN index makes fast.
create index courses_tags_idx on public.courses using gin (tags);

-- Stamp updated_at and updated_by on every change, so the app cannot forget or fake it.
create or replace function public.courses_stamp_update()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  -- Checkout lowers seats too, but a customer buying is not "editing the course".
  -- place_order sets this flag (for its own transaction only), so we leave the stamps alone then.
  if tg_op = 'UPDATE' and current_setting('skillforge.in_checkout', true) = 'on' then
    return new;
  end if;
  new.updated_at := now();
  -- auth.uid() is empty when a trainer edits in the SQL editor; keep the old value then.
  new.updated_by := coalesce((select auth.uid()), new.updated_by);
  return new;
end;
$$;

create trigger courses_stamp_update
  before insert or update on public.courses
  for each row execute function public.courses_stamp_update();

create table public.course_modules (
  id           bigint generated always as identity primary key,
  -- "cascade": modules belong to their course; delete the course, delete its syllabus.
  course_id    bigint not null references public.courses (id) on delete cascade,
  position     integer not null check (position between 1 and 100),
  title        text not null check (char_length(title) between 1 and 120),
  description  text check (description is null or char_length(description) <= 1000),
  -- Two modules of one course can't both be "module 1".
  constraint course_modules_course_position_key unique (course_id, position)
);
-- The unique (course_id, position) index also serves the foreign key lookup on course_id.
