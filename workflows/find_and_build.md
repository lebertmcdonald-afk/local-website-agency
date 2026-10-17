# Workflow: Find Leads → Build Sample Site

**Objective:** Find local service businesses with good Google reviews but no/weak
website, then build a sample website for the best one to use as outreach bait.

## Inputs
- `GOOGLE_PLACES_API_KEY` in `../.env` (project root).
- A trade + set of city/neighborhood searches (configured in the tools).

## Tools
- `tools/find_leads.py` — pulls + filters leads, writes `nyc-pest-leads.csv`.
- `tools/get_reviews.py "<Business Name City NY>"` — pulls one business's details +
  recent reviews; saves `.tmp/place_details.json`.

## Steps
1. **Find leads.** Run `python3 tools/find_leads.py`.
   - Edit the CONFIG block (TRADE, QUERIES, MIN_RATING, MIN_REVIEWS) to change trade/city.
   - Output: `nyc-pest-leads.csv` (rating ≥ 4.3, ≥ 25 reviews, no real website).
2. **Pick the top target** by reviews/score from the CSV.
3. **Pull review context.** Run `python3 tools/get_reviews.py "<name + area>"`.
4. **Grab email + owner name by hand** (API doesn't give these — see `qualification-checklist.md`).
5. **Build the sample site** in `sites/<business-slug>/index.html`, using the real
   services, rating, review count, and 2–3 real review quotes for trust.
6. **Send outreach** using `outreach-email-template.md` with the live preview link.

## Expected outputs
- `nyc-pest-leads.csv` (deliverable: lead list).
- `sites/<business>/index.html` (deliverable: sample site to preview/deploy).

## Edge cases / lessons learned
- **macOS SSL:** this Mac's Python has no usable default CA file. Tools point the SSL
  context at `/etc/ssl/cert.pem`. Reuse `make_ssl_context()` for any new HTTPS tool here.
- **Cost:** `find_leads.py` ≈ $1 per full run; `get_reviews.py` ≈ a few cents (reviews
  field is the priciest SKU). Both covered by the $300 free trial. Ask before re-running
  `find_leads.py` unnecessarily.
- **Reviews field** returns up to 5 reviews per place — enough for website social proof.
- **Don't fabricate** business claims (licenses, years in business). Only use what the
  data/reviews support; mark anything assumed as a placeholder to verify before go-live.
