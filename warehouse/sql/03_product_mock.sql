-- Mock product database: what CloudScale's own app would log per workspace per day.
-- Seeded by scripts/seed_usage.py. The n8n usage sync (rETL) reads public.workspace_usage_latest
-- through the Supabase REST API and upserts Product Workspaces in Attio.
-- RLS is on with no policies: only the service/secret key (n8n, scripts) can read or write.

create table if not exists public.workspace_usage_daily (
    workspace_id         text        not null,
    usage_date           date        not null,
    workspace_name       text        not null,
    company_domain       text        not null,
    seats_used           int         not null,
    weekly_active_users  int         not null,
    departments_active   int         not null,
    paywall_hits         int         not null default 0,   -- hits that day
    last_active_at       timestamptz,
    primary key (workspace_id, usage_date)
);
alter table public.workspace_usage_daily enable row level security;

-- Failed n8n rows, with the payload so they can be replayed (runbook: 03-docs/runbooks/usage-sync.md).
create table if not exists public.sync_errors (
    id            bigint generated always as identity primary key,
    occurred_at   timestamptz not null default now(),
    workflow      text        not null,
    node          text,
    workspace_id  text,
    error         text        not null,
    payload       jsonb,
    replayed_at   timestamptz
);
alter table public.sync_errors enable row level security;

-- One row per workspace: today's numbers plus the 30-day figures W4 rules use.
-- security_invoker makes the view obey the table's RLS, so the anon key sees nothing.
create or replace view public.workspace_usage_latest
with (security_invoker = true) as
with latest as (
    select distinct on (workspace_id) *
    from public.workspace_usage_daily
    order by workspace_id, usage_date desc
)
select
    l.workspace_id,
    l.workspace_name,
    l.company_domain,
    l.usage_date,
    l.seats_used,
    l.weekly_active_users,
    round(100.0 * (l.weekly_active_users - prev.weekly_active_users)
          / nullif(prev.weekly_active_users, 0), 1)                  as wau_change_30d,
    l.departments_active,
    (select coalesce(sum(d.paywall_hits), 0) from public.workspace_usage_daily d
      where d.workspace_id = l.workspace_id
        and d.usage_date > l.usage_date - 30)                        as paywall_hits_30d,
    l.last_active_at
from latest l
left join public.workspace_usage_daily prev
       on prev.workspace_id = l.workspace_id and prev.usage_date = l.usage_date - 30;
