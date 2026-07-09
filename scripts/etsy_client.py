"""
Read-only Etsy Open API v3 client.

This is used ONLY for public, read-only competitive research (checking
how many listings target a keyword, sampling competitor prices) in
trend_scan.py and pricing.py. It does NOT write anything to Etsy —
all writes go through the Make.com relay instead (see publish.py and
docs/make-scenario-setup.md).

Public search endpoints like /application/listings/active only need
the app's API key (keystring) in the x-api-key header — no OAuth
token or shop-level authorization required. Etsy's manual review
step is mainly a concern for write/commercial-scope access; a
narrowly-scoped, read-only app registration is a much smaller ask
and worth trying even if a broader app was previously rejected.
Register at https://www.etsy.com/developers/register requesting
only read access, keep the description explicitly scoped to
"read-only market research for my own product decisions."

Required environment variable (GitHub Actions secret):
    ETSY_KEY_STRING - App keystring from developers.etsy.com
"""

import os

ETSY_API_BASE = "https://api.etsy.com/v3"


class EtsyClient:
    def __init__(self):
        self.key_string = os.environ["ETSY_KEY_STRING"]

    def _headers(self):
        return {"x-api-key": self.key_string}
