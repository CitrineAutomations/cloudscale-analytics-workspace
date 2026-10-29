# CloudScale Analytics — Attio Build Plan

**Phase:** 02 Design · **Status:** Built · **Input:** [01-discovery/gtm-motion-map.md](../01-discovery/gtm-motion-map.md), [01-discovery/product-profile.md](../01-discovery/product-profile.md)

Workspace: `cloud-scale-analytics-citrineautomations` (Pro plan, 12-object cap, formula attributes available).

Legend: **API** = created by script through the Attio REST API. **UI** = built by hand (the API cannot create it). **Std** = standard attribute that already exists.

---

## 0. Pre-checks (verified 2026-10-16)

| Check | Result |
|---|---|
| Object cap | 5 of 12 used after build (Companies, People, Deals, Subscriptions, Product Workspaces) |
| Same person on a list more than once | Allowed: "Multiple list entries are allowed for the same parent record" |
| Two-way relationships | Supported on `record-reference` via a `relationship` object |
| Formula attributes | Pro plan, UI only |
| Team / member permissions | Pro plan (Plus is workspace-wide only) |
| Funnel + time-in-stage reports | Plus and above |
| Native Sequences from a workflow | "Enroll in sequence" workflow block |
| Deals object | Enabled (confirmed 2026-10-18) |
| Date math in workflows (W3a renewal `end_date` = start + 12 months) | **To verify.** Fallback: CSM sets `end_date` on the new term |

---

## 1. Objects

| Object | Slug | Type | Purpose | Req |
|---|---|---|---|---|
| Companies | `companies` | Std | Account, lifecycle, segment, total ARR | R1–R3 |
| People | `people` | Std | Leads and contacts, lifecycle, source | R1, R3 |
| Deals | `deals` | Std (enable) | New, expansion and renewal pipeline | R4 |
| Subscriptions | `subscriptions` | **Custom** | One row per contract term: plan, ARR, seats, dates | R6 |
| Product Workspaces | `product_workspaces` | **Custom** | One row per product tenant: usage and health | R7, R8 |

---

## 2. Relationships (two-way, API)

| From attribute | ↔ | Reverse attribute | Cardinality |
|---|---|---|---|
| `subscriptions.company` | ↔ | `companies.subscriptions` | many → one |
| `subscriptions.originating_deal` | ↔ | `deals.created_subscription` | one ↔ one |
| `subscriptions.renewal_deal` | ↔ | `deals.renews_subscription` | one ↔ one |
| `deals.expands_subscription` | ↔ | `subscriptions.expansion_deals` | many → one |
| `product_workspaces.company` | ↔ | `companies.product_workspaces` | many → one |
| `product_workspaces.subscription` | ↔ | `subscriptions.product_workspaces` | many → one |
| `product_workspaces.users` | ↔ | `people.product_workspaces` | many ↔ many |

Std links kept as-is: `people.company`, `deals.associated_company`, `deals.associated_people`.

```
Companies 1 ── * Deals (deal_type: New / Expansion / Renewal)
Companies 1 ── * Subscriptions ── 1 originating Deal
                               ├── 0..1 renewal Deal
                               └── * expansion Deals
Companies 1 ── * Product Workspaces * ── * People (users)
Subscriptions 1 ── * Product Workspaces
Deals ── People  (economic_buyer, champion, technical_evaluator; everyone else in associated_people)
```

---

## 3. Attributes

What each field means, who sets it and what uses it: [field-guide.md](field-guide.md).

### Companies (add)

| Attribute | Slug | Type | Values / notes | Build |
|---|---|---|---|---|
| Lifecycle stage | `lifecycle_stage` | select | Lead, MQL, SQL, Opportunity, Customer, Churned | API |
| Segment | `segment` | select | Growth, Mid-Market, Enterprise | API |
| SDR owner | `sdr_owner` | actor-reference | | API |
| CSM owner | `csm_owner` | actor-reference | | API |
| Health | `health` | select | Healthy, Watch, At risk | API (set by W4: worst signal across the company's workspaces) |
| Total ARR | `total_arr` | formula (currency) | `sum({Subscriptions > Live ARR})`. Attio can't filter an aggregation, so the status filter lives in the Subscriptions `live_arr` helper. | **UI** |
| Active users | `active_users` | formula | `sum()` of `product_workspaces.weekly_active_users` | **UI** |

### People (add)

| Attribute | Slug | Type | Values / notes | Build |
|---|---|---|---|---|
| Lifecycle stage | `lifecycle_stage` | select | Lead, MQL, SQL, Opportunity, Customer, Churned | API |
| Lead source | `lead_source` | select | Demo request, Content download, Webinar, Contact sales, Outbound, Referral | API |
| UTM campaign | `utm_campaign` | text | | API |
| UTM source | `utm_source` | text | | API |
| Form intent | `form_intent` | select | High (demo / contact sales), Low (content) | API |
| First touch at | `first_touch_at` | timestamp | Set by SDR or W2b; drives speed-to-lead | API |

### Deals (add to Std `name`, `stage`, `owner`, `value`, `associated_company`, `associated_people`)

| Attribute | Slug | Type | Values / notes | Build |
|---|---|---|---|---|
| Stage | `stage` | status (Std) | Replace defaults: Demo Scheduled, Discovery, Technical Evaluation, Business Case & Proposal, Security & Procurement, Negotiation, Closed Won, Closed Lost | API |
| Deal type | `deal_type` | select | New, Expansion, Renewal | API |
| Plan | `plan` | select | Growth, Business, Enterprise | API |
| Seats | `seats` | number | Total seats on the subscription after this deal closes | API |
| Price per seat | `price_per_seat` | currency (USD) | Extra-user rate; list price or negotiated | API |
| Resulting ARR | `resulting_arr` | currency (USD) | Subscription ARR after close. `value` = ARR added by this deal. | API |
| Economic buyer | `economic_buyer` | record-reference → People (single) | Signs off on budget | API |
| Champion | `champion` | record-reference → People (single) | Sells for us internally | API |
| Technical evaluator | `technical_evaluator` | record-reference → People (single) | Data / IT lead running the evaluation | API |
| Close date | `close_date` | date | | API |
| Loss reason | `loss_reason` | select | Price, Timing, Competitor, No decision, Missing feature, Bad fit | API |
| SDR (sourced by) | `sourced_by` | actor-reference | Credit for SDR | API |

### Subscriptions (custom)

| Attribute | Slug | Type | Values / notes | Build |
|---|---|---|---|---|
| Name | `name` | text | e.g. "Acme — 2026–27" | API |
| Status | `status` | status | Onboarding, Active, Renewal Due, Renewed, Churned | API |
| Plan | `plan` | select | Growth, Business, Enterprise (pricing in product profile §2) | API |
| ARR | `arr` | currency (USD) | Base price + (seats − included) × price per seat. Set by W3a. | API |
| Seats purchased | `seats_purchased` | number | Never below the plan's included users | API |
| Price per seat | `price_per_seat` | currency (USD) | Extra-user rate; negotiated on Enterprise | API |
| Start date | `start_date` | date | | API |
| End date | `end_date` | date | Renewal deal opens at end − 90 days (W5) | API |
| Auto-renew | `auto_renew` | checkbox | | API |
| Live ARR | `live_arr` | formula (currency) | `arr` when status is Onboarding, Active or Renewal Due (a new customer counts from signature); otherwise 0. Helper for Company `total_arr`. | **UI** |

### Product Workspaces (custom)

| Attribute | Slug | Type | Values / notes | Build |
|---|---|---|---|---|
| Name | `name` | text | | API |
| Workspace ID | `workspace_id` | text, **unique** | Product tenant key; n8n upserts on it | API |
| Seats used | `seats_used` | number | Synced | API |
| Seat utilisation | `seat_utilisation` | number (%) | Calculated by n8n: `seats_used / subscription.seats_purchased` | API |
| Weekly active users | `weekly_active_users` | number | Synced | API |
| WAU change 30d (%) | `wau_change_30d` | number | Synced | API |
| Departments active | `departments_active` | number | Distinct user groups with active users | API |
| Paywall hits (30d) | `paywall_hits_30d` | number | Attempts to use a feature above the plan | API |
| Last active at | `last_active_at` | timestamp | Synced | API |
| Last synced at | `last_synced_at` | timestamp | Set by n8n; shows sync freshness | API |
| Usage signal | `usage_signal` | select | Expansion, Stable, Risk | API (set by W4) |
| Expansion reason | `expansion_reason` | select | Seats, New department, Plan upgrade | API (set by W4) |

---

## 4. Lists

| List | Parent | Entry attributes | Req |
|---|---|---|---|
| **SDR Queue** | People | `status` (status: New, Contacted, Qualified, Nurture, Disqualified), `sla_due_at` (timestamp), `dq_reason` (select: Too small, No data stack, Student / job seeker, Competitor, Duplicate) | R2 |
| **Onboarding** | Companies | `stage` (status: Kickoff, Data Source Connected, First Dashboard Live, Team Trained, Live), `subscription` (record-reference → Subscriptions), `kickoff_date`, `target_go_live`, `go_live_date` (dates) | R9 |

The buying committee (R5) is not a list: the three decision roles are person fields on Deals (section 3), and everyone else involved sits in the standard `associated_people`.

---

## 5. Workflows (UI) — mapped to the build

Block-by-block build specs and tests: [workflow-specs.md](workflow-specs.md).

| Workflow (name in Attio) | Trigger → actions | Touches | Integration |
|---|---|---|---|
| W1 — Inbound lead (Typeform) | Typeform submit → upsert Person + Company, set source/UTM/intent, lifecycle = MQL → add to SDR Queue, round-robin SDR by segment, set `sla_due_at` | People, Companies, SDR Queue | **Typeform (native)** |
| W2a — New Lead Alert | SDR Queue entry created → post in `#sdr-leads` + first-touch task for the SDR; `sla_due_at` passed and status still New → Slack alert to SDR lead | SDR Queue | **Slack (native)** |
| W2b — Speed-to-lead | SDR Queue status leaves New → stamp `first_touch_at` on the person, for the speed-to-lead report | SDR Queue, People | Attio |
| W3a — Closed Won handoff | Deal stage → Closed Won. **New:** create Subscription (status Onboarding) with `plan`, `seats_purchased`, `price_per_seat` and `arr` copied from the deal (`arr` = `resulting_arr`), link originating deal, set company lifecycle = Customer, assign CSM, add to Onboarding, Slack handoff. **Expansion:** update the linked subscription's `plan`, `seats_purchased`, `price_per_seat` and `arr` from the deal, then Slack the CSM. **Renewal:** set the old term (`renews_subscription`) to Renewed; create the next term (status Active, no onboarding) with `plan`, `seats_purchased`, `price_per_seat` and `arr` from the deal, `start_date` = old `end_date`, `end_date` = start + 12 months, link it as `created_subscription`; Slack the CSM. | Deals, Subscriptions, Onboarding | Attio + Slack |
| W3b — Lost renewal → Churned | Renewal deal → Closed Lost → set the old term to Churned; if the company has no other live subscription, lifecycle = Churned; alert `#cs-alerts` | Deals, Subscriptions, Companies | Attio + Slack |
| W4 — Usage Signal | Workspace usage updated → evaluate the expansion and risk rules in [product profile §4](../01-discovery/product-profile.md#4-triggers-w4). **Act only when `usage_signal` or `expansion_reason` changes.** Expansion: set reason + CSM task. Risk: Slack alert to CSM. Roll up `health` to Company (worst signal wins). | Product Workspaces, Companies | Attio + Slack |
| W5 — Renewal opens | Subscription end date − 90 days → create Renewal deal, link `renewal_deal`, status = Renewal Due | Subscriptions, Deals | Attio |
| W6 — Nurture sequence | SDR Queue status → Nurture → enroll Person in a nurture **Sequence** (3 emails over 21 days); reply or demo request → exit sequence, back to SDR Queue | People, SDR Queue | **Attio Sequences (native)** |
| n8n | Supabase usage view → join Attio contracts → upsert Product Workspace by `workspace_id` (company linked by domain) → error branch: retry, then log to `sync_errors` + Slack | Product Workspaces | n8n + Attio API |

W6 automates follow-up sequences. Sequences send real email from a connected mailbox, so seed data uses test addresses only (`+test` aliases you own), and no sequence goes live without your approval.

**Demo priority (2–3 min in Video 1):** W1 (Typeform) → W3a (Closed Won handoff) → W4 (Usage Signal). W2a, W2b, W3b, W5 and W6 are shown in one sentence each.

### n8n workflow — endpoints used

Built: [`n8n/usage-sync.json`](../n8n/usage-sync.json) + [`n8n/usage-sync-error.json`](../n8n/usage-sync-error.json). Mock product DB: `warehouse/sql/03_product_mock.sql`, seeded by `scripts/seed_usage.py`. Runbook: [03-docs/runbooks/usage-sync.md](../03-docs/runbooks/usage-sync.md).

| Step | Node | Endpoint |
|---|---|---|
| 1 | Schedule trigger (hourly) | — |
| 2 | HTTP Request: fetch usage | Supabase `GET /rest/v1/workspace_usage_latest` (view: latest day per workspace, with 30-day WAU change and paywall hits worked out from history) |
| 3 | HTTP Request ×2 (run once): read contracts | Attio `POST /v2/objects/subscriptions/records/query` and `.../product_workspaces/records/query` |
| 4 | Code: build Attio values; seat utilisation = all seats used on the contract ÷ `seats_purchased` | — ([`n8n/build-attio-payloads.js`](../n8n/build-attio-payloads.js)) |
| 5 | HTTP Request: upsert workspace, company linked by domain in the same call | Attio `PUT /v2/objects/product_workspaces/records?matching_attribute=workspace_id`, batched 10/s |
| Error (row) | Retry 3×, 5 s apart → error output → row in `sync_errors` with payload → one Slack summary per run | Supabase `POST /rest/v1/sync_errors`; Slack incoming webhook |
| Error (run) | Error Trigger workflow → row in `sync_errors` + Slack alert with execution link | Same |

Rate limits and 429s are handled by the retry settings and batching; failed rows are logged with the payload so they can be replayed.

---

## 5a. Roles, teams and permissions (UI, Pro)

| Team | Members (demo) | Companies / People | Deals | Subscriptions / Workspaces | Lists |
|---|---|---|---|---|---|
| SDR | 2 | Read & write | Read | — | SDR Queue: full |
| AE | 2 | Read & write | Read & write | Read | — |
| CS | 1 | Read & write | Read | Read & write | Onboarding: full |
| Leadership | 1 | Read | Read | Read | All: read |
| RevOps (admin) | you | Full | Full | Full | Full |

- Workflows get explicit write access only to the objects they update (Attio workflows default to read-only).
- Trial seats: invite 2–3 test members (your own aliases) to show permission differences.

## 5b. Reports and dashboards (UI)

| Dashboard | Report | Type | Answers |
|---|---|---|---|
| **SDR** | Leads by source this month | Insight (bar, grouped by `lead_source`) | Where leads come from |
| | Speed-to-lead | Insight on SDR Queue (`first_touch_at` vs created) | Is the 1-hour SLA met |
| **Sales** | Pipeline by stage | Insight (deals, sum of `value`, grouped by `stage`) | Current pipeline |
| | Stage conversion | Funnel (deal `stage`) | Where deals drop |
| | Time in stage | Time in stage | Where deals stall |
| | Committee coverage | View: open deals past Discovery with no `economic_buyer` or `champion` | Which deals are single-threaded |
| **CS / Leadership** | ARR by plan | Insight (subscriptions, sum `live_arr`, grouped by `plan`; plans map 1:1 to segments). Not `arr`: that counts renewed terms twice. | Revenue mix |
| | Accounts by usage signal | Insight (workspaces grouped by `usage_signal`) | Expansion vs risk book |

Menu names follow [Set up an Insight report](https://attio.com/help/reference/managing-your-data/dashboard-and-reports/set-up-an-insight-report) (checked 2026-10-25). A report change stays private until you click **Save**.

### CS / Leadership dashboard (~20 min)

1. Sidebar → **Reports** → create a dashboard named `CS / Leadership — Revenue & health`.
2. **+ Add report** → **Insight**, named `ARR by plan`:

   | Setting | Value |
   |---|---|
   | Data source | Subscriptions |
   | Metric | Live ARR, aggregation **Sum** |
   | Grouped by | Plan |
   | Visualization | Bar; **Sorted by** Amount |

3. **+ Add report** → **Insight**, named `Accounts by usage signal`:

   | Setting | Value |
   |---|---|
   | Data source | Product Workspaces |
   | Metric | **Count** |
   | Grouped by | Usage signal |
   | Visualization | Bar (or Pie) |

4. Put the two reports on one row: press and hold a report title, then drag it beside the other. To resize, hover in the gap between them and drag the divider ([Customize dashboard layout](https://attio.com/help/reference/managing-your-data/dashboard-and-reports/dashboards#customize-dashboard-layout)).
5. New dashboards start with no workspace access. Click **Share** (top right) → add the CS and Leadership teams (5a) → **Read only**.

The dashboard also holds four more reports, built the same way: **Subscriptions by status** (Subscriptions, Count, grouped by Status), **Live ARR by status** (Subscriptions, Live ARR Sum, grouped by Status), **Expansion by reason** (Product Workspaces, Count, grouped by Expansion reason, filter Usage signal is Expansion) and **Seat utilisation by usage signal** (Product Workspaces, Seat utilisation Average, grouped by Usage signal). Layout: ARR by plan + Subscriptions by status; Live ARR by status; Accounts by usage signal + Expansion by reason; Seat utilisation by usage signal.

**Check against the seed data (2026-10-29 API read, 22 subscriptions, 20 workspaces):**

| Report | Expected | If wrong |
|---|---|---|
| ARR by plan | Enterprise $409,275 · Business $184,800 · Growth $79,920 · total $673,995 | A higher total means the metric is `arr`: the 4 Renewed and 2 Churned terms count. |
| Subscriptions by status | Active 10 · Renewed 4 · Onboarding 3 · Renewal Due 3 · Churned 2 | A total other than 22 means a filter is on. |
| Live ARR by status | Active $386,595 · Onboarding $167,000 · Renewal Due $120,400 | Renewed or Churned above $0 means the metric is `arr`. |
| Accounts by usage signal | Stable 9 · Expansion 7 · Risk 4 | Missing groups mean W4 or the usage seed has not run. |
| Expansion by reason | Seats 4 · Plan upgrade 3 | A "No value" bar means the Expansion filter is missing. |
| Seat utilisation by usage signal | Expansion 87.8 · Risk 78.2 · Stable 63.2 | Values in the hundreds mean the aggregation is Sum. |

Warehouse (`etl_attio.py`): `metrics_revenue` NRR 90.3%, GRR 82.5% on a 12-month cohort of 5 customers ($240,000); Polaris and Juniper churned.

No New department reason: the `usage_rule` formula has no rule for it (W4 option A not built), so the hourly sync would reset any seeded New department workspace to Stable.

## 5c. Warehouse sync — technical depth (Video 1, segment 5)

Story: CloudScale sells BI, so its own GTM data should live in a warehouse and be queryable in BI. Data flows both ways.

```
Attio ──ETL (nightly + webhooks)──▶ Supabase Postgres ──▶ SQL views ──▶ BI dashboard
  ▲                                          │
  └──────────rETL (n8n, hourly)──────────────┘  product usage → Product Workspaces
```

| Piece | Build |
|---|---|
| **ETL — full load** | Python script: for each object and list, page through `POST /v2/objects/{object}/records/query` and `POST /v2/lists/{list}/entries/query` (limit 500, offset), upsert into `raw.attio_records` (`object`, `record_id`, `values jsonb`, `synced_at`). |
| **ETL — incremental** | Attio webhook (`record.created`, `record.updated`, `list-entry.*`) → Supabase Edge Function → same upsert. Nightly full load catches missed events. |
| **Modelled layer** | SQL views: `dim_company`, `fct_deal`, `fct_subscription`, `fct_workspace_usage`; metrics view for ARR, NRR, GRR, win rate, cycle length. |
| **rETL** | Already the n8n usage sync above (warehouse → Attio). |
| **Show** | Run the script live, query `fct_subscription` for ARR by segment, show one chart. |

## 5d. Documentation method

| Layer | What | Where |
|---|---|---|
| In-tool | Every custom attribute gets a description in Attio (what it means, who sets it, source system) | Attio attribute settings (set via API on create) |
| Data dictionary | Generated from the API: object → attribute → type → options → description | `03-docs/data-dictionary.md`, regenerated by script after each change |
| Decision log | Why each modelling choice was made, options rejected | [`03-docs/decisions.md`](../03-docs/decisions.md) |
| Naming conventions | Below | `03-docs/conventions.md` |
| Runbooks | n8n sync, warehouse sync: what they do, how to replay failures | `03-docs/runbooks/` |
| Client handoff | 1-page "how to use your CRM" per role (SDR, AE, CSM) | `03-docs/handoff/` |

In a client engagement the data dictionary, conventions file and handoff pages ship at launch. In this repo, [field-guide.md](field-guide.md) is the data dictionary and the conventions are below.

**Naming conventions**
- Object and attribute slugs: `snake_case`, singular noun for references (`company`), plural for multi-references (`users`).
- Objects: plural display names (Subscriptions); lists: Title Case nouns (SDR Queue).
- Owners: `<role>_owner` (`sdr_owner`, `csm_owner`); timestamps end `_at`; dates end `_date`.
- Synced fields: description starts with "Synced from <system>"; never edited by hand.
- Views: `<Team> — <purpose>` (e.g. "AE — My open deals").

---

## 6. Build order

1. **Operator:** enable Deals (Settings → Objects).
2. **API:** create `subscriptions` and `product_workspaces` objects.
3. **API:** create attributes, select options and statuses (section 3).
4. **API:** create two-way relationships (section 2).
5. **API:** create lists and entry attributes (section 4).
6. **UI:** formula attributes, in this order: Subscriptions `live_arr`, then Companies `total_arr` and `active_users`. (`seat_utilisation` is synced by n8n, decision 16.)
7. **API:** seed demo data (~8 companies across segments, deals at each stage, customers with subscriptions and workspaces: one per expansion reason plus one risk case — see product profile §4).
8. **UI:** teams and permissions (5a), views per role, record pages.
9. **UI:** connect test mailbox, build nurture sequence, workflows W1–W6.
10. **UI:** reports and dashboards (5b).
11. **n8n:** usage sync (rETL) with error workflow.
12. **Script:** warehouse ETL + SQL views (5c).
13. **Script:** generate data dictionary; write conventions, runbooks and handoff docs (5d).

Script lives in `scripts/` and is idempotent: it reads existing slugs first and skips anything that exists.

---

## 7. Design decisions

All decisions live in the decision log: [03-docs/decisions.md](../03-docs/decisions.md), written as "I considered X, but did Y, because Z". Add new ones there, not here.
