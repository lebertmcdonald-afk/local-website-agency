#!/usr/bin/env python3
"""
find_contacts.py — WAT tool
Pulls each lead's websiteUri + maps link from Google Places (the link Google has
on file) and classifies it (Website / Facebook / Instagram / Yelp / None) so we
know who has any web/social presence to chase an email or DM on.
Run from project root:  python3 tools/find_contacts.py
"""
import json, os, ssl, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
MASK = "places.displayName,places.websiteUri,places.nationalPhoneNumber,places.googleMapsUri"

# (name, area) — the 23 outreach prospects
LEADS = [
    ("Stars Exterminator", "Whitestone Queens"),
    ("Fumigador Latino", "Sunnyside Queens"),
    ("Pest Hunter", "Bay Ridge Brooklyn"),
    ("Force Pest Control", "Bushwick Brooklyn"),
    ("Positive Pest Control", "Sheepshead Bay Brooklyn"),
    ("Infestation Protection Pest Control", "Forest Hills Queens"),
    ("Ecofriendly USA Pest Control", "Pelham Bay Bronx"),
    ("Golden Touch Pest Services", "Fordham Bronx"),
    ("Goodfellas Pest Management", "Washington Heights Manhattan"),
    ("Hibbert Exterminating", "Crown Heights Brooklyn"),
    ("Alley Cat Exterminating", "Bensonhurst Brooklyn"),
    ("Green Pest Control Service", "Ridgewood Queens"),
    ("First Solutions Pest Control", "Throggs Neck Bronx"),
    ("Express Sewer Drain Cleaning & Repairs", "Fordham Bronx"),
    ("Huitt Plumbing & Heating", "Ridgewood Queens"),
    ("Pomonok Heating and Plumbing", "Flushing Queens"),
    ("Osborn Brothers Plumbing", "Washington Heights Manhattan"),
    ("SMB Plumbing and Heating", "Flatbush Brooklyn"),
    ("Plumbing Emergency Service 24 7", "Astoria Queens"),
    ("BMT Plumbing & Heating", "Throggs Neck Bronx"),
    ("DLS Pest Management", "Jamaica Queens"),
    ("NYC Plumber Bronx & Drain Cleaning", "Fordham Bronx"),
    ("Sunnyside Heating and Plumbing", "Sunnyside Queens"),
]


def ssl_ctx():
    for f in ("/etc/ssl/cert.pem", "/usr/local/etc/ca-certificates/cert.pem"):
        if os.path.exists(f):
            return ssl.create_default_context(cafile=f)
    return ssl.create_default_context()


def key():
    with open(ENV) as f:
        for line in f:
            if line.strip().startswith("GOOGLE_PLACES_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("no key in .env")


def classify(uri):
    if not uri:
        return "None"
    u = uri.lower()
    if "facebook.com" in u:
        return "Facebook"
    if "instagram.com" in u:
        return "Instagram"
    if "yelp.com" in u:
        return "Yelp"
    if "linktr" in u or "business.site" in u:
        return "Social"
    return "Website"


def main():
    api_key, ctx = key(), ssl_ctx()
    print(f"{'Business':<40} {'Type':<10} URL")
    print("-" * 90)
    for name, area in LEADS:
        body = json.dumps({"textQuery": f"{name} {area} NY", "pageSize": 1}).encode()
        req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
            "Content-Type": "application/json", "X-Goog-Api-Key": api_key, "X-Goog-FieldMask": MASK})
        uri = ""
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                places = json.loads(r.read().decode()).get("places", [])
                if places:
                    uri = places[0].get("websiteUri", "")
        except urllib.error.HTTPError as e:
            print(f"{name:<40} ERROR {e.code}")
            continue
        print(f"{name[:39]:<40} {classify(uri):<10} {uri or '-'}")


if __name__ == "__main__":
    main()
