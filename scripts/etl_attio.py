"""Full load: Attio -> Supabase Postgres warehouse (build-plan.md section 5c, step 12).

Usage: python etl_attio.py [--schema-only]

Reads ATTIO_API_KEY and SUPABASE_DB_URL from the repo .env. Applies warehouse/sql/*.sql
(idempotent), then pages through every object and list and upserts into raw.*. Records
deleted in Attio are removed from raw.* so the warehouse matches the CRM after each run.
Requires: pip install "psycopg[binary]"
"""
import json
import sys
from datetime import datetime, timezone

import psycopg

from build_workspace import REPO, call

OBJECTS = ["companies", "people", "deals", "subscriptions", "product_workspaces"]
LISTS = ["sdr_queue", "onboarding"]
PAGE = 500
SQL_DIR = REPO / "warehouse" / "sql"

# Which key holds the plain value for each Attio attribute type.
VALUE_KEY = {
    "currency": "currency_value",
    "record-reference": "target_record_id",
    "actor-reference": "referenced_actor_id",
    "domain": "domain",
    "email-address": "email_address",
    "personal-name": "full_name",
    "phone-number": "original_phone_number",
    "interaction": "interacted_at",
}


def env(name):
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            value = line.split("=", 1)[1].strip().strip("\"'")
            if value:
                return value
    sys.exit(f"{name} not found in .env")


def plain(v):
    t = v.get("attribute_type")
    if t == "select":
        return v["option"]["title"]
    if t == "status":
        return v["status"]["title"]
    if t == "location":
        return ", ".join(p for p in (v.get("locality"), v.get("region"), v.get("country_code")) if p) or None
    return v.get(VALUE_KEY.get(t, "value"))


def flatten(values, multi):
    """{slug: [attio value objects]} -> {slug: plain value, or a list for multi-value attributes}."""
    out = {}
    for slug, items in values.items():
        current = [plain(v) for v in items if v.get("active_until") is None]
        out[slug] = current if slug in multi else (current[0] if current else None)
    return out


def multi_slugs(path):
    return {a["api_slug"] for a in call("GET", path)["data"] if a.get("is_multiselect")}


def page_through(path):
    offset = 0
    while True:
        rows = call("POST", path, {"limit": PAGE, "offset": offset})["data"]
        yield from rows
        if len(rows) < PAGE:
            return
        offset += PAGE


def apply_sql(conn):
    for f in sorted(SQL_DIR.glob("*.sql")):
        conn.execute(f.read_text(encoding="utf-8"))
        print(f"applied {f.name}")


def load_members(conn):
    members = call("GET", "/workspace_members")["data"]
    with conn.cursor() as cur:
        cur.executemany(
            """insert into raw.attio_members (member_id, name, email, access, synced_at)
               values (%s, %s, %s, %s, now())
               on conflict (member_id) do update set name = excluded.name, email = excluded.email,
                   access = excluded.access, synced_at = now()""",
            [(m["id"]["workspace_member_id"], f'{m["first_name"]} {m["last_name"]}'.strip(),
              m["email_address"], m["access_level"]) for m in members],
        )
    return len(members)


def load_object(conn, obj):
    multi = multi_slugs(f"/objects/{obj}/attributes")
    rows = [(obj, r["id"]["record_id"], r["created_at"], json.dumps(r["values"]),
             json.dumps(flatten(r["values"], multi)))
            for r in page_through(f"/objects/{obj}/records/query")]
    with conn.cursor() as cur:
        cur.executemany(
            """insert into raw.attio_records (object, record_id, created_at, "values", fields, synced_at)
               values (%s, %s, %s, %s, %s, now())
               on conflict (object, record_id) do update set created_at = excluded.created_at,
                   "values" = excluded."values", fields = excluded.fields, synced_at = now()""",
            rows,
        )
        cur.execute("delete from raw.attio_records where object = %s and not (record_id = any(%s))",
                    (obj, [r[1] for r in rows]))
    return len(rows)


def load_list(conn, lst):
    multi = multi_slugs(f"/lists/{lst}/attributes")
    rows = [(lst, e["id"]["entry_id"], e["parent_object"], e["parent_record_id"], e["created_at"],
             json.dumps(e["entry_values"]), json.dumps(flatten(e["entry_values"], multi)))
            for e in page_through(f"/lists/{lst}/entries/query")]
    with conn.cursor() as cur:
        cur.executemany(
            """insert into raw.attio_list_entries
                   (list, entry_id, parent_object, parent_record_id, created_at, "values", fields, synced_at)
               values (%s, %s, %s, %s, %s, %s, %s, now())
               on conflict (list, entry_id) do update set parent_object = excluded.parent_object,
                   parent_record_id = excluded.parent_record_id, created_at = excluded.created_at,
                   "values" = excluded."values", fields = excluded.fields, synced_at = now()""",
            rows,
        )
        cur.execute("delete from raw.attio_list_entries where list = %s and not (entry_id = any(%s))",
                    (lst, [r[1] for r in rows]))
    return len(rows)


def main():
    with psycopg.connect(env("SUPABASE_DB_URL")) as conn:
        apply_sql(conn)
        conn.commit()
        if "--schema-only" in sys.argv:
            return
        started = datetime.now(timezone.utc)
        counts = {}
        try:
            counts["members"] = load_members(conn)
            for obj in OBJECTS:
                counts[obj] = load_object(conn, obj)
                print(f"{obj}: {counts[obj]}")
            for lst in LISTS:
                counts[lst] = load_list(conn, lst)
                print(f"{lst}: {counts[lst]}")
            conn.execute("insert into raw.etl_runs (started_at, finished_at, mode, row_counts) "
                         "values (%s, now(), 'full', %s)", (started, json.dumps(counts)))
            conn.commit()
        except Exception as e:
            conn.rollback()
            conn.execute("insert into raw.etl_runs (started_at, finished_at, mode, row_counts, error) "
                         "values (%s, now(), 'full', %s, %s)", (started, json.dumps(counts), str(e)[:2000]))
            conn.commit()
            raise
    print("\ndone.")


if __name__ == "__main__":
    main()
