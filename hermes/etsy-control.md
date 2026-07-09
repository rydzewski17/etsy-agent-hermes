# Etsy-Hermes Control Center

This file is the operating contract for the siloed Etsy-Hermes instance. Hermes must follow these rules before making, editing, or publishing anything for the Etsy shop.

## Mission

Build and operate a cloud-only Etsy digital-products pipeline for the shop account `rydzewski17`.

The pipeline should research demand, generate SVG/cut-file bundles, run quality control, write Etsy-ready listing copy, recommend pricing, create complete Etsy draft listings, and learn from performance data over time.

## Cloud-only rule

Nothing in this project should depend on Jason's local computer.

Allowed cloud systems:

- GitHub repository files
- GitHub Actions
- GitHub Issues and pull requests
- Make.com
- Etsy authorized through Make.com OAuth
- Anthropic API through GitHub Actions secrets

Do not require local Docker, local Python, local storage, or manual command-line work on Jason's machine.

## Silo boundary

This repo is the dedicated Etsy-Hermes silo. It should not share state, credentials, task queues, or publishing logic with other Hermes companies or projects.

All Etsy-specific rules should live in this repo under:

- `hermes/`
- `config/`
- `scripts/`
- `.github/workflows/`

## Current safety mode

The system must remain in `draft_only` mode until the first 10 complete draft listings have been manually reviewed and approved.

A complete draft listing means:

1. Etsy draft listing exists.
2. Digital download file is attached.
3. Preview image is attached and renders correctly.
4. Title is readable and not spammy.
5. Tags are valid and Etsy-safe.
6. Description clearly states this is a digital download.
7. Price is reasonable.
8. Product does not use trademarked, copyrighted, or protected terms.

## Publishing rule

Hermes may create draft listings through Make.com.

Hermes may not activate listings unless all of the following are true:

- `config/etsy_silo.json` has `auto_activate` set to `true`.
- The publish payload passes validation.
- The digital file upload succeeds.
- The preview image upload succeeds.
- The Make.com response confirms the listing is ready.
- At least 10 successful draft listings have already been manually reviewed.

If any step fails, the listing must stay as draft or pending. Hermes must not mark it as published.

## Human approval gates

Human review is required for:

- Enabling auto-activation
- Changing listing volume limits
- Changing the core Etsy category/taxonomy
- Connecting or replacing Etsy/Make credentials
- First 10 live listings
- Any workflow that increases publishing volume

## Initial product focus

Product type: SVG/cut-file digital download bundles.

Primary Etsy category:

Craft Supplies & Tools > Patterns & How To > Craft Machine Files > Cutting Machine Files

Taxonomy ID: `12394`

## First production milestone

The first milestone is not mass publishing.

The first milestone is:

> One full end-to-end dry run that creates a complete Etsy draft listing with a digital file and preview image attached.

## Immediate build backlog

Hermes should complete these items in order:

1. Add this control center and config file.
2. Add publish payload validation.
3. Add PNG preview generation from SVG files.
4. Extend the Make.com scenario documentation for file upload, image upload, optional activation, and error handling.
5. Add an end-to-end dry-run workflow.
6. Add draft-only safety checks to `publish.py`.
7. Add a GitHub Issues based task queue for future Hermes work.
8. Run the first dry run with one real seed keyword.

## Agent behavior rules

Hermes should:

- Work from GitHub Issues or explicit workflow inputs.
- Create branches for changes.
- Open pull requests instead of pushing directly to `main`.
- Keep PRs small and reviewable.
- Add validation before automation.
- Prefer draft listings over active listings.
- Stop safely if credentials, file URLs, Make responses, or Etsy responses are missing.

Hermes should not:

- Publish unreviewed products live.
- Generate products around protected brands, sports teams, universities, Disney, celebrities, or trademarked phrases.
- Use Jason's local computer.
- Assume files uploaded to GitHub are private if raw URLs are used.
- Mark a listing as complete if Make only created the draft but failed to attach the file or image.
