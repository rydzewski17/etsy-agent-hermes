"""
Stage 6a - Bundle Preparation

Zips each ready-to-publish bundle's SVG designs into a single digital
download file, saved under data/bundles/. This runs BEFORE the repo
commit step in the GitHub Actions workflow, so that by the time
publish.py runs, these files already have live raw.githubusercontent.com
URLs that Make.com's modules can fetch from.
"""

import json
import os
import zipfile

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PUBLISH_QUEUE_FILE = os.path.join(DATA_DIR, "publish_queue.json")
BUNDLES_DIR = os.path.join(DATA_DIR, "bundles")


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def slugify(keyword: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in keyword.lower()).strip("_")


def main():
    queue = load_json(PUBLISH_QUEUE_FILE, {"ready_to_publish": []})
    os.makedirs(BUNDLES_DIR, exist_ok=True)

    for brief in queue["ready_to_publish"]:
        slug = slugify(brief["keyword"])
        zip_name = f"{slug}_bundle.zip"
        zip_path = os.path.join(BUNDLES_DIR, zip_name)

        with zipfile.ZipFile(zip_path, "w") as zf:
            for filepath in brief.get("design_files", []):
                zf.write(filepath, arcname=os.path.basename(filepath))

        # Record repo-relative paths now, so publish.py can turn them
        # into raw.githubusercontent.com URLs after the commit+push step.
        brief["bundle_repo_path"] = f"data/bundles/{zip_name}"
        if brief.get("design_files"):
            first_design = brief["design_files"][0]
            brief["preview_repo_path"] = os.path.relpath(
                first_design, os.path.join(os.path.dirname(__file__), "..")
            )

    save_json(PUBLISH_QUEUE_FILE, queue)
    print(f"Prepared {len(queue['ready_to_publish'])} bundles for publishing.")


if __name__ == "__main__":
    main()
