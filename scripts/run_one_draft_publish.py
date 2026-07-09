"""
Controlled one-draft Etsy publish test.

This script is intentionally stricter than the normal publish flow. It is
for the first real Make.com/Etsy integration test and will only send one
validated draft listing payload to Make.

Safety behavior:
- Requires config mode to remain draft-only.
- Refuses to run if auto_activate is true.
- Sends at most one listing.
- Requires Make to return status=draft.
- Requires Make to confirm file and image upload.
- Moves successful draft listings into data/drafts_pending_review.json.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from publish import build_payload
from validate_publish_payload import validate_payload

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
CONFIG_FILE = os.path.join(REPO_ROOT, "config", "etsy_silo.json")
PUBLISH_QUEUE_FILE = os.path.join(DATA_DIR, "publish_queue.json")
DRAFT_RESULTS_FILE = os.path.join(DATA_DIR, "draft_publish_test_results.json")
DRAFTS_PENDING_REVIEW_FILE = os.path.join(DATA_DIR, "drafts_pending_review.json")

MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL")


def load_json(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def fail(message: str) -> int:
    print(f"ERROR: {message}")
    return 1


def assert_safe_config(config: Dict[str, Any]) -> None:
    if config.get("auto_activate") is not False:
        raise RuntimeError("Refusing to run: config auto_activate must be false")

    if config.get("mode") != "draft_only":
        raise RuntimeError("Refusing to run: config mode must be draft_only")

    publish_rules = config.get("publish_rules", {})
    if publish_rules.get("activate_listings_allowed") is not False:
        raise RuntimeError("Refusing to run: activate_listings_allowed must be false")


def validate_make_response(result: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    if not result.get("listing_id"):
        errors.append("Make response missing listing_id")

    if result.get("status") != "draft":
        errors.append(f"Make response status must be draft; got {result.get('status')}")

    if result.get("file_uploaded") is not True:
        errors.append("Make response must include file_uploaded=true")

    if result.get("image_uploaded") is not True:
        errors.append("Make response must include image_uploaded=true")

    return errors


def main() -> int:
    if not MAKE_WEBHOOK_URL:
        return fail("MAKE_WEBHOOK_URL secret is required")

    config = load_json(CONFIG_FILE, {})
    try:
        assert_safe_config(config)
    except RuntimeError as exc:
        return fail(str(exc))

    queue = load_json(PUBLISH_QUEUE_FILE, {"ready_to_publish": []})
    ready = [brief for brief in queue.get("ready_to_publish", []) if brief.get("bundle_repo_path")]

    if not ready:
        return fail("No prepared listing found in data/publish_queue.json. Run prepare_bundles.py first.")

    brief = ready[0]
    remaining = ready[1:]

    payload = build_payload(brief, config)
    payload["state"] = "draft"

    is_valid, validation_errors = validate_payload(payload, config)
    if not is_valid:
        print("Payload failed validation:")
        for error in validation_errors:
            print(f"- {error}")
        return 1

    print("Payload validation passed. Sending exactly one draft listing to Make.com...")

    try:
        response = requests.post(MAKE_WEBHOOK_URL, json=payload, timeout=90)
        response.raise_for_status()
        result = response.json()
    except Exception as exc:
        return fail(f"Make webhook request failed: {exc}")

    response_errors = validate_make_response(result)
    if response_errors:
        print("Make response failed validation:")
        for error in response_errors:
            print(f"- {error}")
        print("Raw Make response:")
        print(json.dumps(result, indent=2))
        return 1

    now = datetime.now(timezone.utc).isoformat()
    draft_record = {
        "listing_id": result.get("listing_id"),
        "status": "draft",
        "keyword": brief.get("keyword"),
        "title": payload.get("title"),
        "price": payload.get("price"),
        "file_uploaded": result.get("file_uploaded"),
        "image_uploaded": result.get("image_uploaded"),
        "created_at": now,
        "make_response": result,
        "payload": payload,
    }

    drafts_pending_review = load_json(DRAFTS_PENDING_REVIEW_FILE, {"drafts": []})
    drafts_pending_review["drafts"].append(draft_record)
    save_json(DRAFTS_PENDING_REVIEW_FILE, drafts_pending_review)

    results = load_json(DRAFT_RESULTS_FILE, {"runs": []})
    results["runs"].append({
        "run_at": now,
        "status": "success",
        "draft_listing": draft_record,
    })
    save_json(DRAFT_RESULTS_FILE, results)

    # Remove only the successfully-created draft from the queue so it does not duplicate.
    save_json(PUBLISH_QUEUE_FILE, {"ready_to_publish": remaining})

    print("SUCCESS: Created exactly one complete Etsy draft listing via Make.com.")
    print(json.dumps(draft_record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
