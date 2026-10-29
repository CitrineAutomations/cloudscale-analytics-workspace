# Runbook — CloudScale usage sync (n8n rETL)

**What it does:** every hour, n8n reads product usage from Supabase and upserts one Attio Product Workspace per product workspace. W4 then reacts to the new numbers.

**Owner:** RevOps · **Workflows:** `CloudScale usage sync (rETL)`, `CloudScale sync error handler` · **Files:** [`n8n/`](../../n8n/)

## Data flow

```
Supabase public.workspace_usage_daily ──▶ view workspace_usage_latest ──▶ n8n ──▶ Attio Product Workspaces
                                                                          │
                                         failures ──▶ public.sync_errors + Slack
```

| Attio field | Comes from |
|---|---|
| `seats_used`, `weekly_active_users`, `departments_active`, `last_active_at`, `name` | Latest day in `workspace_usage_daily` |
| `wau_change_30d` | View: today's WAU vs the WAU 30 days earlier, % to 1 decimal |
| `paywall_hits_30d` | View: sum of the last 30 days |
| `seat_utilisation` | n8n: seats used across every workspace on the contract ÷ the subscription's `seats_purchased` |
| `company` | n8n: linked by `company_domain` on every run |
| `last_synced_at` | n8n: time of the run |

The sync never writes `usage_signal`, `expansion_reason` or `subscription`. W4 owns the first two, and the CSM links the subscription.

## API endpoints

Every call retries 3 times before it counts as failed.

| # | n8n node | Method + endpoint | Auth | Request | Returns / used for |
|---|---|---|---|---|---|
| 1 | Fetch usage | `GET {SUPABASE_URL}/rest/v1/workspace_usage_latest` | Supabase service role key (`apikey` + `Authorization: Bearer`) | None | One row per product workspace: latest seats, WAU, departments, 30-day WAU change and paywall hits |
| 2 | Get subscriptions | `POST https://api.attio.com/v2/objects/subscriptions/records/query` | `Authorization: Bearer <ATTIO_API_KEY>` | `{"limit": 500}` | Every subscription with `seats_purchased` and linked workspaces, used for `seat_utilisation` |
| 3 | Get Attio workspaces | `POST https://api.attio.com/v2/objects/product_workspaces/records/query` | Attio bearer | `{"limit": 500}` | Existing workspaces and their linked subscription, so utilisation is summed per contract |
| 4 | Upsert workspace | `PUT https://api.attio.com/v2/objects/product_workspaces/records?matching_attribute=workspace_id` | Attio bearer | `{"data": {"values": {...}}}`, batched 10 per second | Assert: creates the record if `workspace_id` is new, updates it otherwise. Reruns never duplicate |
| 5 | Log failed row | `POST {SUPABASE_URL}/rest/v1/sync_errors` | Supabase service role key, `Prefer: return=minimal` | `workflow`, `node`, `workspace_id`, `error`, `payload` | One row per Attio rejection, with the full payload for replay |
| 6 | Slack alert | `POST <Slack incoming webhook>` | Webhook URL is the secret | `{"text": "N of M workspaces failed…"}` | One summary per run, only when rows failed |
| 7 | Log run failure (error workflow) | `POST {SUPABASE_URL}/rest/v1/sync_errors` | Supabase service role key | Failed node name and error message | Records a crash of the whole run |
| 8 | Slack run failure (error workflow) | `POST <Slack incoming webhook>` | Webhook URL | `{"text": "…failed at <node>"}` | Alerts on a crash of the whole run |

Scopes: the Attio key needs `record_permission:read-write` and `object_configuration:read`. Limits: Attio allows about 25 writes per second, so batching at 10 per second leaves headroom. The two `query` calls read up to 500 records each with no paging, which covers the demo (22 subscriptions, 20 workspaces). Add `offset` paging above 500.

Docs: [Attio list records](https://developers.attio.com/reference/post_v2-objects-object-records-query) · [Attio assert record](https://developers.attio.com/reference/put_v2-objects-object-records) · [Supabase REST](https://supabase.com/docs/guides/api)

## Setup (once)

1. **Credentials in n8n**
   - `Attio API`: type **Header Auth**, name `Authorization`, value `Bearer <ATTIO_API_KEY>`.
   - `Supabase CloudScale`: type **Supabase API**, host = the project URL, service role secret = `SUPABASE_SERVICE_ROLE_KEY`.
2. **Import** `usage-sync-error.json`, then `usage-sync.json` (Workflows → Import from file).
3. **Slack:** in both workflows, replace `PASTE_SLACK_INCOMING_WEBHOOK_URL` with the CS alerts channel webhook.
4. **Error workflow:** open `CloudScale usage sync (rETL)` → Settings → Error workflow → `CloudScale sync error handler`.
5. Run it once by hand (Execute workflow), check the results (below), then switch it to **Active**.

## Check a run

- n8n execution: `Upsert workspace` shows one green item per workspace, and the error output is empty.
- Attio: Product Workspaces → `last_synced_at` is within the last hour on every record.
- Supabase: `select * from sync_errors where replayed_at is null;` returns no rows.

## When it fails

| Symptom | Likely cause | Fix |
|---|---|---|
| Slack: "N of M workspaces failed to upsert" | Attio rejected some rows (bad value, deleted attribute, wrong domain) | Read `error` in `sync_errors`, fix the cause, then replay (below) |
| Slack: "failed at Fetch usage" | Supabase key rotated or project paused | Update the `Supabase CloudScale` credential; restore the project |
| Slack: "failed at Get subscriptions" / 401 | Attio key revoked | Create a new key with record read/write scopes; update `Attio API` |
| 429 in the error text | Attio rate limit despite retries | Lower `Upsert workspace` batching from 10 to 5 per second |
| Workspace has no `seat_utilisation` | New workspace with no subscription linked yet | CSM links the subscription; the next run fills it |
| Workspace has no company | `company_domain` doesn't match any Attio company domain | Add the domain to the right company in Attio |

## Replay failed rows

Each failed row stores the exact Attio payload. To resend one:

1. Find it: `select id, workspace_id, error, payload from sync_errors where replayed_at is null order by occurred_at;`
2. Fix the cause first, or the replay fails the same way.
3. Send `{"data": {"values": <payload>}}` to Attio `PUT /v2/objects/product_workspaces/records?matching_attribute=workspace_id`. Easiest: wait for the next hourly run, which resends every workspace anyway.
4. Mark it done: `update sync_errors set replayed_at = now() where id = <id>;`

Because every run upserts every workspace, a missed run heals itself on the next one. Replaying by hand is only needed when you can't wait an hour.

## Demo data

- `python scripts/seed_usage.py` resets 31 days of usage ending today. Re-run it before a demo, or the latest day goes stale.
- To show W4 firing live: `update workspace_usage_daily set departments_active = departments_active + 1 where workspace_id = 'ws-quantum-us' and usage_date = current_date;`, then execute the workflow.
