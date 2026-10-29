# CloudScale Analytics — Product Profile

**Phase:** 01 Discovery · **Status:** v4 (pricing final) · **Feeds:** [02-design/build-plan.md](../02-design/build-plan.md) (Subscriptions, Product Workspaces, W4, n8n usage sync)

The brief calls CloudScale a "Business Intelligence Platform" and says nothing else about the product. This page defines just enough product for the usage attributes and expansion triggers to make sense. The assessment tests Attio, not product design, so this stays small.

**Rule:** a usage field goes into Attio only if a workflow, view or report uses it. Everything else stays in the warehouse or is left out.

CloudScale is **modelled on** two real BI products. It is inspired by them, not a copy of either.

| Reference | What we borrowed | Source (checked 2026-10-16) |
|---|---|---|
| **Metabase** | Pricing shape (platform fee + users, features gated by plan) and its usage-analytics data model (what a BI product can log) | [metabase.com/pricing](https://www.metabase.com/pricing), [Usage analytics reference](https://www.metabase.com/docs/latest/usage-and-performance-tools/usage-analytics-reference) |
| **Tableau** | Sanity check on per-seat price levels only | tableau.com/pricing blocks automated fetches; 2026 list prices from [DashboardFox](https://dashboardfox.com/guides/bi-software-pricing-guide/tableau-pricing-explained/). |

---

## 1. The product in one paragraph

A company connects its data sources (Postgres, Snowflake, Salesforce, Stripe). Analysts build dashboards and the rest of the company views them. Each customer has one or more **workspaces**, and users belong to **departments** (Finance, Sales, Ops). Higher plans unlock SSO, row-level security and embedding dashboards in the customer's own app.

## 2. Pricing (final, built backward from the brief's $12K–$120K ACV)

The base price includes a minimum number of users (Metabase's model). Extra users are billed per user per year. One seat type: anyone who logs in counts. Higher plans unlock features.

| Plan | Base price (includes) | Extra user / yr | ACV | Segment | Adds |
|---|---|---|---|---|---|
| **Growth** | $12,000 (25 users) | $240 | $12K–$30K | Growth | Core product |
| **Business** | $30,000 (75 users) | $240 | $30K–$72K | Mid-Market | SSO, row-level security |
| **Enterprise** | $75,000 (225 users) | $200, negotiable | $75K–$120K+ | Enterprise | Embedded analytics, audit logs, dedicated CSM |

**ARR = base price + (seats − included users) × extra-user price**

- Seats can't go below the plan's included users, so no deal comes in under $12K.
- Per user that's $22–$40 a month, between Tableau Viewer (~$15) and Creator (~$75).
- The $12K floor fits a sales-led motion (SDRs, AEs, 30–60 day cycle): deals much smaller than that don't pay back the cost of selling them.

**Expansion has a price:** extra seats at the plan's rate, or a plan upgrade for the features. Example: Acme on Business with 120 seats = $30,000 + 45 × $240 = $40,800. Adding 30 seats = +$7,200. Moving to Enterprise at 150 seats = $75,000 → +$27,000.

## 3. Usage signals

**Synced to Attio (each one drives W4 or a report):**

| Attribute | From (Metabase equivalent) | Drives |
|---|---|---|
| `seats_used` | People (Is Active) | Seat utilisation |
| `seat_utilisation` | Calculated by n8n: `seats_used / seats_purchased` | W4 seat expansion |
| `weekly_active_users`, `wau_change_30d` | View log + Query log | W4 risk; Company `active_users` |
| `departments_active` | Group Members | W4 new department |
| `paywall_hits_30d` | Activity log (permission failures) | W4 plan upgrade |
| `last_active_at` | People (Last Login) | W4 risk |

**Warehouse only:** dashboards and questions created, query volume and errors, scheduled reports and alerts, embedded views, AI token use, stale content. They're useful for CS analysis in BI but don't trigger anything in the CRM.

**Left out:** admin and security events (MFA, API keys, settings), performance (query time, cache), transforms, uploads, comments.

## 4. Triggers (W4)

| Signal | Rule (starting values, tune with CS) | `expansion_reason` |
|---|---|---|
| Seats nearly full | `seat_utilisation` ≥ 90% | Seats |
| New department | `departments_active` went up | New department (new stakeholders for the expansion deal) |
| Wants a higher plan | `paywall_hits_30d` ≥ 10 | Plan upgrade |
| **Risk** | `wau_change_30d` ≤ −30% or no activity for 14 days | — (Slack alert to CSM) |

- **Fire on change only.** W4 acts when `usage_signal` or `expansion_reason` changes, so the CSM gets one task per signal, not one per hourly sync.
- **Company rollup.** Company `health` = worst signal across its workspaces.

