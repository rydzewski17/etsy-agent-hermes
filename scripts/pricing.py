"""
Stage 5 - Pricing Agent

Sets a competitive price per bundle by sampling current Etsy listings
for the same keyword and asking Claude to recommend a price that's
competitive but not a race-to-the-bottom.
"""

import json
import os

from etsy_client import EtsyClient
from claude_client import call_claude_json

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
COPY_QUEUE_FILE = os.path.join(DATA_DIR, "copy_queue.json")
PUBLISH_QUEUE_FILE = os.path.join(DATA_DIR, "publish_queue.json")


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def sample_competitor_prices(etsy: EtsyClient, keyword: str, limit: int = 10):
    import requests
    r = requests.get(
        "https://api.etsy.com/v3/application/listings/active",
        headers=etsy._headers(),
        params={"keywords": keyword, "limit": limit},
        timeout=30,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    prices = []
    for item in results:
        price_obj = item.get("price", {})
        amount = price_obj.get("amount")
        divisor = price_obj.get("divisor", 100)
        if amount:
            prices.append(amount / divisor)
    return prices


def main():
    queue = load_json(COPY_QUEUE_FILE, {"ready_to_price": []})
    ready = queue["ready_to_price"]

    if not ready:
        print("Nothing ready to price.")
        return

    etsy = EtsyClient()
    publish_queue = load_json(PUBLISH_QUEUE_FILE, {"ready_to_publish": []})

    for brief in ready:
        try:
            comp_prices = sample_competitor_prices(etsy, brief["keyword"])
        except Exception as e:
            print(f"Price sampling failed for '{brief['keyword']}': {e}")
            comp_prices = []

        prompt = f"""Recommend a price in USD for a digital SVG cut-file
bundle ({len(brief.get('design_files', []))} designs) targeting the
keyword "{brief['keyword']}".

Competitor prices found for similar listings: {comp_prices or 'none found'}

Digital products on Etsy have near-zero marginal cost, so pricing should
optimize for conversion + perceived value, not just undercutting.
Return ONLY raw JSON: {{"price": 0.00, "rationale": "one sentence"}}
"""
        result = call_claude_json(prompt)
        brief["price"] = result["price"]
        brief["pricing_rationale"] = result["rationale"]
        brief["status"] = "ready_to_publish"
        publish_queue["ready_to_publish"].append(brief)

    save_json(PUBLISH_QUEUE_FILE, publish_queue)
    save_json(COPY_QUEUE_FILE, {"ready_to_price": []})
    print(f"Priced {len(ready)} bundles.")


if __name__ == "__main__":
    main()
