"""Seed CloudScale demo data into Attio (build-plan.md step 7).

Usage: python seed_demo.py

Run build_workspace.py first. Re-running is safe: companies match on domain, people on
email, workspaces on workspace_id, deals and subscriptions on name. All domains are
subdomains of example.com (reserved), so no seeded email can reach a real inbox.

Covers: deals at every stage (new, expansion, renewal), three renewed subscription chains,
subscriptions in every status (22 terms), 20 workspaces whose signals match the W4 rules as
built, three accounts in onboarding, and SDR Queue entries in every status.

Pause the Attio workflows and the n8n usage sync before running: seeded Closed Won / Closed
Lost deals and workspace updates would otherwise fire W3, W3b, W4 and W6.
"""
from datetime import datetime, timedelta, timezone

from build_workspace import call

# Pricing from 01-discovery/product-profile.md §2: (base price, included users, extra-user rate)
PLANS = {"Growth": (12000, 25, 240), "Business": (30000, 75, 240), "Enterprise": (75000, 225, 200)}
NOW = datetime.now(timezone.utc).replace(microsecond=0)


def arr(plan, seats, rate=None):
    base, included, list_rate = PLANS[plan]
    return base + max(seats - included, 0) * (rate or list_rate)


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def domain(key):
    return f"{key}.example.com"


# key, name, segment, lifecycle, health
COMPANIES = [
    ("northwind", "Northwind Logistics", "Mid-Market", "Customer", "Healthy"),
    ("brightpath", "Brightpath Health", "Growth", "Customer", "Healthy"),
    ("quantum", "Quantum Retail Group", "Enterprise", "Customer", "Healthy"),
    ("helix", "Helix Fintech", "Mid-Market", "Customer", "Healthy"),
    ("corvid", "Corvid Media", "Growth", "Customer", "At risk"),
    ("lumen", "Lumen Energy", "Enterprise", "Customer", None),
    ("atlas", "Atlas Manufacturing", "Mid-Market", "Opportunity", None),
    ("pinecrest", "Pinecrest Insurance", "Enterprise", "Opportunity", None),
    ("redwood", "Redwood Labs", "Growth", "Opportunity", None),
    ("summit", "Summit Outdoor Co", "Mid-Market", "Opportunity", None),
    ("orbit", "Orbit Payments", "Enterprise", "Opportunity", None),
    ("kestrel", "Kestrel Travel", "Growth", "Lead", None),
    ("tidewater", "Tidewater Ports", "Mid-Market", "SQL", None),
    ("marlowe", "Marlowe Foods", None, "MQL", None),
    ("sprout", "Tiny Sprout Bakery", None, "MQL", None),
    ("granite", "Granite Peak Bank", "Enterprise", "Customer", "Healthy"),
    ("kettle", "Kettle & Crate Retail", "Mid-Market", "Customer", "Healthy"),
    ("bluefin", "Bluefin Seafoods", "Growth", "Customer", "Healthy"),
    ("meridian", "Meridian Clinics", "Mid-Market", "Customer", "At risk"),
    ("foxglove", "Foxglove Studios", "Growth", "Customer", None),
    ("stonegate", "Stonegate Property Group", "Mid-Market", "Customer", "At risk"),
    ("aurora", "Aurora Telecom", "Enterprise", "Customer", None),
    ("nimbus", "Nimbus Air Cargo", "Enterprise", "Customer", "At risk"),
    ("willow", "Willow & Pine Furniture", "Growth", "Customer", "Healthy"),
    ("cedar", "Cedar Valley Schools", "Growth", "Customer", "Watch"),  # Watch is the CSM's manual flag
    ("polaris", "Polaris Biotech", "Mid-Market", "Churned", None),
    ("juniper", "Juniper Hotels", "Growth", "Churned", None),
]

# key, first, last, title, company, lifecycle, lead source, form intent, utm campaign, utm source
PEOPLE = [
    ("dana", "Dana", "Whitfield", "VP Operations", "northwind", "Customer", None, None, None, None),
    ("marcus", "Marcus", "Lee", "Analytics Lead", "northwind", "Customer", "Demo request", "High", "q1-bi-buyers-guide", "google"),
    ("priya", "Priya", "Nair", "Data Engineer", "northwind", "Customer", None, None, None, None),
    ("elena", "Elena", "Ruiz", "CFO", "brightpath", "Customer", None, None, None, None),
    ("tom", "Tom", "Becker", "BI Manager", "brightpath", "Customer", "Webinar", "Low", "healthcare-kpis-webinar", "linkedin"),
    ("grace", "Grace", "Okafor", "Chief Data Officer", "quantum", "Customer", "Referral", "High", None, None),
    ("liam", "Liam", "Chen", "Director of Analytics", "quantum", "Customer", None, None, None, None),
    ("sofia", "Sofia", "Martins", "Head of Data Platform", "quantum", "Customer", None, None, None, None),
    ("aaron", "Aaron", "Price", "VP Finance", "helix", "Customer", None, None, None, None),
    ("nina", "Nina", "Kowalski", "Analytics Manager", "helix", "Customer", "Contact sales", "High", "fintech-reporting", "google"),
    ("ben", "Ben", "Harlow", "COO", "corvid", "Customer", None, None, None, None),
    ("chloe", "Chloe", "Adams", "Marketing Analyst", "corvid", "Customer", "Content download", "Low", "dashboard-templates", "linkedin"),
    ("rachel", "Rachel", "Stone", "VP Strategy", "lumen", "Customer", None, None, None, None),
    ("david", "David", "Park", "Data Lead", "lumen", "Customer", "Demo request", "High", "energy-analytics", "google"),
    ("omar", "Omar", "Haddad", "IT Director", "lumen", "Customer", None, None, None, None),
    ("karen", "Karen", "Liu", "Director of Operations", "atlas", "Opportunity", "Outbound", None, None, None),
    ("jason", "Jason", "Reed", "Plant Systems Lead", "atlas", "Opportunity", None, None, None, None),
    ("helen", "Helen", "Brooks", "CFO", "pinecrest", "Opportunity", None, None, None, None),
    ("victor", "Victor", "Alvarez", "Head of Analytics", "pinecrest", "Opportunity", "Demo request", "High", "insurance-loss-ratios", "google"),
    ("mei", "Mei", "Tanaka", "Security Architect", "pinecrest", "Opportunity", None, None, None, None),
    ("sam", "Sam", "Patel", "Procurement Manager", "pinecrest", "Opportunity", None, None, None, None),
    ("ivy", "Ivy", "Collins", "Founder & CEO", "redwood", "Opportunity", "Demo request", "High", "startup-metrics", "producthunt"),
    ("noah", "Noah", "Fischer", "Ecommerce Manager", "summit", "Opportunity", "Webinar", "Low", "retail-dashboards-webinar", "linkedin"),
    ("leah", "Leah", "Grant", "Data Analyst", "summit", "Opportunity", None, None, None, None),
    ("monica", "Monica", "Reyes", "CFO", "orbit", "Opportunity", None, None, None, None),
    ("kevin", "Kevin", "O'Brien", "Director of BI", "orbit", "Opportunity", "Contact sales", "High", "payments-analytics", "google"),
    ("arjun", "Arjun", "Mehta", "Data Platform Lead", "orbit", "Opportunity", None, None, None, None),
    ("fiona", "Fiona", "Walsh", "Head of Marketing", "kestrel", "Lead", "Content download", "Low", "travel-demand-report", "linkedin"),
    ("laura", "Laura", "Kim", "Logistics Analytics Manager", "tidewater", "SQL", "Demo request", "High", "port-throughput", "google"),
    ("jake", "Jake", "Turner", "Operations Manager", "marlowe", "MQL", "Demo request", "High", "food-supply-chain", "google"),
    ("mia", "Mia", "Rossi", "Owner", "sprout", "MQL", "Contact sales", "High", None, "direct"),
    ("hannah", "Hannah", "Cole", "CFO", "granite", "Customer", None, None, None, None),
    ("ravi", "Ravi", "Desai", "Head of BI", "granite", "Customer", "Referral", "High", None, None),
    ("ingrid", "Ingrid", "Holm", "Data Platform Lead", "granite", "Customer", None, None, None, None),
    ("owen", "Owen", "Marsh", "VP Merchandising", "kettle", "Customer", None, None, None, None),
    ("tara", "Tara", "Quinn", "Analytics Manager", "kettle", "Customer", "Webinar", "Low", "retail-dashboards-webinar", "linkedin"),
    ("lucas", "Lucas", "Moreau", "COO", "bluefin", "Customer", None, None, None, None),
    ("jenna", "Jenna", "Fry", "Operations Analyst", "bluefin", "Customer", "Demo request", "High", "food-supply-chain", "google"),
    ("paula", "Paula", "Kemp", "VP Finance", "meridian", "Customer", None, None, None, None),
    ("dev", "Dev", "Sharma", "Analytics Lead", "meridian", "Customer", "Contact sales", "High", "healthcare-kpis", "google"),
    ("zoe", "Zoe", "Hart", "Managing Director", "foxglove", "Customer", None, None, None, None),
    ("felix", "Felix", "Brandt", "Production Data Lead", "foxglove", "Customer", "Content download", "Low", "dashboard-templates", "linkedin"),
    ("george", "George", "Lyle", "CFO", "stonegate", "Customer", None, None, None, None),
    ("anika", "Anika", "Bose", "BI Analyst", "stonegate", "Customer", "Outbound", None, None, None),
    ("carmen", "Carmen", "Vidal", "VP Network Operations", "aurora", "Customer", None, None, None, None),
    ("yusuf", "Yusuf", "Kaya", "Director of Analytics", "aurora", "Customer", "Demo request", "High", "telecom-churn-analytics", "google"),
    ("lena", "Lena", "Berg", "Enterprise Architect", "aurora", "Customer", None, None, None, None),
    ("patrick", "Patrick", "Doyle", "CFO", "nimbus", "Customer", None, None, None, None),
    ("sana", "Sana", "Iqbal", "Head of Ops Analytics", "nimbus", "Customer", "Referral", "High", None, None),
    ("erik", "Erik", "Lund", "IT Director", "nimbus", "Customer", None, None, None, None),
    ("rosa", "Rosa", "Lin", "Founder", "willow", "Customer", None, None, None, None),
    ("matt", "Matt", "Gibbs", "Ecommerce Lead", "willow", "Customer", "Demo request", "High", "startup-metrics", "producthunt"),
    ("diane", "Diane", "Ellis", "Director of Finance", "cedar", "Customer", None, None, None, None),
    ("kyle", "Kyle", "Moss", "Data Coordinator", "cedar", "Customer", "Webinar", "Low", "public-sector-reporting", "linkedin"),
    ("irene", "Irene", "Vos", "CFO", "polaris", "Churned", None, None, None, None),
    ("hugo", "Hugo", "Lam", "Data Scientist", "polaris", "Churned", "Demo request", "High", "lab-ops-analytics", "google"),
    ("nora", "Nora", "Field", "General Manager", "juniper", "Churned", None, None, None, None),
    ("colin", "Colin", "West", "Revenue Analyst", "juniper", "Churned", "Content download", "Low", "travel-demand-report", "linkedin"),
]

# key, name, company, status, plan, seats, rate, start, end, auto_renew
SUBSCRIPTIONS = [
    # nw26 at 150 seats and the Corvid renewal (cv26 Renewed, cv27 Active) match the W3 test runs.
    ("nw26", "Northwind Logistics — 2026–27", "northwind", "Active", "Business", 150, None, "2026-03-01", "2027-02-28", True),
    ("bp26", "Brightpath Health — 2026–27", "brightpath", "Active", "Growth", 40, None, "2026-05-01", "2027-04-30", True),
    ("qr25", "Quantum Retail Group — 2025–26", "quantum", "Renewed", "Enterprise", 240, None, "2025-06-01", "2026-05-31", False),
    ("qr26", "Quantum Retail Group — 2026–27", "quantum", "Active", "Enterprise", 260, None, "2026-06-01", "2027-05-31", False),
    ("hx26", "Helix Fintech — 2026–27", "helix", "Active", "Business", 80, None, "2026-02-01", "2027-01-31", True),
    ("cv26", "Corvid Media — 2026", "corvid", "Renewed", "Growth", 30, None, "2026-01-01", "2026-12-31", False),
    ("cv27", "Corvid Media — Renewal 2027", "corvid", "Active", "Growth", 30, None, "2026-12-31", "2027-12-31", False),
    ("lm26", "Lumen Energy — 2026–27", "lumen", "Onboarding", "Enterprise", 225, None, "2026-10-15", "2027-10-14", True),
    ("gp25", "Granite Peak Bank — 2025–26", "granite", "Renewed", "Enterprise", 300, None, "2025-09-01", "2026-08-31", True),
    ("gp26", "Granite Peak Bank — 2026–27", "granite", "Active", "Enterprise", 340, 185, "2026-09-01", "2027-08-31", True),
    ("kc26", "Kettle & Crate Retail — 2026–27", "kettle", "Active", "Business", 95, None, "2026-07-01", "2027-06-30", True),
    ("bf26", "Bluefin Seafoods — 2026–27", "bluefin", "Active", "Growth", 28, None, "2026-08-15", "2027-08-14", True),
    ("mc25", "Meridian Clinics — 2025–26", "meridian", "Renewed", "Business", 75, None, "2025-04-01", "2026-03-31", False),
    ("mc26", "Meridian Clinics — 2026–27", "meridian", "Active", "Business", 110, None, "2026-04-01", "2027-03-31", False),
    ("wp26", "Willow & Pine Furniture — 2026–27", "willow", "Active", "Growth", 35, None, "2026-04-01", "2027-03-31", True),
    ("fg26", "Foxglove Studios — 2026–27", "foxglove", "Onboarding", "Growth", 25, None, "2026-10-01", "2027-09-30", True),
    ("au26", "Aurora Telecom — 2026–27", "aurora", "Onboarding", "Enterprise", 250, None, "2026-09-15", "2027-09-14", True),
    # Renewal Due terms end inside the 90-day window, so the Renewals view shows them.
    ("sg26", "Stonegate Property Group — 2026–27", "stonegate", "Renewal Due", "Business", 85, None, "2026-01-15", "2027-01-14", False),
    ("nb25", "Nimbus Air Cargo — 2025–26", "nimbus", "Renewal Due", "Enterprise", 230, None, "2025-12-01", "2026-11-30", False),
    ("cs26", "Cedar Valley Schools — 2026–27", "cedar", "Renewal Due", "Growth", 25, None, "2026-01-08", "2027-01-07", False),
    ("pb25", "Polaris Biotech — 2025–26", "polaris", "Churned", "Business", 75, None, "2025-09-01", "2026-08-31", False),
    ("jh25", "Juniper Hotels — 2025–26", "juniper", "Churned", "Growth", 25, None, "2025-07-01", "2026-06-30", False),
]

# name, company, type, stage, plan, seats, rate, value override (None = full ARR, "delta:<sub>" = change
# from that term, int = as given), close, EB, champion, TE, other people, links {attr: subscription key},
# loss reason
DEALS = [
    ("Northwind Logistics — New", "northwind", "New", "Closed Won", "Business", 120, None, None, "2026-02-20",
     "dana", "marcus", "priya", [], {"created_subscription": "nw26"}, None),
    ("Northwind Logistics — Expansion +30 seats", "northwind", "Expansion", "Closed Won", "Business", 150, None,
     7200, "2026-10-23", "dana", "marcus", None, [], {"expands_subscription": "nw26"}, None),
    ("Brightpath Health — New", "brightpath", "New", "Closed Won", "Growth", 40, None, None, "2026-04-24",
     "elena", "tom", None, [], {"created_subscription": "bp26"}, None),
    ("Quantum Retail Group — New", "quantum", "New", "Closed Won", "Enterprise", 240, None, None, "2025-05-28",
     "grace", "liam", "sofia", [], {"created_subscription": "qr25"}, None),
    ("Quantum Retail Group — Renewal 2026", "quantum", "Renewal", "Closed Won", "Enterprise", 260, None, "delta:qr25",
     "2026-05-20", "grace", "liam", None, [], {"renews_subscription": "qr25", "created_subscription": "qr26"}, None),
    ("Helix Fintech — New", "helix", "New", "Closed Won", "Business", 80, None, None, "2026-01-26",
     "aaron", "nina", None, [], {"created_subscription": "hx26"}, None),
    ("Corvid Media — New", "corvid", "New", "Closed Won", "Growth", 30, None, None, "2025-12-18",
     "ben", "chloe", None, [], {"created_subscription": "cv26"}, None),
    ("Corvid Media — Renewal 2027", "corvid", "Renewal", "Closed Won", "Growth", 30, None, "delta:cv26", "2026-10-23",
     "ben", "chloe", None, [], {"renews_subscription": "cv26", "created_subscription": "cv27"}, None),
    ("Lumen Energy — New", "lumen", "New", "Closed Won", "Enterprise", 225, None, None, "2026-10-10",
     "rachel", "david", "omar", [], {"created_subscription": "lm26"}, None),
    ("Atlas Manufacturing — New", "atlas", "New", "Discovery", "Business", 100, None, None, "2026-12-10",
     None, "karen", "jason", [], {}, None),
    ("Pinecrest Insurance — New", "pinecrest", "New", "Security & Procurement", "Enterprise", 300, 190, None, "2026-11-14",
     "helen", "victor", "mei", ["sam"], {}, None),
    ("Redwood Labs — New", "redwood", "New", "Demo Scheduled", "Growth", 25, None, None, "2026-12-18",
     None, "ivy", None, [], {}, None),
    ("Summit Outdoor Co — New", "summit", "New", "Technical Evaluation", "Business", 90, None, None, "2026-12-05",
     None, "noah", "leah", [], {}, None),
    ("Orbit Payments — New", "orbit", "New", "Negotiation", "Enterprise", 250, None, None, "2026-10-31",
     "monica", "kevin", "arjun", [], {}, None),
    ("Kestrel Travel — New", "kestrel", "New", "Closed Lost", "Growth", 30, None, None, "2026-09-30",
     None, "fiona", None, [], {}, "Competitor"),
    ("Granite Peak Bank — New", "granite", "New", "Closed Won", "Enterprise", 300, None, None, "2025-08-25",
     "hannah", "ravi", "ingrid", [], {"created_subscription": "gp25"}, None),
    ("Granite Peak Bank — Renewal 2026", "granite", "Renewal", "Closed Won", "Enterprise", 340, 185, "delta:gp25",
     "2026-08-20", "hannah", "ravi", None, [], {"renews_subscription": "gp25", "created_subscription": "gp26"}, None),
    ("Kettle & Crate Retail — New", "kettle", "New", "Closed Won", "Business", 95, None, None, "2026-06-24",
     "owen", "tara", None, [], {"created_subscription": "kc26"}, None),
    ("Bluefin Seafoods — New", "bluefin", "New", "Closed Won", "Growth", 28, None, None, "2026-08-10",
     "lucas", "jenna", None, [], {"created_subscription": "bf26"}, None),
    ("Meridian Clinics — New", "meridian", "New", "Closed Won", "Business", 75, None, None, "2025-03-25",
     "paula", "dev", None, [], {"created_subscription": "mc25"}, None),
    ("Meridian Clinics — Renewal 2026", "meridian", "Renewal", "Closed Won", "Business", 110, None, "delta:mc25",
     "2026-03-20", "paula", "dev", None, [], {"renews_subscription": "mc25", "created_subscription": "mc26"}, None),
    ("Willow & Pine Furniture — New", "willow", "New", "Closed Won", "Growth", 35, None, None, "2026-03-27",
     "rosa", "matt", None, [], {"created_subscription": "wp26"}, None),
    ("Foxglove Studios — New", "foxglove", "New", "Closed Won", "Growth", 25, None, None, "2026-09-26",
     "zoe", "felix", None, [], {"created_subscription": "fg26"}, None),
    ("Aurora Telecom — New", "aurora", "New", "Closed Won", "Enterprise", 250, None, None, "2026-09-10",
     "carmen", "yusuf", "lena", [], {"created_subscription": "au26"}, None),
    ("Stonegate Property Group — New", "stonegate", "New", "Closed Won", "Business", 85, None, None, "2026-01-09",
     "george", "anika", None, [], {"created_subscription": "sg26"}, None),
    ("Nimbus Air Cargo — New", "nimbus", "New", "Closed Won", "Enterprise", 230, None, None, "2025-11-24",
     "patrick", "sana", "erik", [], {"created_subscription": "nb25"}, None),
    ("Cedar Valley Schools — New", "cedar", "New", "Closed Won", "Growth", 25, None, None, "2026-01-05",
     "diane", "kyle", None, [], {"created_subscription": "cs26"}, None),
    ("Polaris Biotech — New", "polaris", "New", "Closed Won", "Business", 75, None, None, "2025-08-28",
     "irene", "hugo", None, [], {"created_subscription": "pb25"}, None),
    ("Juniper Hotels — New", "juniper", "New", "Closed Won", "Growth", 25, None, None, "2025-06-26",
     "nora", "colin", None, [], {"created_subscription": "jh25"}, None),
    # Open renewals as W5 creates them (flat, value 0), and two lost renewals for the churned terms.
    ("Stonegate Property Group — Renewal", "stonegate", "Renewal", "Business Case & Proposal", "Business", 85, None, 0,
     "2027-01-14", "george", "anika", None, [], {"renews_subscription": "sg26"}, None),
    ("Nimbus Air Cargo — Renewal", "nimbus", "Renewal", "Negotiation", "Enterprise", 230, None, 0,
     "2026-11-30", "patrick", "sana", "erik", [], {"renews_subscription": "nb25"}, None),
    ("Cedar Valley Schools — Renewal", "cedar", "Renewal", "Business Case & Proposal", "Growth", 25, None, 0,
     "2027-01-07", "diane", "kyle", None, [], {"renews_subscription": "cs26"}, None),
    ("Polaris Biotech — Renewal", "polaris", "Renewal", "Closed Lost", "Business", 75, None, 0,
     "2026-08-31", "irene", "hugo", None, [], {"renews_subscription": "pb25"}, "Price"),
    ("Juniper Hotels — Renewal", "juniper", "Renewal", "Closed Lost", "Growth", 25, None, 0,
     "2026-06-30", "nora", "colin", None, [], {"renews_subscription": "jh25"}, "No decision"),
]

# workspace_id, name, subscription, seats used, WAU, WAU change %, departments, paywall hits,
# days since last active, usage signal, expansion reason, users
# Signals follow the W4 rules as built (usage_rule): Risk (WAU ≤ −30% or idle 14+ days), then Seats
# (utilisation ≥ 90), then Plan upgrade (paywall hits ≥ 10), else Stable. No New department rule exists.
WORKSPACES = [
    ("ws-northwind-us", "Northwind — US", "nw26", 112, 96, 6, 3, 2, 0, "Stable", None, ["marcus", "priya"]),
    ("ws-brightpath-main", "Brightpath — Main", "bp26", 34, 29, 18, 3, 1, 0, "Stable", None, ["tom"]),
    ("ws-quantum-us", "Quantum — US", "qr26", 120, 104, 3, 5, 0, 0, "Stable", None, ["liam", "sofia"]),
    ("ws-quantum-eu", "Quantum — EU", "qr26", 80, 66, -4, 3, 0, 1, "Stable", None, ["liam"]),
    ("ws-helix-main", "Helix — Main", "hx26", 70, 61, 5, 2, 14, 0, "Expansion", "Plan upgrade", ["nina"]),
    ("ws-corvid-main", "Corvid — Main", "cv27", 22, 6, -45, 1, 0, 16, "Risk", None, ["chloe"]),
    ("ws-lumen-main", "Lumen — Main", "lm26", 60, 48, 85, 2, 0, 0, "Stable", None, ["david", "omar"]),
    ("ws-granite-us", "Granite Peak — US", "gp26", 215, 188, 4, 6, 0, 0, "Expansion", "Seats", ["ravi", "ingrid"]),
    ("ws-granite-uk", "Granite Peak — UK", "gp26", 95, 81, 9, 2, 0, 0, "Expansion", "Seats", ["ravi"]),
    ("ws-kettle-main", "Kettle & Crate — Main", "kc26", 88, 79, 8, 4, 3, 0, "Expansion", "Seats", ["tara"]),
    ("ws-bluefin-main", "Bluefin — Main", "bf26", 20, 17, 2, 2, 17, 1, "Expansion", "Plan upgrade", ["jenna"]),
    ("ws-meridian-east", "Meridian — East", "mc26", 70, 62, 7, 3, 12, 0, "Expansion", "Plan upgrade", ["dev"]),
    ("ws-meridian-west", "Meridian — West", "mc26", 25, 11, -38, 1, 0, 2, "Risk", None, ["dev"]),
    ("ws-willow-main", "Willow & Pine — Main", "wp26", 33, 30, 12, 2, 4, 0, "Expansion", "Seats", ["matt"]),
    ("ws-foxglove-main", "Foxglove — Main", "fg26", 9, 8, 60, 1, 0, 0, "Stable", None, ["felix"]),
    ("ws-aurora-core", "Aurora — Core", "au26", 95, 82, 40, 3, 0, 0, "Stable", None, ["yusuf", "lena"]),
    ("ws-stonegate-main", "Stonegate — Main", "sg26", 60, 2, -90, 2, 0, 18, "Risk", None, ["anika"]),
    ("ws-nimbus-ops", "Nimbus — Ops", "nb25", 150, 84, -34, 3, 0, 0, "Risk", None, ["sana"]),
    ("ws-nimbus-finance", "Nimbus — Finance", "nb25", 40, 35, 2, 1, 0, 0, "Stable", None, ["patrick"]),
    ("ws-cedar-main", "Cedar Valley — Main", "cs26", 18, 14, -8, 2, 2, 1, "Stable", None, ["kyle"]),
]

# company, subscription, stage, kickoff, target go-live
ONBOARDING = [
    ("lumen", "lm26", "Data Source Connected", "2026-10-16", "2026-11-30"),
    ("foxglove", "fg26", "Kickoff", "2026-10-05", "2026-11-16"),
    ("aurora", "au26", "First Dashboard Live", "2026-09-18", "2026-10-23"),  # past target: late-onboarding case
]

# person, status, SLA offset from now (hours), first touch offset (hours), DQ reason
SDR_QUEUE = [
    ("jake", "New", -2, None, None),  # SLA passed, still New: W2a overdue alert case
    ("laura", "Contacted", -20, -20.5, None),
    ("ivy", "Qualified", -96, -96.4, None),
    ("fiona", "Nurture", -400, -399, None),
    ("mia", "Disqualified", -30, -29.8, "Too small"),
]


def member_id():
    members = call("GET", "/workspace_members")["data"]
    admin = next(m for m in members if m["access_level"] == "admin")
    return admin["id"]["workspace_member_id"]


def ref(obj, record_id):
    return [{"target_object": obj, "target_record_id": record_id}]


def compact(values):
    return {k: v for k, v in values.items() if v is not None}


def assert_by(obj, match, values):
    data = call("PUT", f"/objects/{obj}/records?matching_attribute={match}", {"data": {"values": compact(values)}})
    return data["data"]["id"]["record_id"]


def upsert_by_name(obj, name, values):
    found = call("POST", f"/objects/{obj}/records/query", {"filter": {"name": name}, "limit": 1})["data"]
    body = {"data": {"values": compact({"name": name, **values})}}
    if found:
        record_id = found[0]["id"]["record_id"]
        call("PUT", f"/objects/{obj}/records/{record_id}", body)
        return record_id
    return call("POST", f"/objects/{obj}/records", body)["data"]["id"]["record_id"]


def main():
    me = [{"referenced_actor_type": "workspace-member", "referenced_actor_id": member_id()}]

    companies = {}
    for key, name, segment, lifecycle, health in COMPANIES:
        is_customer = lifecycle in ("Customer", "Churned")
        companies[key] = assert_by("companies", "domains", {
            "name": name,
            "domains": [domain(key)],
            "segment": segment,
            "lifecycle_stage": lifecycle,
            "health": health,
            "sdr_owner": me,
            "csm_owner": me if is_customer else None,
        })
    print(f"companies: {len(companies)}")

    people = {}
    for key, first, last, title, company, lifecycle, source, intent, campaign, utm_source in PEOPLE:
        people[key] = assert_by("people", "email_addresses", {
            "name": [{"first_name": first, "last_name": last, "full_name": f"{first} {last}"}],
            "email_addresses": [f"{first.lower()}.{last.lower().replace(chr(39), '')}@{domain(company)}"],
            "job_title": title,
            "company": ref("companies", companies[company]),
            "lifecycle_stage": lifecycle,
            "lead_source": source,
            "form_intent": intent,
            "utm_campaign": campaign,
            "utm_source": utm_source,
        })
    print(f"people: {len(people)}")

    subs, sub_arr, sub_rows = {}, {}, {s[0]: s for s in SUBSCRIPTIONS}
    for key, name, company, status, plan, seats, rate, start, end, auto in SUBSCRIPTIONS:
        sub_arr[key] = arr(plan, seats, rate)
        subs[key] = upsert_by_name("subscriptions", name, {
            "company": ref("companies", companies[company]),
            "status": status,
            "plan": plan,
            "arr": sub_arr[key],
            "seats_purchased": seats,
            "price_per_seat": rate or PLANS[plan][2],
            "start_date": start,
            "end_date": end,
            "auto_renew": auto,
        })
    print(f"subscriptions: {len(subs)}")

    for (name, company, dtype, stage, plan, seats, rate, value, close,
         eb, champ, te, others, links, loss) in DEALS:
        resulting = arr(plan, seats, rate)
        # value = ARR this deal adds: full ARR for New, the change for Expansion / Renewal
        if isinstance(value, int):
            added = value
        else:
            added = resulting - sub_arr[value.split(":")[1]] if value else resulting
        involved = [p for p in (eb, champ, te, *others) if p]
        upsert_by_name("deals", name, {
            "associated_company": ref("companies", companies[company]),
            "associated_people": [r for p in involved for r in ref("people", people[p])],
            "deal_type": dtype,
            "stage": stage,
            "owner": me,
            "plan": plan,
            "seats": seats,
            "price_per_seat": rate or PLANS[plan][2],
            "resulting_arr": resulting,
            "value": added,
            "close_date": close,
            "economic_buyer": ref("people", people[eb]) if eb else None,
            "champion": ref("people", people[champ]) if champ else None,
            "technical_evaluator": ref("people", people[te]) if te else None,
            "sourced_by": me if dtype == "New" else None,
            "loss_reason": loss,
            **{attr: ref("subscriptions", subs[s]) for attr, s in links.items()},
        })
    print(f"deals: {len(DEALS)}")

    # Seat utilisation is per subscription: a contract's seats are shared across its workspaces.
    used_by_sub = {}
    for w in WORKSPACES:
        used_by_sub[w[2]] = used_by_sub.get(w[2], 0) + w[3]
    for (ws_id, name, sub, seats_used, wau, wau_change, depts, paywall,
         idle_days, signal, reason, users) in WORKSPACES:
        company = sub_rows[sub][2]
        assert_by("product_workspaces", "workspace_id", {
            "workspace_id": ws_id,
            "name": name,
            "company": ref("companies", companies[company]),
            "subscription": ref("subscriptions", subs[sub]),
            "users": [r for u in users for r in ref("people", people[u])],
            "seats_used": seats_used,
            "seat_utilisation": round(100 * used_by_sub[sub] / sub_rows[sub][5], 1),
            "weekly_active_users": wau,
            "wau_change_30d": wau_change,
            "departments_active": depts,
            "paywall_hits_30d": paywall,
            "last_active_at": iso(NOW - timedelta(days=idle_days, hours=3)),
            "last_synced_at": iso(NOW),
            "usage_signal": signal,
            "expansion_reason": reason,
        })
    print(f"product workspaces: {len(WORKSPACES)}")

    for company, sub, stage, kickoff, target in ONBOARDING:
        call("PUT", "/lists/onboarding/entries", {"data": {
            "parent_record_id": companies[company],
            "parent_object": "companies",
            "entry_values": {
                "stage": stage,
                "subscription": ref("subscriptions", subs[sub]),
                "kickoff_date": kickoff,
                "target_go_live": target,
            },
        }})
    print(f"onboarding entries: {len(ONBOARDING)}")

    for person, status, sla_hours, touch_hours, dq in SDR_QUEUE:
        call("PUT", "/lists/sdr_queue/entries", {"data": {
            "parent_record_id": people[person],
            "parent_object": "people",
            "entry_values": compact({
                "status": status,
                "sla_due_at": iso(NOW + timedelta(hours=sla_hours)),
                "dq_reason": dq,
            }),
        }})
        if touch_hours is not None:
            call("PATCH", f"/objects/people/records/{people[person]}", {"data": {"values": {
                "first_touch_at": iso(NOW + timedelta(hours=touch_hours))}}})
    print(f"sdr queue entries: {len(SDR_QUEUE)}")
    print("\ndone.")


if __name__ == "__main__":
    main()
