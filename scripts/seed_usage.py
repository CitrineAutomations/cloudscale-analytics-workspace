"""Seed the mock product database in Supabase (build-plan.md step 11).

Usage: python seed_usage.py

Writes 31 days of daily usage per workspace into public.workspace_usage_daily, ending today.
Numbers are back-solved from seed_demo.WORKSPACES, so the first n8n sync reproduces what is
already in Attio, within a fraction of a percent on wau_change_30d (no false W4 alerts). Re-running replaces the history with a fresh window.
Requires: pip install "psycopg[binary]"
"""
from datetime import date, datetime, timedelta, timezone

import psycopg

from etl_attio import SQL_DIR, env
from seed_demo import SUBSCRIPTIONS, WORKSPACES, domain

DAYS = 30


def wau_30d_ago(wau, change_pct):
    """Whole-number WAU 30 days ago whose % change to today is closest to change_pct."""
    guess = round(wau / (1 + change_pct / 100))
    return min(range(max(guess - 3, 1), guess + 4), key=lambda n: abs(100 * (wau - n) / n - change_pct))


def main():
    company_of = {s[0]: s[2] for s in SUBSCRIPTIONS}
    today = date.today()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    rows = []
    for (ws_id, name, sub, seats_used, wau, wau_change, depts, paywall,
         idle_days, *_rest) in WORKSPACES:
        start_wau = wau_30d_ago(wau, wau_change)
        per_day, extra = divmod(paywall, DAYS)
        for back in range(DAYS, -1, -1):
            day = today - timedelta(days=back)
            day_wau = round(wau + (start_wau - wau) * back / DAYS)
            # Spread the 30-day paywall total over days 0..29; the newest days get any remainder.
            hits = 0 if back == DAYS else per_day + (1 if back < extra else 0)
            last_active = now - timedelta(days=back + idle_days, hours=3)
            rows.append((ws_id, day, name, domain(company_of[sub]), seats_used, day_wau,
                         depts, hits, last_active))

    with psycopg.connect(env("SUPABASE_DB_URL")) as conn:
        conn.execute((SQL_DIR / "03_product_mock.sql").read_text(encoding="utf-8"))
        with conn.cursor() as cur:
            cur.execute("delete from public.workspace_usage_daily where workspace_id = any(%s)",
                        ([w[0] for w in WORKSPACES],))
            cur.executemany(
                """insert into public.workspace_usage_daily (workspace_id, usage_date, workspace_name,
                       company_domain, seats_used, weekly_active_users, departments_active,
                       paywall_hits, last_active_at)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                rows,
            )
    print(f"workspace_usage_daily: {len(rows)} rows ({len(WORKSPACES)} workspaces x {DAYS + 1} days)")


if __name__ == "__main__":
    main()
