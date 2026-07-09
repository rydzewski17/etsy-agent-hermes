"""
Stage 6a - Bundle Preparation

Zips each ready-to-publish bundle's SVG designs into a single digital
download file, saved under data/bundles/. Also converts the first SVG
in the bundle into an Etsy-friendly PNG preview image under data/previews/.

This runs BEFORE the repo commit step in the GitHub Actions workflow,
so that by the time publish.py runs, both the ZIP bundle and PNG preview
already have live raw.githubusercontent.com URLs that Make.com's modules
can fetch from.
"""

import json
import os
import zipfile

from preview_utils import PreviewGenerationError, generate_png_preview

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PUBLISH_QUEUE_FILE = os.path.join(DATA_DIR, "publish_queue.json")
BUNDLES_DIR = os.path.join(DATA_DIR, "bundles")
PREVIEWS_DIR = os.path.join(DATA_DIR, "previews")


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
    os.makedirs(PREVIEWS_DIR, exist_ok=True)

    prepared_count = 0
    preview_count = 0

    for brief in queue["ready_to_publish"]:
        slug = slugify(brief["keyword"])
        zip_name = f"{slug}_bundle.zip"
        zip_path = os.path.join(BUNDLES_DIR, zip_name)

        design_files = brief.get("design_files", [])
        with zipfile.ZipFile(zip_path, "w") as zf:
            for filepath in design_files:
                zf.write(filepath, arcname=os.path.basename(filepath))

        # Record repo-relative paths now, so publish.py can turn them
        # into raw.githubusercontent.com URLs after the commit+push step.
        brief["bundle_repo_path"] = f"data/bundles/{zip_name}"
        prepared_count += 1

        if design_files:
            first_design = design_files[0]
            preview_name = f"{slug}_preview.png"
            preview_path = os.path.join(PREVIEWS_DIR, preview_name)

            try:
                generate_png_preview(first_design, preview_path)
                brief["preview_repo_path"] = f"data/previews/{preview_name}"
                preview_count += 1
            except PreviewGenerationError as exc:
                # Leave preview_repo_path unset so the publish validator
                # blocks this listing instead of sending a bad payload.
                brief.pop("preview_repo_path", None)
                print(f"WARNING: preview generation failed for '{brief['keyword']}': {exc}")

    save_json(PUBLISH_QUEUE_FILE, queue)
    print(f"Prepared {prepared_count} bundles for publishing.")
    print(f"Generated {preview_count} PNG preview images.")


if __name__ == "__main__":
    main()
