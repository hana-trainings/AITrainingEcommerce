-- 0009_audit_log.sql
-- Who changed what, and when (NFR-SEC-18, US-706 AC3, US-709 AC4).
-- Triggers write most entries automatically, so the log stays complete even if a page forgets.

create table public.audit_log (
  id          bigint generated always as identity primary key,
  -- No foreign key on purpose: the history must survive even if that user is deleted later.
  actor_id    uuid,
  action      text not null check (char_length(action) between 1 and 60),
  entity      text not null check (char_length(entity) between 1 and 60),
  entity_id   text,
  before      jsonb,
  after       jsonb,
  created_at  timestamptz not null default now()
);

create index audit_log_created_at_idx on public.audit_log (created_at desc);
create index audit_log_entity_idx on public.audit_log (entity, entity_id);

-- Internal writer used by the triggers below. Lives in "private" so the app can't call it.
create or replace function private.write_audit(
  p_action text, p_entity text, p_entity_id text, p_before jsonb, p_after jsonb
)
returns void
language sql
security definer
set search_path = ''
as $$
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values ((select auth.uid()), p_action, p_entity, p_entity_id, p_before, p_after);
$$;

-- Helper the app CAN call, for notes a trigger can't know, e.g. the reason for a seat adjustment.
-- Only staff and owner may write, and the actor is always the real caller (never a parameter).
create or replace function public.write_audit_log(
  p_action text, p_entity text, p_entity_id text, p_before jsonb default null, p_after jsonb default null
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.is_staff() then
    raise exception 'NOT_ALLOWED: only staff can write to the audit log';
  end if;
  perform private.write_audit(p_action, p_entity, p_entity_id, p_before, p_after);
end;
$$;

revoke execute on function public.write_audit_log(text, text, text, jsonb, jsonb) from public, anon;
grant execute on function public.write_audit_log(text, text, text, jsonb, jsonb) to authenticated;

-- Course changes: create, update, publish/unpublish, seat adjustment, delete.
create or replace function private.audit_courses()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_action text;
begin
  if tg_op = 'INSERT' then
    perform private.write_audit('course_create', 'course', new.id::text, null, to_jsonb(new));
  elsif tg_op = 'DELETE' then
    perform private.write_audit('course_delete', 'course', old.id::text, to_jsonb(old), null);
  else
    -- Name the most important thing that changed, so the log is easy to read.
    if new.is_published is distinct from old.is_published then
      v_action := case when new.is_published then 'course_publish' else 'course_unpublish' end;
    elsif (new.seats_total, new.seats_available) is distinct from (old.seats_total, old.seats_available) then
      v_action := 'seat_adjust';
    else
      v_action := 'course_update';
    end if;
    -- Checkout also lowers seats. That is already recorded in orders, so skip it here and keep
    -- the log about admin work. place_order sets this flag for its own transaction only.
    if v_action = 'seat_adjust' and current_setting('skillforge.in_checkout', true) = 'on' then
      return null;
    end if;
    perform private.write_audit(v_action, 'course', new.id::text, to_jsonb(old), to_jsonb(new));
  end if;
  return null;
end;
$$;

create trigger audit_courses
  after insert or update or delete on public.courses
  for each row execute function private.audit_courses();

-- Role changes (US-709 AC4).
create or replace function private.audit_profile_role()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.role is distinct from old.role then
    perform private.write_audit('role_change', 'profile', new.id::text,
                                jsonb_build_object('role', old.role), jsonb_build_object('role', new.role));
  end if;
  return null;
end;
$$;

create trigger audit_profile_role
  after update of role on public.profiles
  for each row execute function private.audit_profile_role();

-- Order cancellations (NFR-SEC-18).
create or replace function private.audit_order_status()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.status is distinct from old.status then
    perform private.write_audit('order_' || new.status, 'order', new.id::text,
                                jsonb_build_object('status', old.status), jsonb_build_object('status', new.status));
  end if;
  return null;
end;
$$;

create trigger audit_order_status
  after update of status on public.orders
  for each row execute function private.audit_order_status();

-- Internal functions: nobody outside the database may call them.
revoke all on all functions in schema private from public, anon, authenticated;
