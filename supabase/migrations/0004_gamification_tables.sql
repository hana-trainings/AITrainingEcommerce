-- 0004_gamification_tables.sql
-- Badges, earned badges and the XP history. Doc 00 section 6, US-601 to US-603.
-- Ethical rules (US-606): no random rewards, no penalties, nothing visible to other customers.

create table public.badges (
  -- A short stable code such as 'first_unlock'. The app and functions refer to badges by code.
  code        text primary key check (code ~ '^[a-z0-9_]+$' and char_length(code) <= 60),
  name        text not null check (char_length(name) between 1 and 80),
  description text not null check (char_length(description) <= 300),
  icon        text not null default '🏅' check (char_length(icon) <= 40),
  -- Shown on locked badges, e.g. "Buy your first course to unlock" (US-603 AC1).
  hint        text check (hint is null or char_length(hint) <= 200),
  sort_order  integer not null default 0 check (sort_order >= 0)
);

-- The core badges live in a migration (not the seed) because sign-up and checkout award them.
-- Path badges ("Path Master: ...") are created with the learning paths in the seed or admin pages.
insert into public.badges (code, name, description, icon, hint, sort_order) values
  ('first_step',   'First Step',   'You created your SkillForge account.',          '👣', 'Create an account to unlock',              1),
  ('identity_set', 'Identity Set', 'You completed your Learner Passport.',          '🪪', 'Add a name, avatar and interests to unlock', 2),
  ('first_unlock', 'First Unlock', 'You unlocked your first course.',               '🔓', 'Buy your first course to unlock',          3),
  ('path_starter', 'Path Starter', 'You own a course that is part of a learning path.', '🧭', 'Unlock any course in a learning path',  4),
  ('collector',    'Collector',    'You own 5 or more courses.',                    '📚', 'Own 5 different courses to unlock',        5)
on conflict (code) do nothing;

create table public.user_badges (
  user_id     uuid not null references public.profiles (id) on delete cascade,
  badge_code  text not null references public.badges (code) on update cascade on delete cascade,
  awarded_at  timestamptz not null default now(),
  -- The primary key means a badge can only be earned once per user.
  primary key (user_id, badge_code)
);
-- Foreign key index for badge_code (user_id is covered by the primary key).
create index user_badges_badge_code_idx on public.user_badges (badge_code);

create table public.xp_events (
  id            bigint generated always as identity primary key,
  user_id       uuid not null references public.profiles (id) on delete cascade,
  action        text not null check (action in ('register', 'complete_profile', 'purchase_course', 'complete_path')),
  points        integer not null check (points >= 0),
  -- Which course or path the XP was for. 0 means "not about a specific course or path".
  reference_id  bigint not null default 0 check (reference_id >= 0),
  created_at    timestamptz not null default now(),
  -- The "once" limits from US-601: once per register, once per profile, once per course, once per path.
  constraint xp_events_once_key unique (user_id, action, reference_id)
);
-- The unique index above starts with user_id, so it also serves "my XP history" lookups.
