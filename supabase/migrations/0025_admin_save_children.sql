-- 0025_admin_save_children.sql
-- Save a course's syllabus and learning-path steps, or a path's ordered courses,
-- in ONE transaction (US-703, US-704, US-711).
--
-- Why: the app used to "delete all rows, then insert the new ones" with two separate
-- requests. If the insert failed (e.g. a path step already used by another course),
-- the old rows were already gone. A database function runs as one transaction, so on
-- any error EVERYTHING is undone and the old modules / path steps stay as they were.
--
-- SECURITY INVOKER (the default, written out on purpose): the function runs with the
-- CALLER's rights, so the RLS policies and grants from 0012 still decide what is allowed.
-- The is_staff() check only gives a clear error message instead of a silent "0 rows".
--
-- Errors (the message starts with a code the app maps to friendly text):
--   NOT_ALLOWED | COURSE_NOT_FOUND | PATH_NOT_FOUND | POSITION_TAKEN: <path> step <n>
--   DUPLICATE_PATH | DUPLICATE_COURSE | INVALID_REQUEST

-- p_modules        : [{"title": "...", "description": "..."}, ...] in syllabus order
-- p_path_positions : [{"path_id": 1, "position": 2}, ...]
create or replace function public.admin_replace_course_children(
  p_course_id bigint, p_modules jsonb, p_path_positions jsonb
)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_clash record;
begin
  if not public.is_staff() then
    raise exception 'NOT_ALLOWED: only staff can edit courses';
  end if;
  if jsonb_typeof(coalesce(p_modules, '[]'::jsonb)) <> 'array'
     or jsonb_typeof(coalesce(p_path_positions, '[]'::jsonb)) <> 'array' then
    raise exception 'INVALID_REQUEST: modules and path positions must be lists';
  end if;

  -- Lock the course row so two editors saving the same course wait for each other.
  perform 1 from public.courses where id = p_course_id for update;
  if not found then
    raise exception 'COURSE_NOT_FOUND';
  end if;

  -- The same path twice in one request?
  if exists (
    select 1
      from jsonb_array_elements(coalesce(p_path_positions, '[]'::jsonb)) as item
     group by (item ->> 'path_id')
    having count(*) > 1
  ) then
    raise exception 'DUPLICATE_PATH: add the course to each learning path only once';
  end if;

  -- Is a requested step already used by ANOTHER course? Checked first for a clear message.
  select lp.name, (item ->> 'position')::integer as position
    into v_clash
    from jsonb_array_elements(coalesce(p_path_positions, '[]'::jsonb)) as item
    join public.learning_path_courses lpc
      on lpc.path_id = (item ->> 'path_id')::bigint
     and lpc.position = (item ->> 'position')::integer
     and lpc.course_id <> p_course_id
    join public.learning_paths lp on lp.id = lpc.path_id
   limit 1;
  if found then
    raise exception 'POSITION_TAKEN: % step %', v_clash.name, v_clash.position;
  end if;

  -- Replace the syllabus: positions are 1, 2, 3 ... in the order given.
  delete from public.course_modules where course_id = p_course_id;
  insert into public.course_modules (course_id, position, title, description)
  select p_course_id,
         m.ord::integer,
         trim(m.item ->> 'title'),
         nullif(trim(coalesce(m.item ->> 'description', '')), '')
    from jsonb_array_elements(coalesce(p_modules, '[]'::jsonb)) with ordinality as m (item, ord);

  -- Replace the learning-path steps.
  delete from public.learning_path_courses where course_id = p_course_id;
  insert into public.learning_path_courses (path_id, course_id, position)
  select (item ->> 'path_id')::bigint, p_course_id, (item ->> 'position')::integer
    from jsonb_array_elements(coalesce(p_path_positions, '[]'::jsonb)) as item;
exception
  -- A step taken by someone else at the very same moment: undo everything with a clear code.
  when unique_violation then
    raise exception 'POSITION_TAKEN: a learning path step is already used';
end;
$$;

-- p_course_ids : the path's courses in order (step 1, 2, 3 ...)
create or replace function public.admin_replace_path_courses(
  p_path_id bigint, p_course_ids bigint[]
)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if not public.is_staff() then
    raise exception 'NOT_ALLOWED: only staff can edit learning paths';
  end if;
  if p_course_ids is null then
    raise exception 'INVALID_REQUEST: a list of courses is required';
  end if;
  if cardinality(p_course_ids) <> (select count(distinct c) from unnest(p_course_ids) as c) then
    raise exception 'DUPLICATE_COURSE: add each course only once';
  end if;

  perform 1 from public.learning_paths where id = p_path_id for update;
  if not found then
    raise exception 'PATH_NOT_FOUND';
  end if;

  delete from public.learning_path_courses where path_id = p_path_id;
  insert into public.learning_path_courses (path_id, course_id, position)
  select p_path_id, c.course_id, c.ord::integer
    from unnest(p_course_ids) with ordinality as c (course_id, ord);
exception
  when unique_violation then
    raise exception 'POSITION_TAKEN: two courses can''t share a step';
end;
$$;

-- Only signed-in users may call them (the staff check and RLS do the rest). Never guests.
revoke execute on function public.admin_replace_course_children(bigint, jsonb, jsonb) from public, anon;
grant execute on function public.admin_replace_course_children(bigint, jsonb, jsonb) to authenticated;
revoke execute on function public.admin_replace_path_courses(bigint, bigint[]) from public, anon;
grant execute on function public.admin_replace_path_courses(bigint, bigint[]) to authenticated;
