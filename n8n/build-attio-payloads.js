// n8n Code node "Build Attio payloads" (Run Once for All Items) in usage-sync.json.
// Kept here so it can be read, diffed and tested outside n8n; paste changes into the node.
//
// Inputs (earlier nodes):
//   Fetch usage           one item per workspace from Supabase workspace_usage_latest
//   Get subscriptions     Attio subscriptions query (seats_purchased per contract)
//   Get Attio workspaces  Attio product_workspaces query (which contract covers each workspace)
// Output: one item per workspace, { workspace_id, values } ready for the Attio upsert.
//
// Seat utilisation is per contract: seats are shared across all workspaces on one subscription,
// so Quantum US (120) + EU (80) on 260 seats is 76.9% for both. Decision 16: calculated here,
// not as an Attio formula. usage_signal / expansion_reason are left alone; W4 owns them.

const usage = $('Fetch usage').all().map(i => i.json);
const subs = $('Get subscriptions').first().json.data;
const attioWorkspaces = $('Get Attio workspaces').first().json.data;

const first = (values, key, field = 'value') => values[key]?.[0]?.[field] ?? null;

const seatsBySub = Object.fromEntries(
  subs.map(s => [s.id.record_id, first(s.values, 'seats_purchased')]),
);
const subByWorkspace = Object.fromEntries(
  attioWorkspaces.map(w => [first(w.values, 'workspace_id'), first(w.values, 'subscription', 'target_record_id')]),
);

const usedBySub = {};
for (const u of usage) {
  const sub = subByWorkspace[u.workspace_id];
  if (sub) usedBySub[sub] = (usedBySub[sub] ?? 0) + u.seats_used;
}

const syncedAt = new Date().toISOString();

return usage.map(u => {
  const sub = subByWorkspace[u.workspace_id];
  const seats = sub ? seatsBySub[sub] : null;
  const values = {
    workspace_id: u.workspace_id,
    name: u.workspace_name,
    // Linked by domain on every sync; a brand-new workspace attaches to its company on first sync.
    // A new workspace has no subscription yet, so the CSM links it and utilisation fills next hour.
    company: [{ target_object: 'companies', domains: [{ domain: u.company_domain }] }],
    seats_used: u.seats_used,
    seat_utilisation: seats ? Math.round((1000 * usedBySub[sub]) / seats) / 10 : null,
    weekly_active_users: u.weekly_active_users,
    wau_change_30d: u.wau_change_30d,
    departments_active: u.departments_active,
    paywall_hits_30d: u.paywall_hits_30d,
    last_active_at: u.last_active_at,
    last_synced_at: syncedAt,
  };
  // Attio rejects null for number attributes, so leave unknowns out instead. A new workspace has
  // no subscription (no seat_utilisation) and no 30-day history (no wau_change_30d) yet.
  for (const key of Object.keys(values)) if (values[key] === null) delete values[key];
  return { json: { workspace_id: u.workspace_id, values } };
});
