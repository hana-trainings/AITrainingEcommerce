-- 0008_email_outbox.sql
-- Saved copies of "sent" confirmation emails. No email is ever really sent (US-406).
-- Stored in the database because cloud file systems are temporary (NFR-DEP-04).

create table public.email_outbox (
  id          bigint generated always as identity primary key,
  order_id    bigint not null references public.orders (id) on delete cascade,
  user_id     uuid not null references public.profiles (id) on delete cascade,
  to_email    text not null check (char_length(to_email) between 3 and 254),
  subject     text not null check (char_length(subject) between 1 and 200),
  html_body   text not null check (char_length(html_body) <= 100000),
  -- Only safe characters: the app names the file, never the user (US-406 AC1).
  file_name   text not null check (file_name ~ '^[A-Za-z0-9_.-]{1,120}$'),
  created_at  timestamptz not null default now()
);

-- Foreign key indexes: "the email for this order" and "my emails".
create index email_outbox_order_id_idx on public.email_outbox (order_id);
create index email_outbox_user_id_idx on public.email_outbox (user_id);
