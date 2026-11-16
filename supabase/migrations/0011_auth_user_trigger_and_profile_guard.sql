-- 0011_auth_user_trigger_and_profile_guard.sql
-- 1) Create a profile automatically when someone signs up.
-- 2) Stop users from changing their own role, XP or level (NFR-SEC-01, NFR-SEC-02, US-709).

-- 1) Runs right after Supabase Auth inserts a new user.
-- SECURITY DEFINER because the new user has no rights on profiles yet.
create or replace function private.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_name text;
begin
  -- Use the name typed on the register form; if empty, use the part of the email before "@".
  v_name := left(coalesce(
    nullif(trim(new.raw_user_meta_data ->> 'display_name'), ''),
    split_part(new.email, '@', 1)
  ), 50);

  -- Role is NOT read from the sign-up data: a user could put "owner" there. Always 'customer'.
  insert into public.profiles (id, email, display_name, role)
  values (new.id, coalesce(new.email, ''), coalesce(nullif(v_name, ''), 'Learner'), 'customer')
  on conflict (id) do nothing;

  -- US-501 AC4: +50 XP and the "First Step" badge for registering.
  perform private.award_xp(new.id, 'register', 50);
  perform private.award_badge(new.id, 'first_step');

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function private.handle_new_user();

revoke all on function private.handle_new_user() from public, anon, authenticated;

-- 2) Profile guard. This is a normal (SECURITY INVOKER) trigger on purpose:
-- "current_user" is then the role that made the change.
--   'authenticated' / 'anon' = a request from the app (follow the strict rules)
--   'postgres' (inside place_order and other database functions, or the SQL editor) = trusted.
create or replace function public.profiles_guard_update()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  v_from_app boolean := current_user in ('anon', 'authenticated');
  v_other_owners integer;
begin
  if v_from_app then
    -- XP, level, id and email are never edited from the app.
    if new.xp_total is distinct from old.xp_total
       or new.level is distinct from old.level
       or new.id is distinct from old.id
       or new.email is distinct from old.email then
      raise exception 'NOT_ALLOWED: XP, level and email are managed by the system';
    end if;

    if new.role is distinct from old.role then
      -- Only the owner may change roles (NFR-SEC-02).
      if not public.is_owner() then
        raise exception 'NOT_ALLOWED: only the owner can change roles';
      end if;
      -- From the app the owner switches people between customer and staff only (US-709 AC1).
      -- Making or removing an owner is a trainer job in the SQL editor (see docs/deployment/demo-accounts.md).
      if old.role = 'owner' or new.role = 'owner' then
        raise exception 'NOT_ALLOWED: the owner role is managed by the trainer';
      end if;
    end if;
  end if;

  -- Always true, even in the SQL editor: never remove the last owner (US-709 AC2).
  if old.role = 'owner' and new.role <> 'owner' then
    select count(*) into v_other_owners
      from public.profiles
     where role = 'owner' and id <> old.id;
    if v_other_owners = 0 then
      raise exception 'LAST_OWNER: the last owner cannot be demoted';
    end if;
  end if;

  return new;
end;
$$;

create trigger profiles_guard_update
  before update on public.profiles
  for each row execute function public.profiles_guard_update();
