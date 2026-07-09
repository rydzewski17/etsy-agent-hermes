# Make.com Scenario Setup (Etsy publish relay)

This replaces "register your own Etsy app for write access" with
"authorize Make.com's already-approved Etsy integration to act on
your shop." You're granting a third-party app permission via a
normal OAuth consent screen — the same kind of click you'd do
connecting any app to your Google or Etsy account — not submitting
anything for Etsy's developer review.

## 1. Create a Make.com account (free tier is enough to start)

https://www.make.com — the free plan includes enough operations/month
for a low-volume listing pipeline. Check current limits on their
pricing page since these change.

## 2. Connect your Etsy shop to Make

1. Create a new Scenario
2. Add an **Etsy** module (search "Etsy" in the module picker)
3. Click **Add** next to the connection field
4. This opens Etsy's normal OAuth authorization screen — log in with
   your existing (fine, unbanned) shop account and approve access
5. Done — Make now has an authorized connection to your shop, without
   you registering or submitting any app of your own

## 3. Build the scenario

**Module 1 — Webhooks: Custom webhook**
- Add a "Custom webhook" trigger module
- Click "Add" to create a new webhook, name it e.g. `etsy-publish`
- Copy the generated webhook URL — this is your `MAKE_WEBHOOK_URL`
  GitHub secret
- Click "Redetermine data structure" once you've sent a test payload
  from `publish.py` (or manually POST a sample JSON matching the
  shape in `publish.py`'s `payload` dict) so Make knows the schema

**Module 2 — Etsy: Create a Listing**
Map these fields from the webhook payload:
- Title → `{{title}}`
- Description → `{{description}}`
- Price → `{{price}}`
- Quantity → `{{quantity}}`
- Who made it → `i_did`
- When made → `made_to_order`
- Taxonomy ID → `{{taxonomy_id}}`
- Is digital → `true`
- Tags → `{{tags}}` (map as array)
- Materials → `digital file`
- State → `draft` (don't activate yet — do that last, after files
  are confirmed uploaded)

This module returns a `listing_id` — used by the next two modules.

**Module 3 — Etsy: Make an API Call** (this covers the missing
"upload digital file" action)
- Connection: use the same Etsy connection
- URL: `/application/shops/{{shop_id}}/listings/{{listing_id}}/files`
- Method: `POST`
- Body type: `Form-data`
- Add a form-data field with key `file`, type `File`, and map its
  source to `{{digital_file_url}}` — Make can fetch a URL into a
  file field directly (use an intermediate "Get a file" / HTTP
  "Get a file" module first if the API-call module doesn't accept a
  URL directly for this field; check Make's current module docs, this
  detail has shifted before)
- Add form-data field `rank` = `1`

**Module 4 — Etsy: Upload a Listing Image**
- Listing ID → `{{listing_id}}` from Module 2
- Image → `{{preview_image_url}}`
- Rank → `1`

**Module 5 — Etsy: Update a Listing**
- Listing ID → `{{listing_id}}`
- State → `active`

**Module 6 — Webhook response**
- Add a "Webhooks: Webhook response" module
- Status: 200
- Body: `{"listing_id": "{{listing_id}}", "status": "active"}`
- This is what `publish.py` reads back to confirm success

## 4. Error handling (important for unattended runs)

Add error handlers on Modules 2-5 (right-click each module → "Add
error handler") that route to a webhook response with an error
status instead of silently failing, so `publish.py` can correctly
mark a bundle as still-pending rather than falsely recording it as
published.

## 5. Test before trusting it with real listings

Manually trigger `publish.yml` from the GitHub Actions tab with one
seeded brief and confirm:
- the listing actually appears as a **draft** first (don't let module
  ordering accidentally activate before the file upload succeeds)
- the digital file downloads correctly from the live listing
- the preview image displays correctly

Only after that dry run succeeds should you let the full pipeline
run unattended on its cron schedule.
