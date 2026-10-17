# Qualification Checklist — Is this a good target?

Use this while you fill in `lead-tracker.csv`. The whole point: don't waste time
building samples for businesses that won't buy.

## The 10-second test

Look at their Google Maps listing and ask:
1. **Are people clearly happy with them?** (good rating + real reviews)
2. **Is their online "front door" missing or ugly?** (no website, or an old one)

If both are YES → they're a target. They already make money and just need a better
front door. That's the easiest "yes" you'll ever get.

## The scoring system (0–5)

Give **1 point** for each that's true. Put the total in the "Target Score" column.

- [ ] **+1 — Rating is 4.3 or higher** (proof customers like them)
- [ ] **+1 — More than 25 reviews** (proof it's a real, busy business)
- [ ] **+1 — No website, OR the website is clearly old / broken / not mobile-friendly**
- [ ] **+1 — You can find a way to reach them** (email, contact form, or phone)
- [ ] **+1 — High-ticket trade** (one new job pays your whole fee — HVAC, roofing, etc.)

**Score 4–5** → 🔥 Hot. Build a sample now.
**Score 2–3** → 🤔 Maybe. Come back to these if the hot ones don't pan out.
**Score 0–1** → ⛔ Skip.

## Green flags (go for it)

- Reviews mention the *owner by name* ("Mike was great!") → easy to personalize.
- Recent reviews (this month) → business is active and reachable.
- "No website" link on their Google listing, or it points to a Facebook page only.
- Photos look like a real local operation (trucks, team, jobs).

## Red flags (skip)

- It's a big franchise / national chain (they have a marketing department already).
- Fewer than ~10 reviews (might be brand new or not serious).
- Rating under 4.0 with lots of angry reviews (different problem — not yours to fix yet).
- Already has a clean, modern, mobile-friendly website (nothing to sell them).

## How to find their email + owner name

Try these in order — stop as soon as you get one:
1. Their Google listing → "Website" or "Contact" link.
2. Their Facebook page → "About" / "Contact" section.
3. Any existing website → footer or "Contact" page.
4. Recent Google reviews → owner often replies and signs their first name.
5. **Just call** and say: *"Hi, who's the best person to send a quick email to about
   the business's website? And what's their email?"* (This works more often than you'd think.)

## Optional: auto-score in Google Sheets

After importing the CSV, put this in the Target Score column (row 2), then drag down.
It scores rating + review count + "no website" automatically:

```
=IF(D2="","",(IF(D2>=4.3,1,0))+(IF(E2>25,1,0))+(IF(OR(F2="None",F2="Outdated"),1,0)))
```

(That covers 3 of the 5 points automatically; add the last 2 by hand.)
