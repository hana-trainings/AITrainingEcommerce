-- 0010_gamification_functions.sql
-- XP, levels and badges are awarded ONLY by these database functions, never from app input
-- (US-601 AC2, NFR-SEC-09). The app just reads the results.
--
-- Rules implemented (doc 01):
--   XP     : register +50 (once), complete profile +25 (once),
--            buy a course +xp_reward (default 100, once per course, not per seat),
--            own every course in a path +bonus_xp (default 250, once per path).
--   Levels : 1 Novice 0, 2 Explorer 150, 3 Practitioner 400, 4 Expert 800, 5 Master 1500.
--   Badges : first_step (register), identity_set (complete profile), first_unlock (first purchase),
--            path_starter (own 1 course in any path), collector (own 5+ courses),
--            the path's own badge_code (own every course in that path).

-- Turn an XP total into a level number (US-602).
create or replace function public.level_for_xp(p_xp integer)
returns integer
language sql
immutable
set search_path = ''
as $$
  select case
    when p_xp >= 1500 then 5
    when p_xp >= 800  then 4
    when p_xp >= 400  then 3
    when p_xp >= 150  then 2
    else 1
  end;
$$;
-- Harmless pure maths, so the app may call it too (e.g. to draw the XP bar).
grant execute on function public.level_for_xp(integer) to anon, authenticated;

-- Give XP once. Returns the points actually added (0 if this reward was already given).
-- The unique key on xp_events (user_id, action, reference_id) is what makes "once" reliable.
create or replace function private.award_xp(
  p_user_id uuid, p_action text, p_points integer, p_reference_id bigint default 0
)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.xp_events (user_id, action, points, reference_id)
  values (p_user_id, p_action, p_points, coalesce(p_reference_id, 0))
  on conflict (user_id, action, reference_id) do nothing;

  if not found then
    return 0;  -- already awarded before: no double XP
  end if;

  update public.profiles
     set xp_total = xp_total + p_points,
         level    = public.level_for_xp(xp_total + p_points)
   where id = p_user_id;

  return p_points;
end;
$$;

-- Give a badge once. Returns true only if it is new.
-- If the badge code doesn't exist (e.g. not seeded yet) nothing happens, instead of an error.
create or replace function private.award_badge(p_user_id uuid, p_badge_code text)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.user_badges (user_id, badge_code)
  select p_user_id, b.code from public.badges b where b.code = p_badge_code
  on conflict (user_id, badge_code) do nothing;
  return found;
end;
$$;

-- US-504 AC3: "complete your profile" gives +25 XP and the Identity Set badge, once.
-- The app calls this after the customer saves name + avatar + 1-3 interests.
-- Returns jsonb: { xp_awarded, new_level, level_up, new_badges }.
create or replace function public.claim_profile_completion()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id     uuid := (select auth.uid());
  v_profile     public.profiles%rowtype;
  v_xp          integer;
  v_new_badges  text[] := '{}';
  v_new_level   integer;
begin
  if v_user_id is null then
    raise exception 'NOT_SIGNED_IN';
  end if;

  select * into v_profile from public.profiles where id = v_user_id for update;

  -- Checked here, not trusted from the app: the profile really must be complete.
  if v_profile.avatar is null or cardinality(v_profile.interests) not between 1 and 3 then
    raise exception 'PROFILE_INCOMPLETE: choose an avatar and 1 to 3 interests';
  end if;

  v_xp := private.award_xp(v_user_id, 'complete_profile', 25);
  if private.award_badge(v_user_id, 'identity_set') then
    v_new_badges := array_append(v_new_badges, 'identity_set'::text);
  end if;

  select level into v_new_level from public.profiles where id = v_user_id;

  return jsonb_build_object(
    'xp_awarded', v_xp,
    'new_level',  v_new_level,
    'level_up',   v_new_level > v_profile.level,
    'new_badges', to_jsonb(v_new_badges)
  );
end;
$$;

revoke execute on function public.claim_profile_completion() from public, anon;
grant execute on function public.claim_profile_completion() to authenticated;

revoke all on all functions in schema private from public, anon, authenticated;
