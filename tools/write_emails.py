#!/usr/bin/env python3
"""
write_emails.py  —  WAT tool
----------------------------
Reads .tmp/manifest.json (from build_sites.py) + the deployed base URL, and writes
a personalized AIDA outreach email per business to outreach-emails.md, plus a
working tracker leads-final.csv (business -> live link -> status).

Usage (from project root):
    python3 tools/write_emails.py https://sites-xxxx.vercel.app
"""

import csv
import json
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
MANIFEST = os.path.join(ROOT_DIR, ".tmp", "manifest.json")
EMAILS_MD = os.path.join(ROOT_DIR, "outreach-emails.md")
FINAL_CSV = os.path.join(ROOT_DIR, "leads-final.csv")

# A few subject templates, rotated for variety (each still uses the business's real stats).
SUBJECTS = [
    "{name}: {reviews} reviews and still no website?",
    "built {name} a website (free sample inside)",
    "quick idea for {name} — {rating}★ deserves a real site",
    "{name} — your {reviews} reviews, finally with a home online",
]


def email_body(m, link):
    owner = m.get("owner") or ""
    greet = f"Hi {owner}," if owner else "Hi there,"
    noun = m["noun"]
    area = m["area"]
    short = area.split()[0] if area else "your area"
    quote = m.get("hero_quote", "").strip().rstrip("…").rstrip(".")
    interest = (f'One customer even wrote: "{quote}." That kind of reputation is rare. '
                if quote else "Your reviews speak for themselves. ")
    return f"""{greet}

I was looking at {noun}s in {area} and {m['name']} really stood out — {m['rating']}★ from {m['reviews']} reviews is genuinely impressive.

{interest}But when someone in {short} searches "{noun} near me" at 9pm, there's no website for them to land on — so those customers go to whoever shows up first instead.

So I built you a free sample to show what it could look like — your real services, your actual Google reviews, click-to-call, and mobile-ready. It's already live here:

{link}

If you like it, I can have it on your own web address in about 10 minutes. Want me to? Just reply "yes" — or call/text me anytime.

— [Your Name] · [Your Phone]

(Not interested? Just reply "no thanks" and I won't follow up.)"""


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: python3 tools/write_emails.py <base_url>')
    base = sys.argv[1].rstrip("/")

    with open(MANIFEST) as f:
        items = json.load(f)

    md = [f"# Outreach Emails — {len(items)} NYC prospects\n",
          f"**Live preview base:** {base}\n",
          "**Before sending:** replace `[Your Name]` / `[Your Phone]`, send a handful a day "
          "from your own inbox (don't blast), and grab each owner's email from their Google "
          "listing / Facebook — or just call and ask.\n", "---\n"]

    rows = []
    for i, m in enumerate(items, 1):
        link = f"{base}/{m['slug']}/"
        subject = SUBJECTS[(i - 1) % len(SUBJECTS)].format(**m)
        body = email_body(m, link)
        owner = m.get("owner") or "(not detected — verify)"
        md.append(
            f"## {i}. {m['name']}  ·  {m['trade']}  ·  {m['area']}\n"
            f"- ☎ **{m['phone']}**  |  ⭐ {m['rating']} ({m['reviews']} reviews)\n"
            f"- 🔗 Live site: {link}\n"
            f"- 👤 Owner (detected): {owner}\n"
            f"- ✉️ Find their email: their Google listing / Facebook, or call and ask.\n\n"
            f"**Subject:** {subject}\n\n"
            f"{body}\n\n---\n")
        rows.append([i, m["name"], m["trade"], m["area"], m["rating"], m["reviews"],
                     m["phone"], owner, link, "", "New"])

    with open(EMAILS_MD, "w") as f:
        f.write("\n".join(md))

    with open(FINAL_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["#", "Business Name", "Trade", "City/Area", "Rating", "# Reviews",
                    "Phone", "Owner (detected)", "Live Link", "Email", "Status"])
        w.writerows(rows)

    print(f"Wrote {len(items)} emails -> {EMAILS_MD}")
    print(f"Wrote tracker -> {FINAL_CSV}")


if __name__ == "__main__":
    main()
