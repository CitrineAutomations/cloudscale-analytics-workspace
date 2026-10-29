-- Modelled layer: one view per business entity, plus metrics views.
-- Recreated on every ETL run, so views always match the latest column logic.
-- "Live" subscription statuses match the Attio live_arr formula: Onboarding, Active, Renewal Due.

create schema if not exists analytics;

create or replace view analytics.dim_company as
select
    r.record_id                                  as company_id,
    r.fields->>'name'                            as name,
    r.fields->'domains'->>0                      as domain,
    r.fields->>'segment'                         as segment,
    r.fields->>'lifecycle_stage'                 as lifecycle_stage,
    r.fields->>'health'                          as health,
    (r.fields->>'total_arr')::numeric            as total_arr,
    (r.fields->>'active_users')::int             as active_users,
    csm.name                                     as csm_owner,
    sdr.name                                     as sdr_owner,
    r.created_at
from raw.attio_records r
left join raw.attio_members csm on csm.member_id = (r.fields->>'csm_owner')::uuid
left join raw.attio_members sdr on sdr.member_id = (r.fields->>'sdr_owner')::uuid
where r.object = 'companies';

create or replace view analytics.fct_subscription as
select
    r.record_id                                  as subscription_id,
    r.fields->>'name'                            as name,
    (r.fields->>'company')::uuid                 as company_id,
    c.name                                       as company,
    c.segment,
    r.fields->>'status'                          as status,
    r.fields->>'status' in ('Onboarding', 'Active', 'Renewal Due') as is_live,
    r.fields->>'plan'                            as plan,
    (r.fields->>'arr')::numeric                  as arr,
    (r.fields->>'seats_purchased')::int          as seats_purchased,
    (r.fields->>'price_per_seat')::numeric       as price_per_seat,
    (r.fields->>'start_date')::date              as start_date,
    (r.fields->>'end_date')::date                as end_date,
    (r.fields->>'auto_renew')::boolean           as auto_renew,
    (r.fields->>'originating_deal')::uuid        as originating_deal_id,
    (r.fields->>'renewal_deal')::uuid            as renewal_deal_id
from raw.attio_records r
left join analytics.dim_company c on c.company_id = (r.fields->>'company')::uuid
where r.object = 'subscriptions';

create or replace view analytics.fct_deal as
select
    r.record_id                                  as deal_id,
    r.fields->>'name'                            as name,
    (r.fields->>'associated_company')::uuid      as company_id,
    c.name                                       as company,
    c.segment,
    r.fields->>'deal_type'                       as deal_type,
    r.fields->>'stage'                           as stage,
    r.fields->>'stage' in ('Closed Won', 'Closed Lost') as is_closed,
    r.fields->>'stage' = 'Closed Won'            as is_won,
    r.fields->>'plan'                            as plan,
    (r.fields->>'seats')::int                    as seats,
    (r.fields->>'value')::numeric                as value,
    (r.fields->>'resulting_arr')::numeric        as resulting_arr,
    (r.fields->>'close_date')::date              as close_date,
    r.fields->>'loss_reason'                     as loss_reason,
    owner.name                                   as owner,
    sdr.name                                     as sourced_by,
    r.created_at,
    (r.fields->>'close_date')::date - r.created_at::date as cycle_days
from raw.attio_records r
left join analytics.dim_company c on c.company_id = (r.fields->>'associated_company')::uuid
left join raw.attio_members owner on owner.member_id = (r.fields->>'owner')::uuid
left join raw.attio_members sdr   on sdr.member_id   = (r.fields->>'sourced_by')::uuid
where r.object = 'deals';

create or replace view analytics.fct_workspace_usage as
select
    r.record_id                                  as workspace_record_id,
    r.fields->>'workspace_id'                    as workspace_id,
    r.fields->>'name'                            as name,
    (r.fields->>'company')::uuid                 as company_id,
    c.name                                       as company,
    (r.fields->>'subscription')::uuid            as subscription_id,
    (r.fields->>'seats_used')::int               as seats_used,
    (r.fields->>'seat_utilisation')::numeric     as seat_utilisation,
    (r.fields->>'weekly_active_users')::int      as weekly_active_users,
    (r.fields->>'wau_change_30d')::numeric       as wau_change_30d,
    (r.fields->>'departments_active')::int       as departments_active,
    (r.fields->>'paywall_hits_30d')::int         as paywall_hits_30d,
    r.fields->>'usage_signal'                    as usage_signal,
    r.fields->>'expansion_reason'                as expansion_reason,
    (r.fields->>'last_active_at')::timestamptz   as last_active_at,
    (r.fields->>'last_synced_at')::timestamptz   as last_synced_at
from raw.attio_records r
left join analytics.dim_company c on c.company_id = (r.fields->>'company')::uuid
where r.object = 'product_workspaces';

-- ARR by segment: the headline chart query.
create or replace view analytics.arr_by_segment as
select segment, count(distinct company_id) as customers, sum(arr) as arr
from analytics.fct_subscription
where is_live
group by segment
order by arr desc;

-- Company ARR on any date: terms whose contract dates cover that date.
-- A renewed or churned term still counts for the period it covered.
create or replace function analytics.company_arr_at(as_of date)
returns table (company_id uuid, arr numeric)
language sql stable as $$
    select company_id, sum(arr)
    from analytics.fct_subscription
    where start_date <= as_of and coalesce(end_date, 'infinity'::date) > as_of
    group by company_id
$$;

-- NRR / GRR over the trailing 12 months for the cohort that was paying 12 months ago.
-- NRR counts expansion; GRR caps each company at its starting ARR, so it only shows losses.
create or replace view analytics.metrics_revenue as
with now_arr as (
    select company_id, sum(arr) as arr from analytics.fct_subscription where is_live group by company_id
), cohort as (
    select company_id, arr from analytics.company_arr_at((current_date - interval '12 months')::date)
)
select
    (select sum(arr) from now_arr)                                   as current_arr,
    (select count(*) from now_arr)                                   as paying_customers,
    (select count(*) from cohort)                                    as cohort_customers_12m_ago,
    (select sum(arr) from cohort)                                    as cohort_arr_12m_ago,
    round(100 * sum(coalesce(n.arr, 0)) / nullif(sum(c.arr), 0), 1)                as nrr_pct,
    round(100 * sum(least(coalesce(n.arr, 0), c.arr)) / nullif(sum(c.arr), 0), 1)  as grr_pct
from cohort c
left join now_arr n using (company_id);

create or replace view analytics.metrics_sales as
select
    count(*) filter (where not is_closed)                                    as open_deals,
    sum(value) filter (where not is_closed)                                  as open_pipeline,
    count(*) filter (where is_won)                                           as won,
    count(*) filter (where is_closed and not is_won)                         as lost,
    round(100.0 * count(*) filter (where is_won)
          / nullif(count(*) filter (where is_closed), 0), 1)                 as win_rate_pct,
    round(avg(cycle_days) filter (where is_won and cycle_days >= 0), 0)      as avg_cycle_days
from analytics.fct_deal;
