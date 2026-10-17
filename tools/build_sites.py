#!/usr/bin/env python3
"""
build_sites.py  —  WAT tool
---------------------------
Reads leads from nyc-pest-leads.csv, selects the top ~20 (all pest control first,
then the best plumbers/electricians), pulls each business's real Google reviews,
and renders a personalized site to sites/<slug>/index.html from templates/site.html.

Also writes .tmp/manifest.json (used by write_emails.py to build the AIDA emails).

Run from project root:  python3 tools/build_sites.py
"""

import csv
import html
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
ENV_PATH = os.path.join(ROOT_DIR, ".env")
LEADS_CSV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT_DIR, "nyc-pest-leads.csv")
SITES_DIR = os.path.join(ROOT_DIR, "sites")
TMP_DIR = os.path.join(ROOT_DIR, ".tmp")
TEMPLATE = os.path.join(TOOLS_DIR, "templates", "site.html")

TARGET = 20
PRESERVE = {"stars-exterminator"}  # keep the hand-made Gil site; don't overwrite it
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.displayName", "places.formattedAddress", "places.nationalPhoneNumber",
    "places.rating", "places.userRatingCount", "places.reviews",
])
AVATAR_COLORS = ["#e0795b", "#5b8de0", "#7d5be0", "#0c7a4d", "#d98a2b", "#3aa6a0"]

# ---------- per-trade content ----------
ICONS = {
    "bug": '<path d="M12 8a4 4 0 0 1 4 4v3a4 4 0 0 1-8 0v-3a4 4 0 0 1 4-4z"/><path d="M12 4v4M9 5l1.5 2M15 5l-1.5 2M4 11l4 1M20 11l-4 1M4 16l4-1M20 16l-4-1"/>',
    "hex": '<polygon points="12,3 19,7.5 19,16.5 12,21 5,16.5 5,7.5"/><path d="M9 11h6M9.5 14h5"/>',
    "mouse": '<circle cx="9" cy="13" r="5"/><circle cx="6" cy="8" r="2"/><circle cx="12" cy="8" r="2"/><path d="M14 15c4 0 6 1.5 6 4"/>',
    "roach": '<ellipse cx="12" cy="13" rx="4" ry="5"/><path d="M12 4v4M9.5 6l2 2.5M14.5 6l-2 2.5M5 12l3 1M19 12l-3 1M5 17l3-1.5M19 17l-3-1.5"/>',
    "magnifier": '<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "shield": '<path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z"/><path d="M9 12l2 2 4-4"/>',
    "droplet": '<path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z"/>',
    "wrench": '<path d="M21 4a5 5 0 0 1-6.5 6.5L6 19l-2-2 8.5-8.5A5 5 0 0 1 19 2l-2.4 2.4 1.6 1.6L21 4z"/>',
    "pipe": '<path d="M4 9h7a4 4 0 0 1 4 4v7M4 9V4M15 20h5"/><path d="M4 13h3"/>',
    "heater": '<rect x="7" y="3" width="10" height="18" rx="3"/><path d="M10 8h4M10 12h4"/>',
    "drain": '<circle cx="12" cy="12" r="8"/><path d="M12 4v16M4 12h16M7 7l10 10M17 7L7 17"/>',
    "faucet": '<path d="M3 11h6V9a2 2 0 0 1 2-2h5M16 5h4M12 11v3a3 3 0 0 0 6 0v-1"/>',
    "bolt": '<path d="M13 3L5 13h6l-1 8 8-10h-6z"/>',
    "bulb": '<path d="M12 3a6 6 0 0 1 4 10.5c-.6.6-1 1.4-1 2.5H9c0-1.1-.4-1.9-1-2.5A6 6 0 0 1 12 3z"/><path d="M9.5 19h5M10.5 21h3"/>',
    "outlet": '<rect x="4" y="4" width="16" height="16" rx="3"/><circle cx="9.5" cy="10" r="1"/><circle cx="14.5" cy="10" r="1"/><path d="M9 15h6"/>',
    "panel": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h6M9 11h6M9 15h6"/>',
    "ev": '<rect x="5" y="9" width="11" height="9" rx="2"/><path d="M16 12h2a2 2 0 0 1 2 2v2M8 9V6h5v3"/><path d="M10 13l-1.5 2H11l-1.5 2"/>',
}

TRADE = {
    "Pest Control": {
        "noun": "exterminator",
        "h1": 'Pests gone for good — <span class="hl">done right the first time.</span>',
        "sub": "Termites, wasps, rodents and more — honest pricing, fast service, and the job done right.",
        "eyebrow": "What we handle", "h2": "Pest problems we solve",
        "ssub": "From a single wasp nest to a full termite treatment — careful, thorough work every time.",
        "cta_h": "Got pests? Let's fix it today.",
        "cta_p": "Call now for a fast, honest quote — or send a message and we'll get right back to you.",
        "stat3": "Same-day",
        "services": [
            ("bug", "Termite Treatment", "Honest inspections and effective treatment to protect your home's structure."),
            ("hex", "Wasp &amp; Hornet Removal", "Nests removed safely — even inside walls — with siding put back damage-free."),
            ("mouse", "Rodent Control", "Mice and rats found, removed, and sealed out so they don't come back."),
            ("roach", "Roaches &amp; Ants", "Targeted treatment that clears infestations and keeps them away for good."),
            ("magnifier", "Home Inspections", "Clear, no-pressure assessments with straightforward advice on next steps."),
            ("shield", "Prevention &amp; Protection", "Practical steps to keep pests out long after the job is done."),
        ],
    },
    "Plumber": {
        "noun": "plumber",
        "h1": 'Plumbing problems fixed fast — <span class="hl">and done right.</span>',
        "sub": "Leaks, clogs, water heaters and emergencies — upfront pricing and dependable, on-time service.",
        "eyebrow": "What we handle", "h2": "Plumbing services we provide",
        "ssub": "From a dripping faucet to a burst pipe — clean, reliable work every time.",
        "cta_h": "Got a leak or clog? Let's fix it today.",
        "cta_p": "Call now for a fast, honest quote — or send a message and we'll get right back to you.",
        "stat3": "Same-day",
        "services": [
            ("droplet", "Emergency Repairs", "Burst pipes, major leaks and overflows handled fast, day or night."),
            ("drain", "Drain &amp; Sewer Cleaning", "Clogged drains and slow lines cleared quickly and cleanly."),
            ("heater", "Water Heaters", "Repair and replacement of water heaters so you're never left cold."),
            ("magnifier", "Leak Detection", "Hidden leaks found and fixed before they cause real damage."),
            ("faucet", "Fixtures &amp; Faucets", "Sinks, faucets, toilets and fixtures repaired or replaced."),
            ("pipe", "Repiping &amp; Installs", "New pipe runs and installations done to last."),
        ],
    },
    "Electrician": {
        "noun": "electrician",
        "h1": 'Safe, reliable electrical work — <span class="hl">done right.</span>',
        "sub": "Wiring, panels, lighting and repairs — honest pricing and dependable, on-time service.",
        "eyebrow": "What we handle", "h2": "Electrical services we provide",
        "ssub": "From a flickering light to a full panel upgrade — careful, code-aware work every time.",
        "cta_h": "Need an electrician? Let's get it sorted.",
        "cta_p": "Call now for a fast, honest quote — or send a message and we'll get right back to you.",
        "stat3": "Fast response",
        "services": [
            ("bolt", "Wiring &amp; Rewiring", "Safe new wiring and rewiring for homes of any age."),
            ("panel", "Panel Upgrades", "Modern electrical panels sized for today's power needs."),
            ("bulb", "Lighting Installation", "Indoor and outdoor lighting installed cleanly and safely."),
            ("outlet", "Outlets &amp; Switches", "New outlets, switches and dedicated circuits where you need them."),
            ("magnifier", "Troubleshooting", "Fast diagnosis of trips, outages and electrical faults."),
            ("ev", "EV Chargers", "Home EV charger installation done right the first time."),
        ],
    },
}

# Pexels stock photos (free commercial license, no attribution) — the trade doing the task.
_IMG = "https://images.pexels.com/photos/{0}/pexels-photo-{0}.jpeg?auto=compress&cs=tinysrgb&w={1}"
IMAGES = {
    "Pest Control": (_IMG.format(19789837, 1600), _IMG.format(35303785, 1000)),
    "Plumber": (_IMG.format(32588548, 1600), _IMG.format(6419128, 1000)),
    "Electrician": (_IMG.format(34054464, 1600), _IMG.format(9679179, 1000)),
}

LEGAL = re.compile(r"\b(inc|llc|corp|co|ltd|incorporated)\b\.?", re.I)
STOP = {
    # pronouns / sentence words that get capitalized mid-text
    "He", "She", "They", "His", "Her", "Him", "The", "This", "That", "Very", "Our",
    "Their", "We", "You", "Came", "Called", "From", "After", "Before", "When", "While",
    "Will", "Would", "Was", "Were", "Had", "Has", "Got", "Get", "Now", "Then", "Here",
    "There", "Just", "Also", "Even", "Once", "Made", "Make", "Took", "Take", "Gave",
    "Give", "Done", "Need", "Needed", "Want", "Wanted", "Did", "Definitely", "Absolutely",
    "Super", "Really", "Always", "Never", "Everything", "Everyone", "Anyone", "Today",
    "Tomorrow", "New", "York", "Mr", "Mrs", "Ms", "Dr", "God",
    # praise words
    "Thank", "Thanks", "Service", "Services", "Work", "Job", "Home", "House", "Team",
    "Company", "Business", "Guys", "Guy", "Man", "Highly", "Recommend", "Recommended",
    "Professional", "Honest", "Fast", "Best", "Friendly", "Knowledgeable", "Excellent",
    "Amazing", "Awesome", "Great", "Good", "Perfect", "Quick", "Prompt", "Reasonable",
    "Affordable", "Clean", "Nice", "Google", "Yelp", "USA", "American", "English", "Spanish",
    # days / months
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "June", "July", "August", "September",
    "October", "November", "December",
}


def make_ssl_context():
    for cafile in ("/etc/ssl/cert.pem", "/usr/local/etc/ca-certificates/cert.pem"):
        if os.path.exists(cafile):
            return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


SSL_CONTEXT = make_ssl_context()


def load_api_key():
    with open(ENV_PATH) as f:
        for line in f:
            if line.strip().startswith("GOOGLE_PLACES_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("ERROR: GOOGLE_PLACES_API_KEY missing in .env")


def clean_name(name):
    n = name.split("|")[0].strip()
    if n.isupper():
        n = n.title()
    n = LEGAL.sub("", n).strip(" .,-")
    return re.sub(r"\s{2,}", " ", n)


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)[:48] or "site"


def clean_text(t):
    t = re.sub(r"\s+", " ", t or "").strip()
    return "".join(ch for ch in t if ch.isprintable() and ord(ch) < 0x2190)  # drop emoji range


def truncate(t, n):
    t = clean_text(t)
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def fetch_place(query, api_key):
    body = json.dumps({"textQuery": query, "pageSize": 1}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK})
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as r:
            places = json.loads(r.read().decode("utf-8")).get("places", [])
            return places[0] if places else {}
    except urllib.error.HTTPError as e:
        print(f"  ! API error {e.code}: {e.read().decode('utf-8','replace')[:160]}")
        return {}


def detect_owner(reviews, business_name):
    # Words in the business name aren't the owner's first name (match singular/plural).
    bn = set(re.findall(r"[a-z]{3,}", business_name.lower()))
    bn |= {w.rstrip("s") for w in bn}
    counts = {}
    for r in reviews:
        text = clean_text(r.get("text", {}).get("text", ""))
        seen = set()
        # A capitalized word sitting MID-sentence (preceded by a lowercase letter or comma)
        # and not a contraction — most likely a person's name, e.g. "...thank Gil for...".
        for tok in re.findall(r"(?<=[a-z,]\s)([A-Z][a-z]{2,})(?![\w'])", text):
            if tok in STOP or tok.lower() in bn or tok.lower().rstrip("s") in bn or tok in seen:
                continue
            seen.add(tok)
            counts[tok] = counts.get(tok, 0) + 1
    if not counts:
        return ""
    name, n = max(counts.items(), key=lambda kv: kv[1])
    return name if n >= 2 else ""  # require it to recur — conservative on purpose


def select_leads(rows):
    # Exclude auto/electronics shops that pollute "electrician" searches.
    bad = ("auto", "wireless", "electronic", "cell", "phone repair", "iphone", "computer")
    ok = lambda r: not any(b in r["Business Name"].lower() for b in bad)
    by_rev = lambda rs: sorted(rs, key=lambda r: int(r["# Reviews"]), reverse=True)
    pest = by_rev([r for r in rows if r["Trade"] == "Pest Control" and ok(r)])
    plumbers = by_rev([r for r in rows if r["Trade"] == "Plumber" and ok(r)])
    electricians = by_rev([r for r in rows if r["Trade"] == "Electrician" and ok(r)])
    chosen = pest[:TARGET]
    chosen += (plumbers + electricians)[:max(0, TARGET - len(chosen))]  # plumbers first (cleaner trade)
    return chosen[:TARGET]


def main():
    api_key = load_api_key()
    with open(LEADS_CSV) as f:
        rows = [r for r in csv.DictReader(f) if r["Business Name"]]
    leads = select_leads(rows)
    print(f"Selected {len(leads)} businesses to build.\n")

    with open(TEMPLATE) as f:
        template = f.read()

    os.makedirs(TMP_DIR, exist_ok=True)
    manifest, used_slugs = [], set()

    for i, row in enumerate(leads, 1):
        raw_name = row["Business Name"]
        name = clean_name(raw_name)
        trade = row["Trade"]
        area = row["City/Area"]
        rating = row["Google Rating"]
        reviews_n = row["# Reviews"]
        phone = row["Phone"]
        phone_tel = "+1" + re.sub(r"\D", "", phone)
        address = (row["Notes"].split(" | ")[0]).strip()

        slug = slugify(name)
        while slug in used_slugs:
            slug += "-2"
        used_slugs.add(slug)

        print(f"[{i}/{len(leads)}] {name} ({trade}) — fetching reviews…")
        place = fetch_place(f"{raw_name.split('|')[0].strip()}, {address}", api_key)
        revs = [r for r in place.get("reviews", []) if r.get("text", {}).get("text")]
        revs.sort(key=lambda r: r.get("rating", 0), reverse=True)
        owner = detect_owner(revs, name)

        # Hero + review cards from real reviews
        hero_quote = truncate(revs[0]["text"]["text"], 105) if revs else \
            f"Highly recommend — {rating} stars from {reviews_n} happy customers."
        hero_author = clean_text(revs[0].get("authorAttribution", {}).get("displayName", "A. Customer")) if revs else "A. Customer"

        review_cards = []
        for j, r in enumerate(revs[:3]):
            author = clean_text(r.get("authorAttribution", {}).get("displayName", "Customer")) or "Customer"
            initial = author[0].upper()
            color = AVATAR_COLORS[j % len(AVATAR_COLORS)]
            quote = html.escape(truncate(r["text"]["text"], 190))
            review_cards.append(
                f'<div class="review reveal"><div class="stars">★★★★★</div>'
                f'<p class="quote">"{quote}"</p>'
                f'<div class="by"><div class="av" style="background:{color}">{html.escape(initial)}</div>'
                f'<div><div class="nm">{html.escape(author)}</div><div class="src">via Google</div></div></div></div>')
        while len(review_cards) < 3:  # pad if fewer than 3 real reviews
            review_cards.append(
                f'<div class="review reveal"><div class="stars">★★★★★</div>'
                f'<p class="quote">"Fantastic service — {rating} stars from {reviews_n} customers across {area}."</p>'
                f'<div class="by"><div class="av" style="background:{AVATAR_COLORS[len(review_cards)%6]}">★</div>'
                f'<div><div class="nm">Verified Customer</div><div class="src">via Google</div></div></div></div>')

        avatars = []
        for j in range(3):
            a = clean_text(revs[j].get("authorAttribution", {}).get("displayName", "")) if j < len(revs) else ""
            initial = (a[0].upper() if a else "★")
            avatars.append(f'<span style="background:{AVATAR_COLORS[j]}">{html.escape(initial)}</span>')
        avatars.append(f'<span style="background:var(--brand)">+</span>')

        services_html = "".join(
            f'<div class="card reveal"><div class="iconbox"><svg class="ic" viewBox="0 0 24 24">{ICONS[k]}</svg></div>'
            f'<h3>{t}</h3><p>{b}</p></div>'
            for (k, t, b) in TRADE[trade]["services"])

        tc = TRADE[trade]
        short_area = area.split()[0] if area else "NYC"
        repl = {
            "{{TITLE}}": html.escape(f"{name} | {short_area} {tc['noun'].title()} — {rating}★ ({reviews_n} Reviews)"),
            "{{META_DESC}}": html.escape(f"{name}: top-rated {tc['noun']} in {area}. {rating}★ from {reviews_n} reviews. Call {phone}."),
            "{{BRAND}}": html.escape(name),
            "{{HERO_IMG}}": IMAGES[trade][0],
            "{{FEATURE_IMG}}": IMAGES[trade][1],
            "{{PHONE}}": html.escape(phone),
            "{{PHONE_TEL}}": phone_tel,
            "{{PILL}}": html.escape(f"{short_area}'s top-rated {tc['noun']}"),
            "{{H1_HTML}}": tc["h1"],
            "{{SUB}}": tc["sub"],
            "{{AREA}}": html.escape(area + ", NYC"),
            "{{HERO_AVATARS}}": "".join(avatars),
            "{{RATING}}": html.escape(str(rating)),
            "{{REVIEWS}}": html.escape(str(reviews_n)),
            "{{HERO_QUOTE}}": html.escape(hero_quote),
            "{{HERO_AUTHOR}}": html.escape(hero_author),
            "{{STAT3}}": tc["stat3"],
            "{{STAT_AREA}}": html.escape(short_area),
            "{{SERVICES_EYEBROW}}": tc["eyebrow"],
            "{{SERVICES_H2}}": tc["h2"],
            "{{SERVICES_SUB}}": tc["ssub"],
            "{{SERVICES_HTML}}": services_html,
            "{{REVIEWS_HTML}}": "".join(review_cards),
            "{{CTA_H}}": tc["cta_h"],
            "{{CTA_P}}": tc["cta_p"],
            "{{ADDRESS}}": html.escape(address),
        }
        page = template
        for k, v in repl.items():
            page = page.replace(k, v)

        out_dir = os.path.join(SITES_DIR, slug)
        index_path = os.path.join(out_dir, "index.html")
        if slug in PRESERVE and os.path.exists(index_path):
            print("   (kept existing hand-made site)")
        else:
            os.makedirs(out_dir, exist_ok=True)
            with open(index_path, "w") as f:
                f.write(page)

        manifest.append({
            "slug": slug, "name": name, "trade": trade, "noun": tc["noun"],
            "area": area, "rating": rating, "reviews": reviews_n, "phone": phone,
            "owner": owner, "hero_quote": hero_quote,
        })
        time.sleep(0.15)

    with open(os.path.join(TMP_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nBuilt {len(manifest)} sites in {SITES_DIR}/")
    print(f"Manifest -> {os.path.join(TMP_DIR, 'manifest.json')}")
    print("Next: deploy the sites/ folder, then run write_emails.py with the base URL.")


if __name__ == "__main__":
    main()
