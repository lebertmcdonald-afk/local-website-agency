#!/usr/bin/env python3
"""
find_leads.py  —  WAT tool
--------------------------
Finds local businesses with good Google reviews but no/weak website, using the
Google Places API (New) Text Search endpoint. Writes matches to nyc-pest-leads.csv
in the project root (same columns as lead-tracker.csv), ready to copy into the tracker.

Run from the project root:  python3 tools/find_leads.py
Edit the CONFIG block below to reuse for other trades / cities.
"""

import csv
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

# ---- CONFIG (edit to reuse for other trades / cities) ----
MIN_RATING = 4.3      # proof customers like them
MIN_REVIEWS = 15      # proof it's a real business

# Trade -> Google Maps searches. Pest control is primary; plumber/electrician are
# "top-up" trades used to reach 20 leads. Each lead is tagged with its trade so the
# site generator can pick the right services.
TRADES = {
    "Pest Control": [
        # Queens
        "exterminator Astoria Queens NY", "pest control Long Island City Queens NY",
        "exterminator Sunnyside Queens NY", "pest control Woodside Queens NY",
        "exterminator Jackson Heights Queens NY", "pest control Elmhurst Queens NY",
        "exterminator Corona Queens NY", "pest control Flushing Queens NY",
        "exterminator Bayside Queens NY", "pest control Forest Hills Queens NY",
        "exterminator Rego Park Queens NY", "pest control Ridgewood Queens NY",
        "exterminator Jamaica Queens NY", "pest control Ozone Park Queens NY",
        # Brooklyn
        "exterminator Bay Ridge Brooklyn NY", "pest control Bensonhurst Brooklyn NY",
        "exterminator Bushwick Brooklyn NY", "pest control Williamsburg Brooklyn NY",
        "exterminator Flatbush Brooklyn NY", "pest control Sheepshead Bay Brooklyn NY",
        "exterminator Canarsie Brooklyn NY", "pest control Sunset Park Brooklyn NY",
        "exterminator Crown Heights Brooklyn NY", "pest control Bedford-Stuyvesant Brooklyn NY",
        # Bronx
        "exterminator Pelham Bay Bronx NY", "pest control Throggs Neck Bronx NY",
        "exterminator Fordham Bronx NY", "pest control Morris Park Bronx NY",
        "exterminator Parkchester Bronx NY",
        # Staten Island
        "exterminator Staten Island NY", "pest control Tottenville Staten Island NY",
        "exterminator New Springville Staten Island NY", "pest control Great Kills Staten Island NY",
        # Manhattan
        "exterminator Washington Heights Manhattan NY", "pest control Harlem Manhattan NY",
        "exterminator Inwood Manhattan NY", "pest control Lower East Side Manhattan NY",
    ],
    "Plumber": [
        "plumber Astoria Queens NY", "plumber Flushing Queens NY", "plumber Jamaica Queens NY",
        "plumber Ridgewood Queens NY", "plumber Bay Ridge Brooklyn NY", "plumber Bushwick Brooklyn NY",
        "plumber Flatbush Brooklyn NY", "plumber Canarsie Brooklyn NY", "plumber Throggs Neck Bronx NY",
        "plumber Fordham Bronx NY", "plumber Staten Island NY", "plumber Washington Heights Manhattan NY",
    ],
    "Electrician": [
        "electrician Astoria Queens NY", "electrician Flushing Queens NY", "electrician Jamaica Queens NY",
        "electrician Ridgewood Queens NY", "electrician Bay Ridge Brooklyn NY", "electrician Bushwick Brooklyn NY",
        "electrician Flatbush Brooklyn NY", "electrician Canarsie Brooklyn NY", "electrician Throggs Neck Bronx NY",
        "electrician Fordham Bronx NY", "electrician Staten Island NY", "electrician Washington Heights Manhattan NY",
    ],
}

# Leading search terms stripped when deriving the area label from a query.
SEARCH_PREFIXES = ("exterminator ", "pest control ", "plumber ", "electrician ")

# A website that is only a social page still counts as a target.
SOCIAL_DOMAINS = ("facebook.com", "fb.com", "instagram.com", "yelp.com",
                  "linktr.ee", "linktree", "business.site")

# ---- Paths: tool lives in tools/, project files live one level up ----
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
ENV_PATH = os.path.join(ROOT_DIR, ".env")
OUTPUT_PATH = os.path.join(ROOT_DIR, "nyc-pest-leads.csv")

ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.rating",
    "places.userRatingCount",
    "places.websiteUri",
    "places.nationalPhoneNumber",
    "places.formattedAddress",
    "places.googleMapsUri",
])

CSV_HEADER = [
    "Business Name", "Trade", "City/Area", "Google Rating", "# Reviews",
    "Website Status", "Phone", "Email", "Owner Name", "Target Score (0-5)",
    "Sample Link", "Status", "Date Contacted", "Notes",
]


def make_ssl_context():
    """Build an SSL context from whatever CA bundle this Mac has.

    Python on macOS often ships without a usable default cert file, so point at a
    known-good bundle instead of disabling verification (the API key rides this connection).
    """
    for cafile in ("/etc/ssl/cert.pem", "/usr/local/etc/ca-certificates/cert.pem"):
        if os.path.exists(cafile):
            return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


SSL_CONTEXT = make_ssl_context()


def load_api_key():
    if not os.path.exists(ENV_PATH):
        sys.exit(f"ERROR: no .env file found at {ENV_PATH}")
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("GOOGLE_PLACES_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key and key != "paste-your-key-here":
                    return key
    sys.exit("ERROR: GOOGLE_PLACES_API_KEY not set in .env (still the placeholder?)")


def search(query, api_key):
    """Call Places Text Search; return a list of place dicts (or stop on a key error)."""
    body = json.dumps({"textQuery": query, "pageSize": 20}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
            return json.loads(resp.read().decode("utf-8")).get("places", [])
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        print(f"  ! API error ({e.code}) for '{query}': {detail}")
        # A bad key / billing / API-not-enabled error repeats for every query,
        # so stop early instead of hammering the API.
        if e.code in (400, 403):
            sys.exit("\nStopping: fix the API error above (usually billing not active, "
                     "Places API (New) not enabled, or the key restriction), then rerun.")
        return []
    except urllib.error.URLError as e:
        print(f"  ! Network error for '{query}': {e}")
        return []


def website_status(uri):
    if not uri:
        return "None"
    low = uri.lower()
    if any(d in low for d in SOCIAL_DOMAINS):
        return "Social only"
    return "Has site"


def city_from_query(query):
    # "pest control Flushing Queens NY" -> "Flushing Queens"
    q = query
    for prefix in SEARCH_PREFIXES:
        if q.lower().startswith(prefix):
            q = q[len(prefix):]
            break
    if q.upper().endswith(" NY"):
        q = q[:-3]
    return q.strip()


def target_score(rating, reviews, status, phone):
    score = 0
    if rating >= MIN_RATING:
        score += 1
    if reviews > MIN_REVIEWS:
        score += 1
    if status in ("None", "Social only"):
        score += 1
    if phone:
        score += 1
    return score


def main():
    api_key = load_api_key()
    seen = {}          # place_id -> CSV row
    total_seen = 0

    n_queries = 0
    for trade, queries in TRADES.items():
        for query in queries:
            n_queries += 1
            print(f"Searching ({trade}): {query}")
            places = search(query, api_key)
            total_seen += len(places)
            area = city_from_query(query)
            for p in places:
                pid = p.get("id")
                if not pid or pid in seen:
                    continue
                rating = p.get("rating", 0) or 0
                reviews = p.get("userRatingCount", 0) or 0
                status = website_status(p.get("websiteUri"))
                if rating < MIN_RATING or reviews < MIN_REVIEWS or status == "Has site":
                    continue
                name = p.get("displayName", {}).get("text", "")
                phone = p.get("nationalPhoneNumber", "")
                maps_url = p.get("googleMapsUri", "")
                addr = p.get("formattedAddress", "")
                seen[pid] = [
                    name, trade, area, rating, reviews, status, phone, "", "",
                    target_score(rating, reviews, status, phone), "", "New", "",
                    f"{addr} | {maps_url}",
                ]
            time.sleep(0.2)

    rows = sorted(seen.values(), key=lambda r: (r[9], r[4]), reverse=True)  # score, then reviews

    with open(OUTPUT_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        w.writerows(rows)

    print(f"\nDone. Saw {total_seen} listings across {n_queries} searches.")
    print(f"{len(rows)} matched (rating >= {MIN_RATING}, {MIN_REVIEWS}+ reviews, no real website).")
    by_trade = {}
    for r in rows:
        by_trade[r[1]] = by_trade.get(r[1], 0) + 1
    print("By trade:", ", ".join(f"{k}: {v}" for k, v in by_trade.items()))
    print(f"Saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
