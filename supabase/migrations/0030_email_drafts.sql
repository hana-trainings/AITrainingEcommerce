-- 0030_email_drafts.sql
-- Turn email_outbox into the app's own "email service": every email the store would send is
-- saved here as a DRAFT and never really sent. Supabase Auth sends no emails either
-- ("Confirm email" is switched off in the dashboard, see docs/deployment/demo-accounts.md).
--
-- Kinds of email:
--   order_confirmation : one per order, saved at checkout (US-406). Needs an order_id.
--   welcome            : one per user, saved by the register service. Has no order.
--
-- A NEW migration on purpose: 0008 and 0012 are already applied, so we never edit them.
-- Safe to run twice.

-- 1) New columns. Existing rows are all order confirmations and drafts.
alter table public.email_outbox
  add column if not exists email_type text not null default 'order_confirmation',
  add column if not exists status     text not null default 'draft';

-- 2) A welcome email has no order, so order_id may now be empty.
alter table public.email_outbox alter column order_id drop not null;

-- 3) Rules for the new columns (dropped first so the file can run again).
alter table public.email_outbox drop constraint if exists email_outbox_email_type_check;
alter table public.email_outbox
  add constraint email_outbox_email_type_check
  check (email_type in ('order_confirmation', 'welcome'));

-- Only drafts exist: this app never sends an email.
alter table public.email_outbox drop constraint if exists email_outbox_status_check;
alter table public.email_outbox
  add constraint email_outbox_status_check check (status = 'draft');

-- An order confirmation always has an order; a welcome email never has one.
alter table public.email_outbox drop constraint if exists email_outbox_order_matches_type;
alter table public.email_outbox
  add constraint email_outbox_order_matches_type
  check ((email_type = 'order_confirmation') = (order_id is not null));

-- 4) At most ONE welcome email per user (a repeated save can't pile up drafts).
create unique index if not exists email_outbox_one_welcome_per_user
  on public.email_outbox (user_id)
  where email_type = 'welcome';

-- Newest first on the admin "Email drafts" page.
create index if not exists email_outbox_created_at_idx
  on public.email_outbox (created_at desc);

-- 5) Who may save a draft. Reading rules from 0012 stay the same:
--    a customer reads their own emails, staff and owner read all of them.
drop policy if exists email_outbox_insert_own_order on public.email_outbox;
drop policy if exists email_outbox_insert_own_order_confirmation on public.email_outbox;
drop policy if exists email_outbox_insert_own_welcome on public.email_outbox;

-- An order confirmation only for an order that is really yours (same rule as before).
create policy email_outbox_insert_own_order_confirmation on public.email_outbox
  for insert to authenticated
  with check (
    email_type = 'order_confirmation'
    and user_id = (select auth.uid())
    and exists (
      select 1 from public.orders o
       where o.id = email_outbox.order_id
         and o.user_id = (select auth.uid())
    )
  );

-- A welcome email only for yourself, addressed to your own email address.
create policy email_outbox_insert_own_welcome on public.email_outbox
  for insert to authenticated
  with check (
    email_type = 'welcome'
    and order_id is null
    and user_id = (select auth.uid())
    and lower(to_email) = (
      select lower(p.email) from public.profiles p where p.id = (select auth.uid())
    )
  );
