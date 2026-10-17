# n8n Workflow — NYC Home-Service Lead Finder

A **new, standalone** n8n workflow (separate from your ShipSlash SDR flow, since this is a
different business). On a schedule it searches Google Maps via the Places API, keeps only
businesses with **4.3★+, 15+ reviews, and no real website**, and appends them to a Google Sheet.

> **Scope:** this only *finds leads → Sheet*. Building the 20 sites + writing the AIDA emails
> stays in the local Python tools (`tools/build_sites.py`, `tools/write_emails.py`) — n8n can't
> generate/deploy websites. Run those locally when you want to build a fresh batch.

File to import: **`n8n-find-leads.json`** (in this folder).

## Setup (one time, ~5 min)

1. **Import** — in n8n: top-right menu **⋯ → Import from File** → choose `n8n-find-leads.json`.
   You'll see 3 nodes: *Every morning 9am → Find leads (Places API) → Append to Google Sheet*.

2. **Add your API key** — open the **“Find leads (Places API)”** Code node and replace
   `PASTE_YOUR_PLACES_API_KEY_HERE` with your Google Places key (same one in your `.env`).
   *(Safer option later: store it in n8n credentials/an env var instead of in the code.)*

3. **Prepare the Google Sheet** —
   - Make a Google Sheet, add a tab named **`Leads`**.
   - Put this header row in row 1 (exact names — the workflow maps to them automatically):
     `Business | Trade | Area | Rating | Reviews | Website | Phone | Address | Maps | Status | Found`
   - Copy the **Sheet ID** from the URL (the long part between `/d/` and `/edit`).

4. **Wire up the Sheets node** — open **“Append to Google Sheet”**:
   - **Credential:** pick your existing Google Sheets credential (the same one your ShipSlash flow uses).
   - **Document ID:** paste the Sheet ID.
   - **Sheet name:** `Leads`.

5. **Test** — click **Test workflow**. It runs the searches and appends rows. Check your Sheet.

6. **Schedule it** — toggle the workflow **Active**. The trigger fires daily at 9am
   (change time/frequency in the *“Every morning 9am”* node).

## Customize
- **Trades / neighborhoods:** edit the `TRADES` object at the top of the Code node.
- **Filters:** change `MIN_RATING` / `MIN_REVIEWS` in the same node.

## Good to know (honest notes)
- **Cost:** each run ≈ 12 API calls (~$0.50). Daily ≈ ~$15/mo — covered by your $300 free trial
  for now; set a budget alert in Google Cloud so you're never surprised after the trial.
- **Duplicates:** this *appends* every run, so the same business will repeat over multiple days.
  For now, sort/de-dupe in the Sheet by Phone. Later we can switch to “append or update” keyed on
  Phone so it self-dedupes.
- **n8n version:** the Code node uses `this.helpers.httpRequest` + top-level `await` (Code node v2).
  If your n8n is old and errors, tell me and I'll swap it for an HTTP Request node version.
