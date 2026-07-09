# Etsy-Hermes Next Actions

Hermes should now operate from GitHub Issues and guarded workflows.

## Current state

Completed:

- Etsy silo control file exists.
- Draft-only config exists.
- Publish payload validator exists.
- PNG preview generation exists.
- Offline E2E dry run passed.

## Current human gate

Jason must ensure the Make.com Etsy connection is authorized and the Make scenario has the required modules.

Hermes cannot complete the Etsy OAuth approval click unless it is given browser-level control. Do not attempt to bypass this.

## Active task order

1. Finish Make.com relay: Issue #5
2. Add/run controlled one-draft workflow: Issue #6
3. Prepare first real keyword/product batch: Issue #7

## Controlled workflow

After Make.com is ready, run:

**Actions → Etsy-Hermes One Draft Publish Test → Run workflow**

Inputs:

- `confirm_make_ready`: `YES_CREATE_ONE_DRAFT`
- `max_listings`: `1`

This workflow is intentionally manual-only and sends exactly one draft listing to Make/Etsy.

## Do not do yet

- Do not enable auto-activation.
- Do not create active Etsy listings.
- Do not schedule real publishing.
- Do not create more than one real draft listing until the first draft is manually reviewed.
