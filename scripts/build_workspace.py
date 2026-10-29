"""Build the CloudScale Attio data model from a JSON spec (build-plan.md steps 2-5).

Usage: python build_workspace.py [workspace-spec.json] [--dry-run]

Reads ATTIO_API_KEY from the repo .env. Re-running is safe: objects, attributes,
select options, statuses, relationships and lists are matched by slug/title and
skipped if they already exist. Formula attributes are UI-only and not created here.
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.attio.com/v2"
REPO = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
DRY = "--dry-run" in sys.argv
CURRENCY = {"currency": {"default_currency_code": "USD", "display_type": "symbol"}}

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # default status names contain emoji


def load_key():
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("ATTIO_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("\"'")
                if key:
                    return key
    sys.exit("ATTIO_API_KEY not found in .env")


KEY = load_key()


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req) as resp:
                time.sleep(0.05)  # writes are limited to 25/s
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:500]}")
    raise RuntimeError(f"{method} {path} -> still rate limited after retries")


def write(method, path, body, label):
    print(f"{'would create' if DRY else 'create'}: {label}")
    if DRY:
        return {}
    return call(method, path, {"data": body})


def attr_body(a):
    body = {
        "title": a["title"],
        "description": a["description"],
        "api_slug": a["slug"],
        "type": a["type"],
        "is_required": False,
        "is_unique": a.get("unique", False),
        "is_multiselect": a.get("multi", False),
        "config": {},
    }
    if a["type"] == "currency":
        body["config"] = CURRENCY
    if a["type"] == "record-reference":
        body["config"] = {"record_reference": {"allowed_objects": [a["target"]]}}
    return body


def sync_options(base, a):
    """Add missing select options to attribute at base (e.g. /objects/x/attributes/y)."""
    have = {o["title"] for o in call("GET", f"{base}/options")["data"]} if not DRY else set()
    for title in a["options"]:
        if title not in have:
            write("POST", f"{base}/options", {"title": title}, f"  option {a['slug']}: {title}")


def sync_statuses(base, titles, celebrate=(), archive_others=False):
    have = {s["title"]: s for s in call("GET", f"{base}/statuses")["data"]} if not DRY else {}
    for title in titles:
        if title not in have:
            write("POST", f"{base}/statuses", {"title": title, "celebration_enabled": title in celebrate},
                  f"  status: {title}")
        elif have[title]["is_archived"]:
            write("PATCH", f"{base}/statuses/{have[title]['id']['status_id']}", {"is_archived": False},
                  f"  unarchive status: {title}")
    if archive_others:
        for title, s in have.items():
            if title not in titles and not s["is_archived"]:
                write("PATCH", f"{base}/statuses/{s['id']['status_id']}", {"is_archived": True},
                      f"  archive default status: {title}")


def existing_attrs(parent):
    if DRY:
        try:
            return {a["api_slug"] for a in call("GET", f"{parent}/attributes")["data"]}
        except RuntimeError:
            return set()  # object not created yet
    return {a["api_slug"] for a in call("GET", f"{parent}/attributes")["data"]}


def sync_attributes(parent, attrs):
    have = existing_attrs(parent)
    for a in attrs:
        base = f"{parent}/attributes/{a['slug']}"
        if a["slug"] in have:
            print(f"exists: {parent} {a['slug']}")
        else:
            write("POST", f"{parent}/attributes", attr_body(a), f"{parent} {a['slug']} ({a['type']})")
        if "options" in a:
            sync_options(base, a)
        if "statuses" in a:
            sync_statuses(base, a["statuses"])


def main(spec_path):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))

    # Step 2: custom objects
    have_objects = {o["api_slug"] for o in call("GET", "/objects")["data"]}
    for o in spec["objects"]:
        if o["api_slug"] in have_objects:
            print(f"exists: object {o['api_slug']}")
        else:
            write("POST", "/objects", o, f"object {o['api_slug']}")

    # Step 3: attributes, options and statuses
    for obj, attrs in spec["attributes"].items():
        sync_attributes(f"/objects/{obj}", attrs)
    for r in spec["replace_statuses"]:
        print(f"statuses: {r['object']}.{r['attribute']}")
        sync_statuses(f"/objects/{r['object']}/attributes/{r['attribute']}", r["statuses"],
                      r.get("celebrate", ()), archive_others=True)

    # Step 4: two-way relationships (creating one side creates the reverse)
    for r in spec["relationships"]:
        have = existing_attrs(f"/objects/{r['object']}")
        if r["slug"] in have:
            print(f"exists: relationship {r['object']}.{r['slug']}")
            continue
        body = attr_body({**r, "type": "record-reference"})
        body["relationship"] = {
            "object": r["target"],
            "title": r["rev_title"],
            "api_slug": r["rev_slug"],
            "is_multiselect": r["rev_multi"],
        }
        write("POST", f"/objects/{r['object']}/attributes", body,
              f"relationship {r['object']}.{r['slug']} <-> {r['target']}.{r['rev_slug']}")

    # Step 5: lists and entry attributes
    have_lists = {l["api_slug"] for l in call("GET", "/lists")["data"]}
    for l in spec["lists"]:
        if l["api_slug"] in have_lists:
            print(f"exists: list {l['api_slug']}")
        else:
            write("POST", "/lists", {
                "name": l["name"],
                "api_slug": l["api_slug"],
                "parent_object": l["parent_object"],
                "workspace_access": "full-access",
                "workspace_member_access": [],
            }, f"list {l['api_slug']}")
        sync_attributes(f"/lists/{l['api_slug']}", l["attributes"])

    print("\ndone." + (" (dry run, nothing written)" if DRY else ""))
    print("UI next: formula live_arr on Subscriptions, then total_arr and active_users on Companies (build-plan.md step 6).")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0] if args else HERE / "workspace-spec.json")
