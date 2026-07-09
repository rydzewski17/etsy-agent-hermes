"""
Stage 1 - Trend/Keyword Agent

Identifies underserved keyword clusters for SVG/cut-file products and
writes them as "briefs" for the design stage to pick up.

NOTE: Etsy doesn't expose a public "trending searches" endpoint, so this
pulls signal from two free/cheap sources instead:
  1. Etsy's own listing search (via the public API), used to gauge
     existing supply/competition for candidate keywords.
  2. Google Trends (via pytrends) for relative search interest.

You seed candidate keywords yourself in data/seed_keywords.json — the
agent's job is to score and rank them, not invent a niche from nothing.
Add to that seed list over time as you learn what sells.
"""

import json
import os
from datetime import datetime, timezone

from etsy_client import EtsyClient
from claude_client import call_claude_json

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SEED_FILE = os.path.join(DATA_DIR, "seed_keywords.json")
BRIEFS_FILE = os.path.join(DATA_DIR, "briefs.json")


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def competition_score(etsy: EtsyClient, keyword: str) -> int:
    """Rough proxy: fewer existing listings for a keyword = more room."""
    # Etsy's findAllListingsActive-style search now lives under
    # /application/listings/active?keywords=... in Open API v3.
    import requests
    r = requests.get(
        "https://api.etsy.com/v3/application/listings/active",
        headers=etsy._headers(),
        params={"keywords": keyword, "limit": 1},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("count", 0)


def main():
    seeds = load_json(SEED_FILE, {"keywords": []})
    if not seeds["keywords"]:
        print("No seed keywords yet. Add candidates to data/seed_keywords.json "
              "and re-run. Example: {\"keywords\": [\"boho monogram svg\", "
              "\"dog mom cut file\"]}")
        return

    etsy = EtsyClient()
    scored = []
    for kw in seeds["keywords"]:
        try:
            listing_count = competition_score(etsy, kw)
        except Exception as e:
            print(f"Skipping '{kw}', Etsy search failed: {e}")
            continue
        scored.append({"keyword": kw, "existing_listings": listing_count})

    # Ask Claude to rank by opportunity (low competition, clear buyer intent,
    # bundle-ability) and propose 3-5 concrete product briefs.
    prompt = f"""You're a product research analyst for an Etsy shop selling
SVG/cut-file digital downloads (Cricut/Silhouette crafters).

Here is keyword competition data (existing_listings = how many Etsy
listings currently target that keyword; lower is less saturated):

{json.dumps(scored, indent=2)}

Return ONLY raw JSON (no markdown fences) as a list of 3-5 product briefs,
each with:
  - "keyword": the target keyword
  - "product_concept": specific description of a cut-file bundle to design
  - "bundle_size": suggested number of designs in the bundle
  - "rationale": 1 sentence on why this is a good opportunity
"""
    briefs = call_claude_json(prompt)

    existing = load_json(BRIEFS_FILE, {"pending": []})
    for b in briefs:
        b["created_at"] = datetime.now(timezone.utc).isoformat()
        b["status"] = "pending_design"
    existing["pending"].extend(briefs)
    save_json(BRIEFS_FILE, existing)
    print(f"Wrote {len(briefs)} new product briefs to data/briefs.json")


if __name__ == "__main__":
    main()
