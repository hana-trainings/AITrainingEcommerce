-- 0002_role_helpers.sql
-- Small helper functions that answer "who is calling?". Security rules (RLS policies) use them.
--
-- Why SECURITY DEFINER: a policy on "profiles" that reads "profiles" would call itself forever.
-- Running the lookup as the table owner skips RLS for this one tiny, read-only question.
-- Why "set search_path = ''": nobody can trick the function into using a look-alike table
-- from another schema; every name below is written in full (public.profiles, auth.uid()).
-- These helpers only ever describe the CURRENT caller, so they leak nothing about other users.

-- Returns 'guest' (not signed in), 'customer', 'staff' or 'owner'.
create or replace function public.current_role_name()
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select coalesce(
    (select p.role from public.profiles p where p.id = (select auth.uid())),
    'guest'
  );
$$;

-- True for staff AND owner (the owner can do everything staff can).
create or replace function public.is_staff()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select public.current_role_name() in ('staff', 'owner');
$$;

-- True only for the owner.
create or replace function public.is_owner()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select public.current_role_name() = 'owner';
$$;

-- Policies run as the caller, so guests (anon) and signed-in users must be able to call these.
revoke execute on function public.current_role_name() from public;
revoke execute on function public.is_staff() from public;
revoke execute on function public.is_owner() from public;
grant execute on function public.current_role_name() to anon, authenticated;
grant execute on function public.is_staff() to anon, authenticated;
grant execute on function public.is_owner() to anon, authenticated;

-- A private schema for internal helpers that the app must NOT call directly.
-- Supabase only exposes the "public" schema through its API, and we also remove all access here.
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
