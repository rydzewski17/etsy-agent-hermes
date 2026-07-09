"""
Stage 6b - Publisher Agent (Make.com relay version)

Etsy's Open API v3 requires either your own approved developer app
(write access, which needs Etsy's manual review) OR an already-
authorized third-party integration acting on your behalf. Since a
self-registered app isn't a reliable option right now, this stage
routes the actual Etsy write operations through a Make.com scenario:
Make already has an Etsy-approved integration, so you authorize
*Make* to act on your shop (a normal OAuth consent click on your own
account, not a developer application under review), and this script
just POSTs the finished, ready-to-list bundle to a Make webhook.

Requires prepare_bundles.py to have already run AND the resulting
files to already be committed+pushed to the repo (the workflow does
this in order), so raw.githubusercontent.com URLs are live by the
time this script builds its payload.

See docs/make-scenario-setup.md for the exact Make scenario to build.
"""

import json
import os
from datetime import datetime, timezone

import requests

from validate_publish_payload import validate_payload

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
CONFIG_FILE = os.path.join(REPO_ROOT, "config", "etsy_silo.json")
PUBLISH_QUEUE_FILE = os.path.join(DATA_DIR, "publish_queue.json")
PUBLISHED_FILE = os.path.join(DATA_DIR, "published.json")

MAKE_WEBHOOK_URL = os.environ["MAKE_WEBHOOK_URL"]

# Set these to match your repo so raw file URLs resolve correctly.
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "")  # auto-set by Actions, "owner/repo"
GITHUB_BRANCH = os.environ.get("GITHUB_REF_NAME", "main")


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def raw_url(repo_relative_path: str) -> str:
    return (f"https://raw.githubusercontent.com/{GITHUB_REPO}/"
            f"{GITHUB_BRANCH}/{repo_relative_path}")


def build_payload(brief, config):
    copy = brief.get("listing_copy", {})
    taxonomy_id = brief.get("taxonomy_id") or config.get("taxonomy_id")
    quantity = config.get("default_quantity", 999)

    # Safety default: draft unless the silo config explicitly allows activation.
    state = "active" if config.get("auto_activate") else "draft"

    return {
        "title": copy.get("title", brief["keyword"])[:140],
        "description": copy.get("description", ""),
        "price": brief.get("price", 4.99),
        "quantity": quantity,
        "taxonomy_id": taxonomy_id,
        "tags": copy.get("tags", [])[:13],
        "materials": ["digital file"],
        "digital_file_url": raw_url(brief["bundle_repo_path"]),
        "preview_image_url": (
            raw_url(brief["preview_repo_path"])
            if brief.get("preview_repo_path") else None
        ),
        "keyword": brief["keyword"],
        "state": state,
    }


def main():
    config = load_json(CONFIG_FILE, {})
    queue = load_json(PUBLISH_QUEUE_FILE, {"ready_to_publish": []})
    ready = [b for b in queue["ready_to_publish"] if b.get("bundle_repo_path")]

    if not ready:
        print("Nothing ready to publish (run prepare_bundles.py + commit first).")
        return

    published = load_json(PUBLISHED_FILE, {"listings": []})
    still_pending = []

    for brief in ready:
        payload = build_payload(brief, config)
        is_valid, validation_errors = validate_payload(payload, config)

        if not is_valid:
            print(f"FAILED validation for '{brief['keyword']}' (will retry after fixes):")
            for error in validation_errors:
                print(f"- {error}")
            still_pending.append(brief)
            continue

        try:
            resp = requests.post(MAKE_WEBHOOK_URL, json=payload, timeout=60)
            resp.raise_for_status()
            result = resp.json()  # expects {"listing_id": ..., "status": "draft" or "active"}

            listing_status = result.get("status", payload.get("state", "draft"))
            published["listings"].append({
                "listing_id": result.get("listing_id"),
                "keyword": brief["keyword"],
                "title": payload["title"],
                "price": brief.get("price"),
                "status": listing_status,
                "published_at": datetime.now(timezone.utc).isoformat(),
            })
            print(f"Created Etsy listing via Make: {result.get('listing_id')} - {payload['title']} ({listing_status})")

        except Exception as e:
            print(f"FAILED to publish '{brief['keyword']}' via Make webhook: {e} "
                  f"(will retry next run)")
            still_pending.append(brief)

    save_json(PUBLISHED_FILE, published)
    save_json(PUBLISH_QUEUE_FILE, {"ready_to_publish": still_pending})


if __name__ == "__main__":
    main()
