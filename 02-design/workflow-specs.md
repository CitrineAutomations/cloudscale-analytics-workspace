# CloudScale Analytics — Workflow Specs (W1–W6)

**Phase:** 02 Design · **Status:** Built · **Input:** [build-plan.md §5](build-plan.md#5-workflows-ui--mapped-to-the-build), [field-guide.md](field-guide.md), [product-profile.md §4](../01-discovery/product-profile.md#4-triggers-w4)

The Attio API cannot create workflows. This page is the click-by-click spec for building W1–W6 in the Attio workflow builder (build order step 9). Block names match the current [Workflows block library](https://attio.com/help/reference/automations/workflows/workflows-block-library) (checked 2026-10-22).

**Conventions on this page**

- `{Block N > field}` is a variable from the output of block N. `{Trigger > field}` is a variable from the trigger.
- **Verify** marks a builder behaviour that the docs do not confirm. Each one has a fallback.
- Slack channels: `#sdr-leads`, `#cs-handoffs`, `#cs-alerts`. Create them before you connect Slack.
- Workflow names follow `W<n> — <purpose>`, so the list in Settings → Workflows sorts in build order.

---

## 0. Before you build

| Check | Why |
|---|---|
| Slack connected (admin only, one Slack workspace) | W2a, W3a, W3b, W4 and W5 post to channels |
| Typeform connected as a **member connection** for the RevOps admin | The Form submitted trigger runs as one member |
| Form "CloudScale — Talk to us" exists (§W1 form) | W1 trigger needs a form |
| Teams `SDR — Growth`, `SDR — Enterprise`, `CS` exist | Round robin blocks pick from teams |
| Sequence "Nurture — 21 days" exists, sender has **delegated sending** on | Enroll in sequence fails without it |
| Test mailbox connected; every seed address is `@*.example.com` or your own `+test` alias | Sequences send real email |
| Write access for workflows | **Verify.** The build plan (§5a) assumes workflows start read-only. The current docs do not say so. If a block fails with a permission error, grant the workflow write access to the object it updates. |

**What the Slack app can do.** The app has two blocks: **Post message to channel** and **Post actions to channel**. It has no direct-message block. So every "ping a person" step in this spec uses two parts. A channel post gives the team visibility. An Attio **Create task** assigned to the person sends the personal notification. A fixed person, such as the SDR lead, can be mentioned with `<@SLACK_MEMBER_ID>` in the message text.

---

## Summary

| # | Name | Trigger | Integration | Runs |
|---|---|---|---|---|
| W1 | Inbound lead (Typeform) | Typeform Form Submitted | **Typeform (native)** | Per submission |
| W2a | New Lead Alert | Record added to list (SDR Queue) | **Slack (native)** | Per new queue entry |
| W2b | Speed-to-lead | List entry updated (SDR Queue, `status`) | — | Per status change |
| W3a | Closed Won handoff | Attribute value changed (Deals, `stage`) | Slack | Per stage change |
| W3b | Lost renewal → Churned | Attribute value changed (Deals, `stage`) | Slack | Per stage change |
| W4 | Usage Signal | Record updated (Product Workspaces, `last_synced_at`) | Slack | Hourly × workspaces |
| W5 | Renewal opens | Recurring schedule (daily 07:00) | Slack | Once a day |
| W6 | Nurture sequence | List entry updated (SDR Queue, `status`) | **Attio Sequences** | Per status change |

Names match the Attio Workflows list exactly. Attio allows one trigger per workflow, so the lead alert (W2a) and the first-touch stamp (W2b) are separate workflows. W3b shares W3a's trigger but handles only lost renewals, so W3a stays focused on Closed Won.

**Credits.** Each run uses workspace credits. W4 runs once per workspace for every sync: 6 workspaces × 24 × 30 ≈ 4,300 runs a month. W4 does its cheap checks first and stops early when nothing changed. If credits run short on the trial, change the n8n schedule to every 6 hours. W4 does not need any change.

---

## W1 — Inbound lead (Typeform)

**Purpose:** create or update the person and company from a form fill, set source and intent, route to an SDR (or to the CSM for an existing customer), and put the lead in the SDR Queue or in nurture.

### The form

| Question | Typeform type | Maps to |
|---|---|---|
| First name, Last name | Short Text | Person `name` |
| Work email | Email | Person `email_addresses` (match key) |
| Job title | Short Text | Person `job_title` |
| Company name | Short Text | Company `name` |
| Company website | Website (outputs a domain) | Company `domains` (match key) |
| Company size | Dropdown: 1–200, 201–1,000, 1,000+ | Company `segment`: Growth, Mid-Market, Enterprise |
| What can we help with? | Dropdown: Book a demo, Talk to sales, Get the BI buyer's guide | `lead_source` + `form_intent` (step 5) |
| `utm_source`, `utm_campaign` | Hidden fields | Person `utm_source`, `utm_campaign` |

**Verify:** the Typeform app docs list answer types but say nothing about hidden fields. Submit one test with `?utm_source=test&utm_campaign=test` on the form URL. Then check the trigger outputs. **Fallback:** drop the two UTM mappings. UTMs then come from web analytics in the warehouse.

Company size drives the segment because routing happens before an SDR has qualified the lead. The SDR corrects `segment` at qualification if the answer was wrong.

### Blocks

| # | Block | Configuration |
|---|---|---|
| T | **Typeform Form Submitted** | Connection: RevOps admin. Form: CloudScale — Talk to us |
| 1 | **Create or update record** | Object: Companies. Matching attribute: `domains` = `{T > Company website}`. Set `name` = `{T > Company name}`. Replace existing values: off |
| 2 | **Create or update record** | Object: People. Matching attribute: `email_addresses` = `{T > Work email}`. Set `name`, `job_title`, `company` = `{1 > record}`, `utm_source`, `utm_campaign` |
| 3 | **If** | `{1 > lifecycle_stage}` is Customer → **true path 3a**. False → step 4 |
| 3a | **Create task** | "Existing customer {2 > name} asked: {T > What can we help with?}". Assignees: `{1 > csm_owner}`. Due: Adjust time +1 day. Linked records: person, company. **End.** An existing customer goes to the CSM as a possible expansion, not to an SDR |
| 4 | **If** | `{1 > segment}` is empty → **Switch** on `{T > Company size}` → **Update record** Companies `segment` (Growth / Mid-Market / Enterprise). The paths merge into step 5 |
| 5 | **Switch** on `{T > What can we help with?}` | Book a demo → `lead_source` Demo request, `form_intent` High. Talk to sales → Contact sales, High. Buyer's guide → Content download, Low. Each path is one **Update record** on People. Set `lead_source` only when it is empty (an **If** before the update), because it records how the person *first* came in. The paths merge |
| 6 | **Update record** ×2 | Companies and People: `lifecycle_stage` = MQL, but only when the current value is empty or Lead (an **If** before each update). A later stage is never moved back |
| 7 | **If** | `{1 > sdr_owner}` is not empty → skip to step 8. The account already has an SDR. Empty → **Switch** on company `segment`: Growth → **Round robin** (team `SDR — Growth`); Mid-Market or Enterprise → **Round robin** (team `SDR — Enterprise`). Each path → **Update record** Companies `sdr_owner` = `{Picked user}` |
| 8 | **Adjust time** | Timestamp: `{T > submitted at}`. Offset: +1 hour → `sla_due_at` |
| 9 | **If** | `form_intent` is High |
| 9a | true → **Exit from sequence** | Sequence: Nurture — 21 days. Recipient: `{2 > record}`. This step does not fail when the person is not enrolled. A nurtured lead who asks for a demo leaves the sequence here |
| 9b | true → **Add record to list** | SDR Queue. Record: `{2 > record}`. `status` = New, `sla_due_at` = `{8 > timestamp}` |
| 9c | false → **Add record to list** | SDR Queue. `status` = Nurture. No SLA |
| 9d | false → **Enroll in sequence** | Nurture — 21 days. Recipient: `{2 > record}`. Sender: the test mailbox |

**Why step 9d enrolls directly:** W6 fires on a status *change*. List entry updated does not fire for values set when the entry is created. So a low-intent lead must be enrolled in W1.

**Repeat submissions:** every high-intent form fill adds a new SDR Queue entry. Attio allows several entries for one person. Each inbound request gets its own SLA and its own speed-to-lead data point.

### Test

| Case | Submit as | Expect |
|---|---|---|
| New lead, new domain | `+test` alias, `newco.example.com`, 201–1,000, Book a demo | New company (Mid-Market, MQL, SDR from the Enterprise pod), new person (Demo request, High, MQL), SDR Queue entry New with `sla_due_at` = submit + 1 h |
| Existing account with an owner | Laura Kim's company `tidewater.example.com`, Talk to sales | Company stays SQL. `sdr_owner` is unchanged. A new queue entry exists |
| Existing customer | `helix.example.com`, Book a demo | CSM task only. No queue entry. Lifecycle stays Customer |
| Low intent | `kestrel.example.com`, Buyer's guide | Queue entry Nurture. Enrolled in the sequence. `lead_source` stays Content download (it was set already) |

---

## W2a — New Lead Alert

**Purpose:** tell the SDR about a new lead now, and escalate to the SDR lead if nobody has touched the lead by `sla_due_at`.

| # | Block | Configuration |
|---|---|---|
| T | **Record added to list** | List: SDR Queue |
| 1 | **Filter** | Entry `status` is New. Nurture entries from W1 stop here |
| 2 | **Find records** | Companies. Filter: record = `{T > parent record > company}`. Limit 1. **Verify:** if the variable picker reaches Person > Company > SDR owner directly, skip this block |
| 3 | **Post message to channel** | `#sdr-leads`: "New {form_intent} lead: {person name}, {job title} at {company name} ({segment}). Owner: {sdr_owner}. First touch due {sla_due_at}." |
| 4 | **Create task** | "First touch: {person name} ({company name})". Assignees: `{2 > sdr_owner}`. Due: `{T > sla_due_at}`. Linked records: person, company. Attio notifies the assignee |
| 5 | **Delay until** | `{T > sla_due_at}` |
| 6 | **Find list entries** | SDR Queue. Filter: entry = `{T > entry}` AND `status` is New. Limit 1. The search reads the entry again, because the status may have changed during the delay |
| 7 | **Filter** | `{6 > Number of matches}` > 0 |
| 8 | **Post message to channel** | `#sdr-leads`: "<@SDR_LEAD_SLACK_ID> SLA missed: {person name} at {company name} has had no first touch for 1 hour. Owner: {sdr_owner}." |

The SLA is one clock hour. It ignores business hours. The SDR lead sees nights and weekends as misses. Leave it that way for the demo. In production, give W1 a working-hours **Switch** before step 8.

### Test

1. Submit the W1 "new lead" case. Expect a Slack post and a task within a minute.
2. To test the escalation without a one-hour wait, temporarily change W1 step 8 to +2 minutes and publish. Leave the entry at New. Expect the SLA-missed post after 2 minutes. Change step 8 back to +1 hour.
3. Run step 2 again and set the entry to Contacted before the delay ends. Expect no escalation.

---

## W2b — Speed-to-lead

**Purpose:** set `first_touch_at` when the SDR first moves a lead out of New. The speed-to-lead report compares this field with the entry's created time.

| # | Block | Configuration |
|---|---|---|
| T | **List entry updated** | List: SDR Queue. Attribute: `status` |
| 1 | **Filter** | Previous value is New AND parent person `first_touch_at` is empty |
| 2 | **Update record** | People: `{T > parent record}`. `first_touch_at` = `{T > timestamp}` |

Optional, if time allows: when the new status is Qualified, also set person `lifecycle_stage` = SQL. The field guide gives this to the SDR today.

---

## W3a — Closed Won handoff

**Purpose:** turn a closed deal into subscription changes, start onboarding for a new customer, and hand off to CS.

**Trigger choice:** Attribute value changed fires on creation *and* on update. So a deal that is created already at Closed Won (an import, for example) still runs W3a. Record updated does not fire for values set at creation.

| # | Block | Configuration |
|---|---|---|
| T | **Attribute value changed** | Object: Deals. Attribute: `stage` |
| 1 | **Switch** | Case 1: stage Closed Won AND `deal_type` New. Case 2: Closed Won AND Expansion. Case 3: Closed Won AND Renewal. Default: end. A lost renewal is handled by W3b |

### Case 1 — New customer

| # | Block | Configuration |
|---|---|---|
| 1.1 | **Filter** | `{T > created_subscription}` is empty. A deal that leaves Closed Won and comes back does not create a second subscription |
| 1.2 | **Adjust time** | `{T > close_date}` +12 months, −1 day → end date. **Verify:** Adjust time accepts a date attribute. **Fallback:** leave `end_date` empty; the CSM sets it (build plan §0) |
| 1.3 | **Create record** | Subscriptions. `name` = "{company name} — {close_date}". `status` Onboarding. `plan`, `seats_purchased` = `seats`, `price_per_seat`, `arr` = `resulting_arr` (decision 17). `start_date` = `close_date`. `end_date` = `{1.2}`. `company` = `associated_company`. `originating_deal` = `{T > record}`. The two-way link fills the deal's `created_subscription` |
| 1.4 | **If** | Company `csm_owner` is empty → **Round robin** (team CS) → **Update record** Companies `csm_owner` = `{Picked user}` |
| 1.5 | **Update record** | Companies: `lifecycle_stage` = Customer. Also People: `economic_buyer`, `champion`, `technical_evaluator` → Customer (one Update record each; skip any that are empty) |
| 1.6 | **Add record to list** | Onboarding. Record: company. `stage` Kickoff. `subscription` = `{1.3 > record}` |
| 1.7 | **Post message to channel** | `#cs-handoffs`: "Closed Won: {company} on {plan}, {seats} seats, {resulting_arr} ARR. CSM: {csm_owner}. AE: {owner}. Champion: {champion}. Economic buyer: {economic_buyer}. Onboarding started." |
| 1.8 | **Create task** | "Book kickoff with {company}". Assignees: CSM. Due: close + 2 days. Linked: company, deal |

### Case 2 — Expansion

| # | Block | Configuration |
|---|---|---|
| 2.1 | **If** | `expands_subscription` is empty → **Create task** for the deal `owner`: "Link the subscription on {deal name}, then move it to Closed Won again", plus a post to `#cs-alerts`. **End** |
| 2.2 | **Update record** | Subscriptions: `{T > expands_subscription}`. Set `plan`, `seats_purchased` = `seats`, `price_per_seat`, `arr` = `resulting_arr` |
| 2.3 | **Post message to channel** | `#cs-handoffs`: "Expansion won: {company} now {seats} seats on {plan}, {resulting_arr} ARR (+{value})." |

Expansion has no duplicate guard, because running it twice writes the same values twice.

### Case 3 — Renewal won

| # | Block | Configuration |
|---|---|---|
| 3.1 | **Filter** | `created_subscription` is empty (duplicate guard) |
| 3.2 | **If** | `renews_subscription` is empty → task + `#cs-alerts` post as in 2.1. **End** |
| 3.3 | **Find records** | Subscriptions. Filter: record = `{T > renews_subscription}`. Limit 1. This step reads the old term's `end_date` |
| 3.4 | **Update record** | Old term: `status` = Renewed |
| 3.5 | **Adjust time** | `{3.3 > end_date}` +12 months → new end date (same **Verify** as 1.2) |
| 3.6 | **Create record** | Subscriptions. `status` Active (no onboarding). `plan`, `seats_purchased`, `price_per_seat`, `arr` from the deal. `start_date` = `{3.3 > end_date}`, `end_date` = `{3.5}`. `company`. `originating_deal` = `{T > record}` |
| 3.7 | **Find records** | Product Workspaces. Filter: `subscription` = old term |
| 3.8 | **Loop** over `{3.7}` → **Update record** | Product Workspaces: `subscription` = `{3.6 > record}`. The n8n sync calculates seat utilisation from the linked term. Without this step, utilisation would use the old term's seats |
| 3.9 | **Post message to channel** | `#cs-handoffs`: "Renewed: {company}, {plan}, {resulting_arr} ARR, new term to {3.5}." |

### Test

| Case | Do | Expect |
|---|---|---|
| New | Move **Orbit Payments — New** to Closed Won | Subscription Onboarding, ARR = `resulting_arr`, end = close + 12 months − 1 day. Orbit is Customer with a CSM, on the Onboarding list at Kickoff. Slack post. CSM task |
| Duplicate guard | Move Orbit to Negotiation, then back to Closed Won | No second subscription |
| Expansion | Move **Northwind — Expansion +30 seats** to Closed Won | `nw26` has 150 seats and the new ARR. `total_arr` updates |
| Renewal won | Move **Corvid Media — Renewal 2027** to Closed Won | `cv26` Renewed. A new term starts 2026-12-31. `ws-corvid-main` is linked to the new term |

Run the tests in that order. After the tests, reseed (`python scripts/seed_demo.py`) so the demo starts clean. **Verify:** the seed script matches deals and subscriptions by name. Records that W3a created during testing stay in place. Delete them by hand before reseeding.

---

## W3b — Lost renewal → Churned

**Purpose:** when a renewal is lost, end the contract and update the account, so Total ARR drops on its own.

| # | Block | Configuration |
|---|---|---|
| T | **Attribute value changed** | Object: Deals. Attribute: `stage` |
| 1 | **Filter** | Stage is Closed Lost AND `deal_type` is Renewal |
| 2 | **Update record** | Subscriptions `{T > renews_subscription}`: `status` = Churned |
| 3 | **Find records** | Subscriptions. Filter: `company` = deal company AND `status` is Onboarding, Active or Renewal Due. This step runs after step 2, so the churned term is not counted |
| 4 | **If** | `{3 > Number of matches}` = 0 → **Update record** Companies `lifecycle_stage` = Churned |
| 5 | **Post message to channel** | `#cs-alerts`: "Churned: {company}, {loss_reason}. {old term ARR} ARR lost." |

### Test

| Case | Do | Expect |
|---|---|---|
| Renewal lost | After the W3a tests, reset Corvid, then move **Corvid Media — Renewal 2027** to Closed Lost with a loss reason | `cv26` Churned. Corvid lifecycle Churned. `#cs-alerts` post |

---

## W4 — Usage Signal

**Purpose:** after each usage sync, work out the workspace's signal. Act only when the signal or the reason changes (decision 15). Roll the result up to company `health`.

**Trigger choice:** the n8n sync sets `last_synced_at` on every run. So this attribute is a reliable hourly tick. W4 updates only `usage_signal` and `expansion_reason`, so it cannot trigger itself. A brand-new workspace is created by the sync, not updated. W4 first evaluates it on the next run.

| # | Block | Configuration |
|---|---|---|
| T | **Record updated** | Object: Product Workspaces. Attribute: `last_synced_at` |
| 1 | **Adjust time** | `{T > timestamp}` −14 days → idle cutoff |
| 2 | **Switch** (first true case wins) | **Risk:** `wau_change_30d` ≤ −30 OR `last_active_at` before `{1}`. **Seats:** `seat_utilisation` ≥ 90. **Plan upgrade:** `paywall_hits_30d` ≥ 10. **New department:** see the note below. **Default:** Stable |
| 3 | per path: **If** | Current `usage_signal` and `expansion_reason` already equal this path's values → **end**. Most hourly runs stop here |
| 4 | per path: **Update record** | `usage_signal` = Risk / Expansion / Expansion / Expansion / Stable. `expansion_reason` = empty / Seats / Plan upgrade / New department / empty |
| 5 | Risk path: **Post message to channel** | `#cs-alerts`: "Risk: {workspace name} ({company}). WAU {wau_change_30d}% in 30 days, last active {last_active_at}." |
| 5 | Expansion paths: **Find records** → **Create task** | Find the company (as W2a step 2). Task: "Expansion signal on {workspace name}: {expansion_reason}. Seats {seat_utilisation}%, paywall hits {paywall_hits_30d}, departments {departments_active}." Assignees: company `csm_owner`. Due: +3 days. Linked: company, workspace |
| 6 | all change paths merge: **Find records** | Product Workspaces. Filter: `company` = this company AND `usage_signal` is Risk |
| 7 | **If** | `{6 > Number of matches}` > 0 → **Update record** Companies `health` = At risk. Else, if company `health` is At risk → **Update record** `health` = Healthy |

**Order of rules.** Risk comes first. A workspace that is shrinking is not an expansion opportunity, even with full seats. Among the expansion rules, Seats is checked first because it has the shortest sales path (a seat add-on with no new stakeholders).

**Health values.** W4 sets only At risk and Healthy. Watch is the CSM's manual flag. W4 does not overwrite Watch, because step 7 writes Healthy only when the company is At risk.

**Verify:** the Switch condition can compare `last_active_at` with the Adjust time output. **Fallback:** drop the idle rule from the Switch. The WAU rule still catches Corvid (−45%).

**New department rule — needs a decision.** The rule is "`departments_active` went up". W4 cannot see the previous value: Record updated returns previous values only for the trigger attribute, which is `last_synced_at`. Options:

| Option | Change | Effect |
|---|---|---|
| **A (recommended)** | Add `departments_change_30d` (number) to the view, the n8n payload and Attio, the same way as `wau_change_30d`. Rule: `departments_change_30d` > 0. Seed Brightpath with 2 departments for the first 20 days and 3 after that | Uses the same pattern as WAU. Stays true for 30 days and then returns to Stable. That return is one more change, which fires one more time |
| B | Separate workflow triggered on `departments_active` (previous vs new) | The next hourly W4 run sets the signal back to Stable. The signal then flip-flops |
| C | Drop the rule for the demo | Two expansion reasons instead of three. Contradicts decision 14 |

Without option A, the first sync sets Brightpath (seeded as New department, departments flat at 3) to Stable.

### Test

1. Reseed usage (`python scripts/seed_usage.py`). Run the n8n sync once. Expect **no** tasks or Slack posts, because every seeded signal matches the seeded data.
2. In Supabase: `update workspace_usage_daily set paywall_hits = paywall_hits + 12 where workspace_id = 'ws-quantum-us' and usage_date = current_date;`. Run the sync. Expect Quantum US to show Expansion / Plan upgrade, one CSM task, and Quantum health still Healthy.
3. Run the sync again with no data change. Expect no new task.
4. Set Quantum US WAU today to 50% of 30 days ago. Run the sync. Expect Risk, a `#cs-alerts` post, and Quantum health At risk. Reseed to undo the change.

---

## W5 — Renewal opens

**Purpose:** 90 days before a term ends, open a renewal deal, link it, and set the term to Renewal Due.

**Trigger choice:** a daily schedule plus a search. A **Delay until** per subscription would hold one run for up to nine months, and every edit to `end_date` would need a new run.

| # | Block | Configuration |
|---|---|---|
| T | **Recurring schedule** | Daily, 07:00, workspace timezone |
| 1 | **Adjust time** | `{T > timestamp}` +90 days → cutoff |
| 2 | **Find records** | Subscriptions. Filter: `status` is Active AND `end_date` on or before `{1}` AND `renewal_deal` is empty. Limit 500. **Verify:** the filter accepts a variable date. **Fallback:** filter only on status and `renewal_deal`, and put an **If** on `end_date` inside the loop |
| 3 | **Loop** over `{2 > Matching records}` | |
| 3.1 | **Find records** | Companies: the subscription's `company`. This step reads `csm_owner` |
| 3.2 | **Create record** | Deals. `name` = "{company} — Renewal". `deal_type` Renewal. `stage` Business Case & Proposal. `owner` = CSM. `associated_company`. `plan`, `seats`, `price_per_seat`, `resulting_arr` = the term's current values (a flat renewal by default). `value` = 0. `close_date` = `end_date`. `renews_subscription` = current item. The two-way link fills `renewal_deal` |
| 3.3 | **Update record** | Subscription: `status` = Renewal Due |
| 3.4 | **Create task** | "Renewal opened: {company}, ends {end_date}". Assignees: CSM |
| 3.5 | **Post message to channel** | `#cs-handoffs`: "Renewal opened: {company}, {arr} ARR, ends {end_date}." |

A renewal starts at Business Case & Proposal. It has no demo or technical evaluation. Time-in-stage reports should filter renewals out, or count them on their own.

The `renewal_deal is empty` filter makes the run safe to repeat. A missed day is caught the next morning.

### Test

On 2026-10-22, no seeded term is inside the window. Helix (`hx26`, ends 2027-01-31) enters it on 2026-11-02. To test now: set Helix `end_date` to 2027-01-15, then **Run** the workflow by hand from the workflow page. Expect one renewal deal, `hx26` Renewal Due, a task and a post. Run the workflow again. Expect nothing new. Reseed to undo the change.

---

## W6 — Nurture sequence

**Purpose:** put leads that aren't ready to buy into a nurture email sequence instead of leaving them in the SDR Queue. This covers low-intent leads (W1 creates their queue entry at Nurture) and leads an SDR moves to Nurture.

| # | Block | Configuration |
|---|---|---|
| T | **List entry updated** | List: SDR Queue. Attribute: `status` |
| 1 | **If** | `{List entry updated > Updated Entry > Status > Stage title}` is Nurture |
| 2 | **Enroll in sequence** | Nurture — 21 days. Recipient: `{T > parent record}`. Sender: test mailbox |

**Leaving the sequence.**

- **Reply:** set the sequence to stop on reply. **Verify** this setting in the sequence editor.
- **Demo request:** W1 step 9a runs **Exit from sequence** and adds a new SDR Queue entry. So a nurtured lead who asks for a demo returns to an SDR with a fresh SLA.

### Test

| Case | Do | Expect |
|---|---|---|
| SDR nurture | Set a `+test` person's SDR Queue entry to Nurture | Enrolled. First email in the test inbox |
| Re-engage | Submit the W1 form as the enrolled person, Book a demo | Leaves the sequence. New queue entry New |

---

## Spec vs build plan: known differences

Where the spec refines the build plan or field guide, the spec wins:

- **Build plan §0:** date math in workflows is resolved. Adjust time supports months. The open point is only whether it accepts a date attribute (W3a 1.2).
- **Build plan §5a:** "workflows default to read-only" is not in the current docs. Confirm it in the trial.
- **Field guide:** `segment` is set by W1 from company size, then corrected by the SDR. `sourced_by` is set by the SDR only (W1 creates no deal). `health` Watch is set by the CSM only.
- **Decision log:** add the Slack channel + task pattern, the W3a trigger and duplicate guard, the workspace relink on renewal, the W5 schedule over Delay until, and the W4 new-department option chosen.
