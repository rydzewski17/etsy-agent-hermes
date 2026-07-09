"""
Stage 4 - Listing Copywriter Agent

Generates Etsy-SEO-optimized title, description, and tags for each
QC-approved bundle. Etsy allows 13 tags max (20 chars each) and
~140 char titles — the prompt enforces those limits directly.
"""

import json
import os

from claude_client import call_claude_json

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
APPROVED_FILE = os.path.join(DATA_DIR, "approved.json")
COPY_QUEUE_FILE = os.path.join(DATA_DIR, "copy_queue.json")


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    approved = load_json(APPROVED_FILE, {"ready_for_listing": []})
    ready = approved["ready_for_listing"]

    if not ready:
        print("Nothing ready for copywriting.")
        return

    copy_queue = load_json(COPY_QUEUE_FILE, {"ready_to_price": []})

    for brief in ready:
        prompt = f"""Write Etsy SEO listing copy for a digital SVG cut-file
bundle. Product concept: {brief['product_concept']}
Target keyword: {brief['keyword']}
Bundle size: {len(brief.get('design_files', []))} designs

Return ONLY raw JSON (no markdown fences):
{{
  "title": "under 140 chars, front-load the primary keyword",
  "description": "3-4 short paragraphs: what's included, file formats,
    compatible cutting machines (Cricut/Silhouette/Glowforge), instant
    download note, usage rights (personal use)",
  "tags": ["exactly 13 tags, each under 20 characters, no duplicates"]
}}
"""
        copy = call_claude_json(prompt)
        brief["listing_copy"] = copy
        brief["status"] = "ready_to_price"
        copy_queue["ready_to_price"].append(brief)

    save_json(COPY_QUEUE_FILE, copy_queue)
    save_json(APPROVED_FILE, {"ready_for_listing": [],
                              "needs_human_review": approved.get("needs_human_review", [])})
    print(f"Wrote listing copy for {len(ready)} bundles.")


if __name__ == "__main__":
    main()
