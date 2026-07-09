"""
Stage 2 - Design Agent

Reads pending briefs from data/briefs.json and generates SVG designs
for each one via Claude (Claude can write clean, valid SVG markup
directly for simple geometric/typographic cut-file designs).

For more illustrative designs than Claude's native SVG output can
handle well, swap this stage to call Higgsfield's generate_image +
a raster-to-vector step instead — the brief structure stays the same,
only the generation call changes.
"""

import json
import os
import re
from datetime import datetime, timezone

from claude_client import call_claude

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BRIEFS_FILE = os.path.join(DATA_DIR, "briefs.json")
DESIGNS_DIR = os.path.join(DATA_DIR, "designs")
QUEUE_FILE = os.path.join(DATA_DIR, "qc_queue.json")


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def extract_svg(text: str) -> str:
    match = re.search(r"<svg.*?</svg>", text, re.DOTALL)
    if not match:
        raise ValueError("No <svg> block found in model output")
    return match.group(0)


def main():
    briefs = load_json(BRIEFS_FILE, {"pending": []})
    pending = [b for b in briefs["pending"] if b["status"] == "pending_design"]

    if not pending:
        print("No pending briefs to design.")
        return

    os.makedirs(DESIGNS_DIR, exist_ok=True)
    qc_queue = load_json(QUEUE_FILE, {"awaiting_review": []})

    for i, brief in enumerate(pending):
        bundle_size = brief.get("bundle_size", 3)
        design_files = []

        for variant in range(bundle_size):
            prompt = f"""Design a single clean, print/cut-ready SVG for this
Etsy cut-file product bundle:

Concept: {brief['product_concept']}
Target keyword: {brief['keyword']}
Variant: {variant + 1} of {bundle_size} (make each variant visually distinct)

Requirements:
- Pure black shapes on transparent background (standard for cut files)
- viewBox="0 0 800 800", clean closed paths (no strokes, no gradients)
- Simple enough to actually cut cleanly on a Cricut/Silhouette
- Return ONLY the raw <svg>...</svg> markup, nothing else
"""
            try:
                raw = call_claude(prompt, max_tokens=3000)
                svg = extract_svg(raw)
            except Exception as e:
                print(f"Failed variant {variant} for '{brief['keyword']}': {e}")
                continue

            filename = f"{brief['keyword'].replace(' ', '_')}_{variant + 1}.svg"
            filepath = os.path.join(DESIGNS_DIR, filename)
            with open(filepath, "w") as f:
                f.write(svg)
            design_files.append(filepath)

        brief["status"] = "pending_qc"
        brief["design_files"] = design_files
        qc_queue["awaiting_review"].append(brief)

    save_json(QUEUE_FILE, qc_queue)
    # Remove designed briefs from the pending list
    briefs["pending"] = [b for b in briefs["pending"] if b["status"] != "pending_qc" or b not in pending]
    save_json(BRIEFS_FILE, briefs)
    print(f"Designed {len(pending)} bundles, sent to QC queue.")


if __name__ == "__main__":
    main()
