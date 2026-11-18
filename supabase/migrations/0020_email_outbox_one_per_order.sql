-- 0020_email_outbox_one_per_order.sql
-- At most ONE saved confirmation email per order (US-406, review fix).
--
-- Why: customers may insert their own email copy (RLS policy email_outbox_insert_own_order),
-- so without this rule someone could add extra rows for their order with any HTML, and a
-- double submit could save the email twice. With a unique order_id the first row wins;
-- the app treats the "unique violation" error (SQLSTATE 23505) as "already saved".
--
-- If duplicates already exist, adding the constraint FAILS. Remove the newer copies first,
-- keeping the oldest row of each order:
--   delete from public.email_outbox e
--    using public.email_outbox older
--    where older.order_id = e.order_id
--      and older.id < e.id;
--
-- Safe to run twice: the constraint is only added when it is missing.

do $$
begin
  if not exists (
    select 1
      from pg_constraint
     where conname = 'email_outbox_order_id_key'
       and conrelid = 'public.email_outbox'::regclass
  ) then
    alter table public.email_outbox
      add constraint email_outbox_order_id_key unique (order_id);
  end if;
end;
$$;

-- The unique constraint has its own index on order_id, so the plain index from 0008 is
-- no longer needed (one index is cheaper to keep up to date than two).
drop index if exists public.email_outbox_order_id_idx;
