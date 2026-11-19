-- 0005_learning_paths.sql
-- Learning paths (the skill tree) and which courses belong to each path, in order.
-- Doc 00 section 6, US-604, US-711.

create table public.learning_paths (
  id           bigint generated always as identity primary key,
  name         text not null unique check (char_length(name) between 1 and 80),
  description  text not null default '' check (char_length(description) <= 1000),
  -- Bonus XP for owning every course in the path (US-601: +250).
  bonus_xp     integer not null default 250 check (bonus_xp between 0 and 1000),
  -- The "Path Master" badge for this path. Optional, so a path can exist before its badge.
  badge_code   text references public.badges (code) on update cascade on delete set null,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index learning_paths_badge_code_idx on public.learning_paths (badge_code);

create trigger learning_paths_set_updated_at
  before update on public.learning_paths
  for each row execute function public.set_updated_at();

create table public.learning_path_courses (
  path_id    bigint not null references public.learning_paths (id) on delete cascade,
  course_id  bigint not null references public.courses (id) on delete cascade,
  position   integer not null check (position between 1 and 50),
  primary key (path_id, course_id),
  -- Two courses can't share the same step in one path.
  constraint learning_path_courses_path_position_key unique (path_id, position)
);
-- Foreign key index for course_id ("which paths is this course in?", US-205, US-603).
create index learning_path_courses_course_id_idx on public.learning_path_courses (course_id);
