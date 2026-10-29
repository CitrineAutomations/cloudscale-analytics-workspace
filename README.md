# CloudScale Analytics — Attio build

An Attio CRM implementation for **CloudScale Analytics**, a fictional Series B B2B SaaS business-intelligence company ($12K–$120K ACV; inbound → SDR → AE → CSM). Built for the Attio Experts Program assessment.

The video walkthrough shows the workspace live. This repo holds everything behind it: the design, the decision log, the workflow specs, the n8n integration and the warehouse ETL.

## Map to the brief

| Brief section | What was built | Where |
|---|---|---|
| **1. Workspace setup** | Teams and permissions, naming conventions, role views (SDR Queue, Committee coverage, Onboarding), CS / Leadership dashboard, record page layouts | [build-plan.md §5a–§6](02-design/build-plan.md) |
| **2. Custom objects and data model** | Two custom objects, **Subscriptions** (one row per contract term) and **Product Workspaces** (one row per product tenant), linked two-way to Companies and Deals. Formula attributes roll contract ARR up to Total ARR on the company | [build-plan.md §1–§4](02-design/build-plan.md), [field-guide.md](02-design/field-guide.md), [decisions.md](03-docs/decisions.md) |
| **3. Workflows and automations** | 8 Attio workflows (W1–W6). W1 uses the **native Typeform** integration, W2–W5 post to **Slack**, W6 enrolls leads in **Attio Sequences**. Each one has a test table | [workflow-specs.md](02-design/workflow-specs.md) |
| **4. n8n integration** | Hourly product-usage sync (reverse ETL), Supabase → Attio. 9 steps, upsert on `workspace_id`, retries, failed-row log with replay, Slack summary, separate error workflow | [n8n/](n8n/), [runbook and API endpoints](03-docs/runbooks/usage-sync.md) |
| **5. Technical depth** | ETL out of Attio into a Postgres warehouse (raw JSON → SQL models → NRR, GRR, ARR by segment), plus scripts that build the data model through the Attio API | [scripts/](scripts/), [warehouse/sql/](warehouse/sql/) |

**Start with [decisions.md](03-docs/decisions.md).** Every modelling choice is written as "I considered X, but did Y, because Z."

## Data model

```
Companies ──< People
    │
    ├──< Deals ──── creates / renews / expands ───▶ Subscriptions
    │                                                    │
    ├──< Subscriptions (contract terms: plan, ARR, seats, dates, status)
    │                                                    │
    └──< Product Workspaces (usage, health) ─── paid for by ──┘
              └──>< People (workspace users)
```

- **Subscriptions** is separate from Deals. A deal is the sale; a subscription is the contract it creates. Each renewal is a new term, so the warehouse can rebuild any customer's ARR on any date (that's what makes NRR and GRR possible).
- **Product Workspaces** is separate from Companies because one customer can run several tenants, and usage signals (seat utilisation, paywall hits, WAU trend) belong to each tenant.
- **Statuses** for stages that move (deal pipeline, subscription lifecycle, SDR Queue). **Selects** for labels that don't (deal type, segment, usage signal).

## Data flow

```
Typeform ──▶ Attio (W1 routing) ──▶ Slack / Sequences
Product DB (Supabase) ──n8n hourly──▶ Attio Product Workspaces ──▶ W4 CSM tasks
Attio ──etl_attio.py──▶ Postgres raw.* ──SQL──▶ analytics.* (NRR, GRR, ARR by segment)
```

## Repo layout

| Folder | Contents |
|---|---|
| `01-discovery/` | GTM motion map and product profile: the requirements the build traces back to |
| `02-design/` | Build plan, field guide (data dictionary), workflow specs |
| `03-docs/` | Decision log, runbook for the n8n sync |
| `n8n/` | Importable workflow JSON (sync + error handler) and the payload-builder code |
| `scripts/` | Python: build the Attio data model from `workspace-spec.json`, seed demo data, run the warehouse ETL |
| `warehouse/sql/` | Raw tables, analytics models, mock product-usage database |

## Run it

Python 3.12. Copy `.env.example` to `.env` and fill it in.

```bash
pip install "psycopg[binary]"
python scripts/build_workspace.py   # objects, attributes, relationships, lists (idempotent)
python scripts/seed_demo.py         # demo companies, deals, subscriptions, workspaces
python scripts/seed_usage.py        # 31 days of product usage in Supabase
python scripts/etl_attio.py         # Attio → warehouse, then rebuild the models
```

Formula attributes, workflows, views and dashboards can't be created through the Attio API, so they're built in the UI from the specs in `02-design/`. To run the n8n sync, follow the setup steps in the [runbook](03-docs/runbooks/usage-sync.md).

All seed data is fictional. Email addresses use `example.com` subdomains, so none can reach a real inbox.
