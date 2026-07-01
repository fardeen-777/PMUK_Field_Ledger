# PMUK Field Staff Ledger

A searchable, month-by-month history of PMUK field staff designations and
postings, built from the monthly "MF Field Staff Status" workbooks.

## Files

- `index.html` — the website. Static, doesn't change month to month. Has
  three tabs: **Search** (name/PIN/branch lookup + profile cards),
  **Transfers** (month-by-month list of every branch/area/zone move), and
  **Structure Map** (Region → Area → Branch org hierarchy, built from the
  latest month's file).
- `data.json` — the employee dataset the site reads. **This is the only file
  that changes each month.**
- `scripts/build_data.py` — reference script showing how `data.json` is
  generated from the monthly Excel files (for documentation / if you ever
  want to run it yourself).

## Deploying on GitHub Pages

1. Create a repo (e.g. `pmuk-field-staff-ledger`) and push `index.html` and
   `data.json` to the root (or to a `/docs` folder — either works, just set
   it in step 2).
2. Repo → Settings → Pages → Source: deploy from branch → pick `main` and
   the folder (`/root` or `/docs`).
3. GitHub gives you a URL like
   `https://<username>.github.io/pmuk-field-staff-ledger/`. That's it — no
   build step, no server.

Because the site fetches `data.json` at runtime, it must be served over
http(s) (GitHub Pages does this automatically). Opening `index.html`
directly as a local file won't load the data — that's a browser security
restriction on `fetch()`, not a bug.

## Monthly update workflow

Each month:

1. Send me that month's `MF Field Staff Status (<Month>, <Year>).xlsx` file.
2. I regenerate `data.json` (adds the new month as a column in the timeline,
   recalculates every promotion/transfer event across the full history).
3. You replace `data.json` in the repo with the new one and push:
   ```
   git add data.json
   git commit -m "Add <Month> <Year> data"
   git push
   ```
4. GitHub Pages updates automatically within a minute or two — no changes
   to `index.html` needed.

## Data notes (carried over from the FY25-26 build)

- One record (PIN 0212800125, Jul 25) has a corrupted Designation cell in
  the source file containing a filename instead of a role.
- "Gowrichanna Branch" and "Gowrichhanna Branch" appear to be the same
  branch spelled two ways in the source files — currently kept as separate
  locations since I don't silently merge/guess at data.
- A handful of organization-wide renames (Zone → Region, "Admin & Accounts"
  → "Finance & Accounts", plus a couple of spacing/spelling variants in
  designations) are normalized **only for change-detection purposes** —
  they won't show up as a false promotion/transfer, but each month's
  timeline still displays the exact wording from that month's source file.
  See `DESIG_SYNONYMS` and `loc_cmp_key()` in `scripts/build_data.py` if a
  future rename needs to be added to that list.
