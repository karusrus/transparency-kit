-- AI Act Transparency Kit · storage. Three tables and one rule: decisions are append-only and hash-chained in the database.
create extension if not exists pgcrypto;

-- one row per asset that entered the gate; the manifest travels as jsonb, the columns are what the auditor filters on
create table if not exists assets (
  id               text primary key,
  line             text not null,
  asset_type       text not null,
  category         text not null,
  status           text not null default 'pending_review',   -- pending_review · approved · returned
  disclosure_status text,                                     -- disclosed · editorial_exception · not_required · returned
  model            text,
  operator         text,
  language         text,
  gate_url         text,
  execution_id     text,
  manifest         jsonb not null,
  created_at       timestamptz not null default now(),
  decided_at       timestamptz
);

-- every human decision, forever. No UPDATE, no DELETE for the application role; each row carries the hash of the previous one.
create table if not exists decisions (
  seq                bigserial primary key,
  asset_id           text not null references assets(id),
  decided_at         timestamptz not null default now(),
  reviewer           text not null,
  decision           text not null,
  reason             text,
  note               text,
  disclosure_status  text not null,
  responsible_person text,
  artefact           text,
  execution_id       text,
  workflow_id        text,
  prev_hash          text,
  hash               text
);

-- the registry as it looked each time the kit ran: history, not a file that gets overwritten
create table if not exists registry_snapshots (
  seq          bigserial primary key,
  generated_at timestamptz not null default now(),
  partial      boolean not null default false,
  systems      integer not null default 0,
  registry     jsonb not null
);

-- hash chain: computed inside the database, so the application never chooses its own hash
create or replace function decisions_chain() returns trigger language plpgsql as $$
declare last_hash text;
begin
  select hash into last_hash from decisions order by seq desc limit 1;
  new.prev_hash := coalesce(last_hash, 'genesis');
  new.hash := encode(digest(
      new.prev_hash || '|' || new.asset_id || '|' || new.decided_at::text || '|' || new.reviewer || '|' || new.decision
      || '|' || coalesce(new.reason,'') || '|' || new.disclosure_status || '|' || coalesce(new.responsible_person,'') || '|' || coalesce(new.artefact,''),
      'sha256'), 'hex');
  return new;
end $$;
drop trigger if exists decisions_chain_trg on decisions;
create trigger decisions_chain_trg before insert on decisions for each row execute function decisions_chain();

-- append-only, enforced in the database: the trigger refuses updates and deletes even from the owner
create or replace function decisions_immutable() returns trigger language plpgsql as $$
begin raise exception 'decisions are append-only'; end $$;
drop trigger if exists decisions_immutable_trg on decisions;
create trigger decisions_immutable_trg before update or delete on decisions for each row execute function decisions_immutable();

-- the auditor's check: recompute every hash from the previous row; returns rows that do not match
create or replace function verify_chain() returns table(seq bigint, ok boolean) language sql as $$
  with c as (
    select d.seq, d.hash, d.prev_hash,
      lag(d.hash) over (order by d.seq) as expected_prev,
      encode(digest(d.prev_hash || '|' || d.asset_id || '|' || d.decided_at::text || '|' || d.reviewer || '|' || d.decision
        || '|' || coalesce(d.reason,'') || '|' || d.disclosure_status || '|' || coalesce(d.responsible_person,'') || '|' || coalesce(d.artefact,''), 'sha256'), 'hex') as recomputed
    from decisions d)
  select seq, (hash = recomputed and prev_hash = coalesce(expected_prev, 'genesis')) as ok from c order by seq
$$;
