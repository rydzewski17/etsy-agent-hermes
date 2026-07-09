# Etsy Digital Products Agent Pipeline

A fully hosted (GitHub Actions only — no server, no Docker) agent
pipeline that researches, designs, lists, prices, and publishes SVG
cut-file bundles to Etsy, then feeds sales performance back into the
next round of research.

## Why this doesn't use Etsy's API directly

Etsy requires manual review to approve write access for a
self-registered developer app. Since a prior app of yours was
rejected, this pipeline routes the actual listing-creation step
through **Make.com** instead: Make already has an Etsy-approved
integration, so you authorize *Make* to act on your shop via a
normal OAuth consent click — no developer application, no review
queue. See `docs/make-scenario-setup.md` for the one-time scenario
build.

Read-only competitive research (checking keyword competition,
sampling competitor prices) still uses a lightweight Etsy API key
directly, since public search endpoints only need the keystring, not
shop-level write authorization — a much smaller ask than what got
rejected before.

## Pipeline stages

| # | Workflow | Script | What it does |
|---|----------|--------|---------------|
| 1 | `1 - Trend Scan` | `trend_scan.py` | Scores seed keywords by Etsy competition (read-only key), writes product briefs |
| 2 | `2 - Design Generation` | `design_gen.py` | Generates SVG cut-files per brief via Claude |
| 3 | `3 - QC Filter` | `qc_filter.py` | Validates SVGs, flags dupes/broken files |
| 4 | `4 - Listing Copy` | `listing_copy.py` | Writes SEO title/description/tags |
| 5 | `5 - Pricing` | `pricing.py` | Recommends price vs. competitor sample (read-only key) |
| 6 | `6 - Publish to Etsy` | `prepare_bundles.py` + `publish.py` | Zips SVG files, creates PNG previews, commits assets so they're fetchable, then relays to Make.com to create/upload/activate the listing |
| 7 | `7 - Performance Sync` | `performance_sync.py` | Nightly pull of listing stats for feedback |

Stages 1-6 chain automatically via `workflow_run` triggers. Stage 1
runs weekly (Monday), stage 7 runs nightly. Everything is also
manually triggerable from the Actions tab (`workflow_dispatch`).

## One-time setup

### 1. Register a narrow, read-only Etsy app
Go to https://www.etsy.com/developers/register, request **read-only
personal access**, and describe it explicitly as market-research
only (checking listing counts and prices for your own product
decisions) — not for automated listing creation. This is a much
smaller ask than commercial write access and worth trying even after
a broader app was rejected.

### 2. Set up the Make.com relay
Follow `docs/make-scenario-setup.md` in full. At the end you'll have
a webhook URL.

### 3. Add GitHub repo secrets
Settings → Secrets and variables → Actions → New repository secret:

- `ANTHROPIC_API_KEY`
- `ETSY_KEY_STRING` (from step 1)
- `MAKE_WEBHOOK_URL` (from step 2)

### 4. Confirm your Etsy taxonomy ID
The Etsy-Hermes silo config stores the confirmed taxonomy ID in
`config/etsy_silo.json`. The current configured category is:

Craft Supplies & Tools > Patterns & How To > Craft Machine Files > Cutting Machine Files

### 5. Seed your first keywords
Edit `data/seed_keywords.json` with real candidate keywords for your
niche, commit, push. Stage 1 will pick them up on its next run (or
trigger it manually from the Actions tab to test immediately).

## Notes / things to sanity-check before trusting this unattended

- **Test the Make scenario manually first** with one seeded brief
  before letting the full pipeline run unattended — see the last
  section of `docs/make-scenario-setup.md`.
- **PNG preview images**: `prepare_bundles.py` now converts the first
  SVG in each bundle into a PNG preview under `data/previews/` using
  `cairosvg`. The publish validator blocks listings if no preview URL
  is available.
- **Draft-only mode**: `config/etsy_silo.json` controls activation.
  Listings should remain drafts unless auto-activation is explicitly
  enabled later.
- **Repo visibility**: bundle and preview files are served via
  `raw.githubusercontent.com`, which requires the repo (or at least
  that path) to be public, or you'll need a token-authenticated fetch
  in the Make scenario instead. If you want the repo private, swap
  the raw-URL approach for uploading bundles to a scratch storage
  bucket (S3, R2, or even a private Gist) and adjust `publish.py`'s
  `raw_url()` accordingly.
- Nothing auto-activates a listing if any step in the Make scenario
  fails — build the error handlers described in
  `docs/make-scenario-setup.md` so a partial failure doesn't leave a
  broken listing live.
