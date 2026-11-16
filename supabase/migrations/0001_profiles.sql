-- 0001_profiles.sql
-- One profile row per signed-up user (Supabase Auth keeps the password; we keep the app data).
-- Doc 00 section 6, US-504, NFR-SEC-01, NFR-PRIV-01.

-- A small reusable trigger function that keeps "updated_at" correct on every UPDATE.
-- Why: the app should never have to remember to set timestamps itself.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create table public.profiles (
  -- Same id as the Supabase Auth user, so "my profile" is simply id = auth.uid().
  id            uuid primary key references auth.users (id) on delete cascade,
  -- Copied from Auth when the account is created, so staff can see who placed an order (US-707, US-709).
  email         text not null,
  display_name  text not null check (char_length(display_name) between 1 and 50),
  -- Avatar is a name from a preset list in the app; never a photo upload (NFR-PRIV-02).
  avatar        text check (avatar is null or char_length(avatar) <= 40),
  -- Up to 3 interests (US-504 AC3).
  interests     text[] not null default '{}' check (cardinality(interests) <= 3),
  -- Every new account is a customer (NFR-SEC-01). Only the owner can change it (see 0011).
  role          text not null default 'customer' check (role in ('customer', 'staff', 'owner')),
  -- XP and level are only changed by database functions, never by the app (US-601 AC2).
  xp_total      integer not null default 0 check (xp_total >= 0),
  level         integer not null default 1 check (level between 1 and 5),
  reduce_motion boolean not null default false,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

comment on table public.profiles is 'One row per auth user: name, avatar, role, XP and level.';

-- Staff search users by email and filter by role (US-707, US-709).
create index profiles_email_idx on public.profiles (lower(email));
create index profiles_role_idx on public.profiles (role);

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();
