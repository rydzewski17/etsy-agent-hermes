"""
Stage 3 - QC / Curation Agent

Sanity-checks generated SVGs before anything gets a listing created:
  - valid, parseable SVG
  - not suspiciously empty or malformed
  - not near-duplicate of an already-published design (basic hash check)

This is intentionally conservative: automation should catch broken
files, not make final creative judgment calls. Flags anything
ambiguous into a "needs_human_review" bucket rather than guessing.
"""

import hashlib
import json
import os
import xml.etree.ElementTree as ET

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
QUEUE_FILE = os.path.join(DATA_DIR, "qc_queue.json")
APPROVED_FILE = os.path.join(DATA_DIR, "approved.json")
PUBLISHED_HASHES_FILE = os.path.join(DATA_DIR, "published_hashes.json")


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def is_valid_svg(filepath) -> bool:
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        return "svg" in root.tag.lower()
    except ET.ParseError:
        return False


def file_hash(filepath) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    queue = load_json(QUEUE_FILE, {"awaiting_review": []})
    published_hashes = set(load_json(PUBLISHED_HASHES_FILE, {"hashes": []})["hashes"])
    approved = load_json(APPROVED_FILE, {"ready_for_listing": [], "needs_human_review": []})

    for brief in queue["awaiting_review"]:
        valid_files = []
        flagged = False

        for filepath in brief.get("design_files", []):
            if not os.path.exists(filepath):
                flagged = True
                continue
            if not is_valid_svg(filepath):
                flagged = True
                continue
            h = file_hash(filepath)
            if h in published_hashes:
                flagged = True  # exact duplicate of something already live
                continue
            valid_files.append(filepath)

        if not valid_files:
            flagged = True

        brief["design_files"] = valid_files
        if flagged:
            brief["status"] = "needs_human_review"
            approved["needs_human_review"].append(brief)
        else:
            brief["status"] = "ready_for_listing"
            approved["ready_for_listing"].append(brief)

    save_json(APPROVED_FILE, approved)
    save_json(QUEUE_FILE, {"awaiting_review": []})
    print(f"QC complete: {len(approved['ready_for_listing'])} ready, "
          f"{len(approved['needs_human_review'])} flagged for human review.")


if __name__ == "__main__":
    main()
