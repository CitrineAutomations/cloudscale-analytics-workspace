# CloudScale Analytics — Field Guide

**Phase:** 02 Design · **Source of truth for slugs and types:** [build-plan.md §2–4](build-plan.md) · **Pricing:** [product-profile.md §2](../01-discovery/product-profile.md)

What each field means, what fills it, and what uses it. Every custom field has at least one entry under **Used by**; a field with nothing there should not exist.

**Set by:** *AE / SDR / CSM* = typed by that team · *W1–W6* = Attio workflow · *n8n* = hourly usage sync · *Formula* = Attio calculates it · *Std* = built into Attio.

---

## Companies

| Field | What it means | Set by | Used by |
|---|---|---|---|
| `name`, `domains` | The account and its web domains | Std / W1 | Matching Typeform leads and n8n workspaces to the right company |
| `lifecycle_stage` | Where the account is: Lead → MQL → SQL → Opportunity → Customer → Churned | W1 (MQL), SDR, W3a (Customer) | Views per team; funnel reporting |
| `segment` | Size band: Growth, Mid-Market, Enterprise | SDR at qualification (from employee count / expected ACV) | W1 round-robin routing to SDRs |
| `sdr_owner` | SDR working the account | W1 | SDR views, SDR Queue |
| `csm_owner` | CSM after the sale | W3a | W4 task and Slack alert recipient; CS views |
| `health` | Account health: Healthy, Watch, At risk. Worst signal across the company's workspaces. | W4 | CS views; renewal prep |
| `total_arr` | ARR across the company's live subscriptions (Onboarding, Active, Renewal Due) | Formula | Account views; the record page header |
| `active_users` | Weekly active users across all its workspaces | Formula | Record page; quick health read |
| `subscriptions` | The company's contract terms | Relationship | Record page; `total_arr` |
| `product_workspaces` | The company's product tenants | Relationship | Record page; `health` rollup |

## People

| Field | What it means | Set by | Used by |
|---|---|---|---|
| `name`, `email_addresses`, `job_title`, `company` | Who the person is and where they work | Std / W1 | Everything |
| `lifecycle_stage` | Same stages as Companies, for the individual | W1, SDR | SDR views; W6 exit rules |
| `lead_source` | How they first came in: Demo request, Content download, Webinar, Contact sales, Outbound, Referral | W1 (from Typeform) / SDR | "Leads by source" report |
| `utm_campaign`, `utm_source` | The marketing campaign and channel behind the lead | W1 (hidden Typeform fields) | Campaign attribution in the warehouse |
| `form_intent` | High (demo / contact sales) or Low (content download) | W1 | SDR prioritisation; low intent goes to nurture |
| `first_touch_at` | When an SDR first contacted them | SDR / W2b | "Speed-to-lead" report against the 1-hour SLA |
| `product_workspaces` | Workspaces this person uses | Relationship | Shows whether a deal's champion or evaluator actually uses the product |

## Deals

| Field | What it means | Set by | Used by |
|---|---|---|---|
| `name` | Deal name, e.g. "Acme — Expansion +30 seats" | AE | Views |
| `stage` | Pipeline stage, Demo Scheduled → Closed Won / Lost | AE | Pipeline, stage conversion and time-in-stage reports; W3a and W3b triggers |
| `owner` | The AE | Std / AE | AE views |
| `value` | **ARR this deal adds.** New = full ARR; Expansion = the increase; Renewal = the change at renewal (often $0). | AE | Pipeline report; expansion ARR in the warehouse |
| `associated_company`, `associated_people` | Account and everyone involved in the deal (end users, security, procurement) | Std / AE | Record page |
| `economic_buyer` | Person who signs off on budget | AE | Committee coverage view; business-case prep |
| `champion` | Person selling CloudScale internally | AE | Committee coverage view; Slack the AE if they leave |
| `technical_evaluator` | Data or IT lead running the evaluation | AE | Technical Evaluation stage; security review |
| `deal_type` | New, Expansion or Renewal | AE / W5 (Renewal) | W3a branch: New creates a subscription, Expansion updates one, Renewal creates the next term; NRR in the warehouse |
| `plan` | Plan being sold: Growth, Business, Enterprise | AE | Copied to the subscription by W3a; deal reports by plan (= segment) |
| `seats` | Total seats on the subscription after close | AE | Copied to `seats_purchased` by W3a |
| `price_per_seat` | Extra-user rate: list ($240 / $200) or negotiated | AE | Copied to the subscription by W3a; quoting future seat expansions |
| `resulting_arr` | Subscription ARR after this deal closes | AE | Copied to `arr` by W3a (no math inside the workflow) |
| `close_date` | Expected or actual close date | AE | Forecast views |
| `loss_reason` | Why a deal was lost | AE at Closed Lost | Loss analysis; W3b churn alert |
| `sourced_by` | SDR who booked the demo | W1 / SDR | SDR credit and pipeline-sourced reporting |
| `created_subscription` | The subscription this deal created (a new customer's first term, or the next term after a renewal) | W3a | Links revenue to the deal that won it |
| `renews_subscription` | The term this renewal deal renews | W5 | W3a marks it Renewed (won), W3b marks it Churned (lost) |
| `expands_subscription` | The subscription this expansion deal grows | AE (or CSM when opening it) | Tells W3a which subscription to update |

## Subscriptions

| Field | What it means | Set by | Used by |
|---|---|---|---|
| `name` | Contract term, e.g. "Acme — 2026–27" | W3a | Views |
| `status` | Onboarding → Active → Renewal Due → Renewed, or Churned | W3a (Onboarding for new; Active for a renewed term; Renewed on the old term), W3b (Churned), CSM (Active after onboarding), W5 (Renewal Due) | `live_arr`; CS views |
| `plan` | Current plan | W3a | ARR-by-plan report; paywall context for W4 |
| `arr` | Current annual recurring revenue on this term | W3a | `live_arr`; ARR report; warehouse ARR/NRR/GRR |
| `seats_purchased` | Seats paid for; never below the plan's included users | W3a | n8n seat-utilisation calculation |
| `price_per_seat` | Extra-user rate on this contract | W3a | CSM quotes seat expansions |
| `start_date`, `end_date` | Term dates. A renewed term starts on the old term's end date and runs 12 months. | W3a / AE | W5 opens the renewal deal 90 days before `end_date` |
| `auto_renew` | Renews automatically unless cancelled | AE | Renewal risk in CS views |
| `live_arr` | `arr` while the term is live (Onboarding, Active, Renewal Due); 0 once Renewed or Churned | Formula | Company `total_arr` |
| `company` | Account that owns it | W3a | `total_arr` |
| `originating_deal`, `renewal_deal`, `expansion_deals` | The deal that created this term (new or renewal), the deal renewing it, and deals that grew it | W3a / W5 / AE | Full revenue history; terms chain together through renewal deals |
| `product_workspaces` | Workspaces covered by this contract | n8n (first sync) | Seat utilisation |

## Product Workspaces

| Field | What it means | Set by | Used by |
|---|---|---|---|
| `name` | Workspace name, e.g. "Acme — US" | n8n | Views |
| `workspace_id` | The product's own tenant ID; unique | n8n | n8n upsert key, so syncs never create duplicates |
| `seats_used` | Users currently holding a seat | n8n | `seat_utilisation` |
| `seat_utilisation` | `seats_used ÷ seats_purchased` | n8n | W4 "Seats" expansion (≥ 90%) |
| `weekly_active_users` | Users active in the last 7 days | n8n | Company `active_users`; health |
| `wau_change_30d` | % change in weekly active users over 30 days | n8n | W4 risk (≤ −30%) |
| `departments_active` | Number of departments (user groups) with active users | n8n | W4 "New department" expansion |
| `paywall_hits_30d` | Attempts to use a feature above the plan in 30 days | n8n | W4 "Plan upgrade" expansion (≥ 10) |
| `last_active_at` | Last time anyone used the workspace | n8n | W4 risk (14 days inactive) |
| `last_synced_at` | Last successful n8n sync | n8n | Shows the data is fresh; spot a broken sync |
| `usage_signal` | Expansion, Stable or Risk | W4 | "Accounts by usage signal" report; `health` rollup |
| `expansion_reason` | Seats, New department or Plan upgrade | W4 | Tells the CSM what to pitch; warehouse measures which reasons convert |
| `company`, `subscription`, `users` | Owning account, covering contract, people using it | n8n | `health` and `active_users` rollups; seat utilisation |

---

## Lists (fields live on the list entry, not the record)

### SDR Queue (People)

| Field | What it means | Set by | Used by |
|---|---|---|---|
| `status` | New → Contacted → Qualified, or Nurture / Disqualified | W1 (New), SDR | W2a SLA alert; W2b first touch; W6 nurture trigger; time-in-stage |
| `sla_due_at` | When first contact is due (created + 1 hour) | W1 | W2a overdue alert |
| `dq_reason` | Why the lead was disqualified | SDR | Lead-quality feedback to marketing |

### Onboarding (Companies)

| Field | What it means | Set by | Used by |
|---|---|---|---|
| `stage` | Kickoff → Data Source Connected → First Dashboard Live → Team Trained → Live | W3a (Kickoff), CSM | Time-in-stage (time to value) |
| `subscription` | Contract being onboarded | W3a | Links onboarding to revenue |
| `kickoff_date`, `target_go_live`, `go_live_date` | Plan vs actual onboarding dates | CSM | Late-onboarding view |
