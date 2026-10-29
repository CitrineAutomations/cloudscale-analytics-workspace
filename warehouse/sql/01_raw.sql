-- Raw layer: Attio records and list entries exactly as the API returns them.
-- Loaded by scripts/etl_attio.py (full load) and, later, the webhook Edge Function (incremental).
-- `values` is the untouched API payload; `fields` is the same data flattened to {slug: value}
-- so the modelled views can read `fields->>'arr'` instead of walking Attio's value arrays.

create schema if not exists raw;

create table if not exists raw.attio_records (
    object      text        not null,
    record_id   uuid        not null,
    created_at  timestamptz,
    "values"    jsonb       not null,
    fields      jsonb       not null,
    synced_at   timestamptz not null default now(),
    primary key (object, record_id)
);

create table if not exists raw.attio_list_entries (
    list              text        not null,
    entry_id          uuid        not null,
    parent_object     text        not null,
    parent_record_id  uuid        not null,
    created_at        timestamptz,
    "values"          jsonb       not null,
    fields            jsonb       not null,
    synced_at         timestamptz not null default now(),
    primary key (list, entry_id)
);

create table if not exists raw.attio_members (
    member_id   uuid primary key,
    name        text,
    email       text,
    access      text,
    synced_at   timestamptz not null default now()
);

-- One row per ETL run, so a stale warehouse is visible.
create table if not exists raw.etl_runs (
    run_id       bigint generated always as identity primary key,
    started_at   timestamptz not null,
    finished_at  timestamptz,
    mode         text        not null,
    row_counts   jsonb,
    error        text
);
