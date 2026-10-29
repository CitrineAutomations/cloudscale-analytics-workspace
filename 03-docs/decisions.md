# CloudScale Analytics — Decision Log

Every design choice in the build, written as **I considered X, but did Y, because Z.** Add new decisions at the bottom of their section with the next number. If a decision is reversed, don't delete it: mark it **Superseded by #N** and add the new one.

Related: [build-plan.md](../02-design/build-plan.md) · [field-guide.md](../02-design/field-guide.md) · [product-profile.md](../01-discovery/product-profile.md)

---

## Data model

1. **I considered** putting subscription details on the Company, **but made** Subscriptions its own object, **because** a company holds several contract terms over time, and keeping each term separate gives clean renewal history and lets the warehouse calculate GRR and NRR. *(2026-10-16)*
2. **I considered** storing usage on the Company, **but made** Product Workspaces its own object, **because** one company can run several product tenants, and the hourly sync needs a stable record to match on `workspace_id`. *(2026-10-16)*
3. **I considered** a Buying Committee list and a junction object, **but put** Economic Buyer, Champion and Technical Evaluator as fields on the Deal, **because** AEs see the committee where they already work, coverage becomes a simple filter, and it avoids extra structure. I'd add a `Deal Stakeholders` junction object if reps need sentiment or more people per role. *(2026-10-17; supersedes the earlier Buying Committee list)*
4. **I considered** extending the subscription at renewal, **but create** a new Subscription record per term, **because** each term keeps its own ARR, so price changes and churn show up clearly. *(2026-10-17)*
5. **I considered** keeping segment on both Companies and Deals, **but kept it** only on Companies, **because** each plan maps to exactly one segment, so deal reports group by plan and the two values can't drift apart. *(2026-10-17)*
6. **I considered** counting only Active subscriptions in `total_arr`, **but included** Onboarding and Renewal Due, **because** a new customer's revenue should count from the day they sign. *(2026-10-17)*
7. **I considered** making Onboarding a custom object, **but made it** a list on Companies, **because** onboarding is a process a company goes through once, not a long-lived record, and it shouldn't use up a custom-object slot. *(2026-10-16)*
8. **I considered** select fields for every pipeline, **but used** status attributes for deal stage, onboarding stage and the SDR Queue, **because** status attributes give time-in-stage reporting, which is where cycle time matters. *(2026-10-16)*

## Product and pricing

9. **I considered** making up generic usage metrics, **but modelled** CloudScale on Metabase's pricing and usage-analytics data, **because** grounding it in a real BI product meant no signals were missed and every field traces back to something a customer does. *(2026-10-16)*
10. **I considered** copying Metabase's or Tableau's prices, **but built** custom pricing backward from the $12K–$120K ACV, **because** the deal size is set, and a sales-led company with SDRs and AEs can't sell $4K deals profitably. *(2026-10-16)*
11. **I considered** a platform fee plus per-user pricing, **but went with** a base price that includes a minimum number of users, **because** it matches how Metabase sells, guarantees the $12K floor, and is one sentence to explain. *(2026-10-16)*
12. **I considered** Tableau-style Creator and Viewer seats, **but used** a single seat type, **because** it removed three fields, and the "new department" signal already captures usage spreading across a company. *(2026-10-16)*

## Usage and expansion

13. **I considered** syncing everything a BI product logs into Attio, **but sync** only nine signals and keep the rest in the warehouse, **because** every CRM field should drive a workflow, view or report, and raw product data is noise for reps. *(2026-10-16)*
14. **I considered** six expansion reasons and five risk rules, **but kept** three reasons (Seats, New department, Plan upgrade) and one risk rule, **because** they cover the main ways CloudScale grows and the demo stays focused. *(2026-10-16)*
15. **I considered** triggering W4 on every usage update, **but fire it** only when the signal changes, **because** the hourly sync would otherwise create a duplicate CSM task every hour. *(2026-10-16)*
16. **I considered** calculating seat utilisation with an Attio formula, **but calculate it** in n8n, **because** formulas that pull values from a related record were a risk, and a synced number is more reliable. *(2026-10-16)*

## Workflows and pricing fields

17. **I considered** having W3a calculate ARR, **but the AE enters** `resulting_arr` on the deal and W3a copies it, **because** it keeps the workflow to copying values and avoids depending on math inside Attio workflows. *(2026-10-16)*
18. **I considered** storing the platform fee or included users as fields, **but left them** in the docs and stored only `price_per_seat`, **because** they're fixed by plan, while the per-seat price is negotiated on Enterprise and needed to quote expansions. *(2026-10-16)*

## Integrations and data

19. **I considered** Apollo enrichment for the n8n workflow, **but built** the product usage sync, **because** it ties directly to the expansion requirement and doubles as reverse ETL. *(2026-10-16)*
20. **I considered** Snowflake or BigQuery, **but used** a separate Supabase Postgres project, **because** it's enough at CloudScale's scale, it's already in my stack, and the same raw-to-modelled-views pattern moves to Snowflake when volume grows. *(2026-10-16)*
21. **I considered** reusing my existing local Supabase database, **but set up** a separate cloud project, **because** Attio webhooks and n8n need a public URL, and demo data shouldn't mix with real data. *(2026-10-16)*
22. **I considered** one Company formula that sums ARR only for live subscriptions, **but split it** into a Subscriptions `live_arr` formula plus a plain `sum()` on Companies, **because** Attio formulas can't filter an aggregation, and the helper also lets views show which terms count toward ARR. *(2026-10-19)*
23. **I considered** a separate n8n step that looks up the company by domain before creating a workspace, **but link it** by domain inside the upsert itself, **because** Attio accepts a record reference by unique attribute, which saves one API call per workspace and a branch for "first sync only". *(2026-10-20)*
