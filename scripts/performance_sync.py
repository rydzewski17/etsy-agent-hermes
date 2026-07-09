"""
Stage 7 - Performance Loop

Nightly pull of views/favorites for each published listing, written
back to data/performance.json. trend_scan.py can be extended later
to weight new keyword suggestions toward niches where past bundles
over/under-performed.

Uses the public GET /v3/application/listings/{listing_id} endpoint,
which only needs the read-only API key (no shop-level OAuth). If
Etsy's response for your shop doesn't include views/num_favorers on
that public object, route this through a second Make.com webhook
instead (same pattern as publish.py) since shop-owner analytics
fields may require the authorized connection.
"""

import json
import os
import requests
from datetime import datetime, timezone

from etsy_client import EtsyClient, ETSY_API_BASE

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PUBLISHED_FILE = os.path.join(DATA_DIR, "published.json")
PERFORMANCE_FILE = os.path.join(DATA_DIR, "performance.json")


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    published = load_json(PUBLISHED_FILE, {"listings": []})
    if not published["listings"]:
        print("No published listings yet.")
        return

    etsy = EtsyClient()
    performance = load_json(PERFORMANCE_FILE, {"snapshots": []})

    for listing in published["listings"]:
        try:
            r = requests.get(
                f"{ETSY_API_BASE}/application/listings/{listing['listing_id']}",
                headers=etsy._headers(), timeout=30,
            )
            r.raise_for_status()
            stats = r.json()
            performance["snapshots"].append({
                "listing_id": listing["listing_id"],
                "keyword": listing["keyword"],
                "views": stats.get("views"),
                "num_favorers": stats.get("num_favorers"),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            print(f"Couldn't fetch stats for listing {listing['listing_id']}: {e}")

    save_json(PERFORMANCE_FILE, performance)
    print(f"Synced performance for {len(published['listings'])} listings.")


if __name__ == "__main__":
    main()
