#!/usr/bin/env python3
"""
get_reviews.py  —  WAT tool
---------------------------
Pulls one business's details + recent Google reviews, to use as context when
building its sample website. Uses the Google Places API (New) Text Search with
the reviews field (Enterprise+Atmosphere SKU — a few cents per call).

Usage (from project root):
    python3 tools/get_reviews.py "Stars Exterminator Whitestone NY"

Prints a readable summary and saves the raw JSON to .tmp/place_details.json.
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.request

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
ENV_PATH = os.path.join(ROOT_DIR, ".env")
TMP_DIR = os.path.join(ROOT_DIR, ".tmp")

ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.rating",
    "places.userRatingCount",
    "places.websiteUri",
    "places.editorialSummary",
    "places.primaryTypeDisplayName",
    "places.types",
    "places.regularOpeningHours",
    "places.reviews",
])


def make_ssl_context():
    for cafile in ("/etc/ssl/cert.pem", "/usr/local/etc/ca-certificates/cert.pem"):
        if os.path.exists(cafile):
            return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


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


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: python3 tools/get_reviews.py "Business Name City NY"')
    query = sys.argv[1]
    api_key = load_api_key()

    body = json.dumps({"textQuery": query, "pageSize": 1}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=make_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"API error ({e.code}): {e.read().decode('utf-8', 'replace')}")

    places = data.get("places", [])
    if not places:
        sys.exit(f"No place found for: {query}")
    p = places[0]

    os.makedirs(TMP_DIR, exist_ok=True)
    out_path = os.path.join(TMP_DIR, "place_details.json")
    with open(out_path, "w") as f:
        json.dump(p, f, indent=2)

    name = p.get("displayName", {}).get("text", "")
    print("=" * 60)
    print(name)
    print("=" * 60)
    print(f"Rating:   {p.get('rating')} stars ({p.get('userRatingCount')} reviews)")
    print(f"Phone:    {p.get('nationalPhoneNumber', '-')}")
    print(f"Address:  {p.get('formattedAddress', '-')}")
    print(f"Type:     {p.get('primaryTypeDisplayName', {}).get('text', '-')}")
    print(f"Website:  {p.get('websiteUri', '(none)')}")
    summary = p.get("editorialSummary", {}).get("text")
    if summary:
        print(f"Summary:  {summary}")

    reviews = p.get("reviews", [])
    print(f"\n--- {len(reviews)} recent reviews ---\n")
    for r in reviews:
        author = r.get("authorAttribution", {}).get("displayName", "Anonymous")
        stars = r.get("rating", "-")
        when = r.get("relativePublishingTimeDescription", "")
        text = r.get("text", {}).get("text") or r.get("originalText", {}).get("text") or ""
        print(f"[{stars}*] {author} ({when})")
        print(f"  {text.strip()}\n")

    print(f"Raw JSON saved -> {out_path}")


if __name__ == "__main__":
    main()
