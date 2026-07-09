"""
Offline Etsy-Hermes end-to-end dry run.

This does not call Etsy, Make.com, Anthropic, or any external API.

It simulates the outputs of stages 1-5 with one safe sample SVG bundle,
then runs the stage 6 preparation path:

- creates a sample SVG design file
- creates a sample ready_to_publish queue item
- runs prepare_bundles.py logic
- generates a ZIP bundle
- generates a PNG preview
- builds the Make.com publish payload
- validates the payload using config/etsy_silo.json
- writes a dry-run report

The goal is to prove the cloud pipeline can safely prepare a complete
Etsy listing payload before any real Etsy/Make publishing is attempted.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Dict

# publish.py expects MAKE_WEBHOOK_URL to exist at import time. The dry run
# never posts to Make.com, so use a harmless placeholder to keep this
# workflow independent of secrets.
os.environ.setdefault("MAKE_WEBHOOK_URL", "https://example.com/etsy-hermes-dry-run")

import prepare_bundles
from publish import build_payload
from validate_publish_payload import validate_payload

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
DESIGNS_DIR = os.path.join(DATA_DIR, "designs")
BUNDLES_DIR = os.path.join(DATA_DIR, "bundles")
PREVIEWS_DIR = os.path.join(DATA_DIR, "previews")
REPORTS_DIR = os.path.join(DATA_DIR, "dry_run_reports")
PUBLISH_QUEUE_FILE = os.path.join(DATA_DIR, "publish_queue.json")
CONFIG_FILE = os.path.join(REPO_ROOT, "config", "etsy_silo.json")
DRY_RUN_REPORT_FILE = os.path.join(REPORTS_DIR, "latest_e2e_dry_run.json")

SAMPLE_KEYWORD = "floral monogram svg"
SAMPLE_SVG_FILE = os.path.join(DESIGNS_DIR, "dry_run_floral_monogram_1.svg")

SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800">
  <path d="M400 140 C450 210 520 250 600 250 C540 310 520 390 560 470 C480 450 420 500 400 580 C380 500 320 450 240 470 C280 390 260 310 200 250 C280 250 350 210 400 140 Z" fill="black"/>
  <circle cx="400" cy="360" r="85" fill="white"/>
  <path d="M345 445 L385 245 L425 245 L465 445 L425 445 L418 400 L392 400 L385 445 Z M397 365 L413 365 L405 310 Z" fill="black"/>
</svg>
"""


def load_json(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def clean_dry_run_outputs() -> None:
    os.makedirs(DESIGNS_DIR, exist_ok=True)
    os.makedirs(BUNDLES_DIR, exist_ok=True)
    os.makedirs(PREVIEWS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    for path in [
        SAMPLE_SVG_FILE,
        os.path.join(BUNDLES_DIR, "floral_monogram_svg_bundle.zip"),
        os.path.join(PREVIEWS_DIR, "floral_monogram_svg_preview.png"),
        DRY_RUN_REPORT_FILE,
    ]:
        if os.path.exists(path):
            os.remove(path)

    # The dry-run owns the publish queue during this workflow run.
    if os.path.exists(PUBLISH_QUEUE_FILE):
        backup_path = PUBLISH_QUEUE_FILE + ".dryrun_backup"
        shutil.copyfile(PUBLISH_QUEUE_FILE, backup_path)


def write_sample_ready_to_publish_item(config: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(DESIGNS_DIR, exist_ok=True)
    with open(SAMPLE_SVG_FILE, "w", encoding="utf-8") as f:
        f.write(SAMPLE_SVG)

    sample_brief = {
        "keyword": SAMPLE_KEYWORD,
        "product_concept": "A simple floral monogram SVG bundle for Cricut and Silhouette users.",
        "bundle_size": 1,
        "status": "ready_to_publish",
        "design_files": [SAMPLE_SVG_FILE],
        "taxonomy_id": config.get("taxonomy_id", 12394),
        "listing_copy": {
            "title": "Floral Monogram SVG Bundle for Cricut and Silhouette",
            "description": (
                "This is a digital download SVG cut-file bundle for personal craft projects. "
                "No physical product will be shipped. Files are intended for use with cutting "
                "machines and compatible design software."
            ),
            "tags": [
                "floral svg",
                "monogram svg",
                "cricut svg",
                "svg bundle",
                "cut file",
                "digital file",
                "flower svg",
            ],
        },
        "price": 4.99,
        "pricing_rationale": "Dry-run sample price inside the configured range.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    queue = {"ready_to_publish": [sample_brief]}
    save_json(PUBLISH_QUEUE_FILE, queue)
    return sample_brief


def main() -> int:
    config = load_json(CONFIG_FILE, {})
    clean_dry_run_outputs()
    write_sample_ready_to_publish_item(config)

    # Run the actual stage 6a bundle/preview preparation logic.
    prepare_bundles.main()

    queue_after_prepare = load_json(PUBLISH_QUEUE_FILE, {"ready_to_publish": []})
    ready = queue_after_prepare.get("ready_to_publish", [])
    if not ready:
        raise RuntimeError("Dry run failed: no ready_to_publish item after prepare_bundles.py")

    prepared_brief = ready[0]
    payload = build_payload(prepared_brief, config)
    is_valid, validation_errors = validate_payload(payload, config)

    bundle_path = os.path.join(REPO_ROOT, prepared_brief.get("bundle_repo_path", ""))
    preview_path = os.path.join(REPO_ROOT, prepared_brief.get("preview_repo_path", ""))

    checks = {
        "bundle_zip_exists": os.path.exists(bundle_path),
        "png_preview_exists": os.path.exists(preview_path),
        "payload_valid": is_valid,
        "state_is_draft": payload.get("state") == "draft",
        "auto_activate_disabled": config.get("auto_activate") is False,
        "taxonomy_matches_config": payload.get("taxonomy_id") == config.get("taxonomy_id"),
    }

    report = {
        "dry_run_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "keyword": SAMPLE_KEYWORD,
        "checks": checks,
        "validation_errors": validation_errors,
        "bundle_repo_path": prepared_brief.get("bundle_repo_path"),
        "preview_repo_path": prepared_brief.get("preview_repo_path"),
        "payload_preview": payload,
    }

    save_json(DRY_RUN_REPORT_FILE, report)
    print(json.dumps(report, indent=2))

    if not all(checks.values()):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
