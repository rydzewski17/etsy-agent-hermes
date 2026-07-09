"""
Validate Etsy publish payloads before sending them to Make.com.

This script is intentionally conservative. It is designed to stop Hermes
from sending incomplete, unsafe, or accidentally-live Etsy listings.

Usage examples:

  python scripts/validate_publish_payload.py --payload data/sample_payload.json
  python scripts/validate_publish_payload.py --payload data/sample_payload.json --config config/etsy_silo.json

Exit codes:
  0 = payload is valid
  1 = payload is invalid
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_CONFIG_PATH = os.path.join(REPO_ROOT, "config", "etsy_silo.json")

MAX_TITLE_LENGTH = 140
MAX_TAGS = 13
MAX_TAG_LENGTH = 20
MIN_DESCRIPTION_LENGTH = 80

BLOCKED_TERMS = {
    "disney",
    "mickey",
    "minnie",
    "taylor swift",
    "swiftie",
    "nfl",
    "nba",
    "mlb",
    "nhl",
    "barbie",
    "stanley cup",
    "cincinnati bengals",
    "ohio state",
    "harry potter",
    "pokemon",
    "marvel",
    "star wars",
}

DIGITAL_DOWNLOAD_PHRASES = (
    "digital download",
    "digital file",
    "instant download",
    "no physical item",
    "no physical product",
)


class PayloadValidationError(Exception):
    """Raised when an Etsy publish payload fails validation."""


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def contains_blocked_term(text: str, blocked_terms: set[str]) -> str | None:
    lowered = text.lower()
    for term in sorted(blocked_terms, key=len, reverse=True):
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        if re.search(pattern, lowered):
            return term
    return None


def validate_payload(payload: Dict[str, Any], config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    required_fields = config.get("required_listing_assets") or [
        "digital_file_url",
        "preview_image_url",
        "title",
        "description",
        "tags",
        "price",
        "taxonomy_id",
    ]

    for field in required_fields:
        value = payload.get(field)
        if value is None or value == "" or value == []:
            errors.append(f"Missing required field: {field}")

    title = normalize_text(payload.get("title"))
    if not title:
        errors.append("Title is required")
    elif len(title) > MAX_TITLE_LENGTH:
        errors.append(f"Title is too long: {len(title)} characters; max is {MAX_TITLE_LENGTH}")

    description = normalize_text(payload.get("description"))
    if len(description) < MIN_DESCRIPTION_LENGTH:
        errors.append(
            f"Description is too short: {len(description)} characters; minimum is {MIN_DESCRIPTION_LENGTH}"
        )
    elif not any(phrase in description.lower() for phrase in DIGITAL_DOWNLOAD_PHRASES):
        errors.append(
            "Description must clearly say this is a digital download / digital file / instant download / no physical product"
        )

    tags = payload.get("tags")
    if not isinstance(tags, list):
        errors.append("Tags must be a list")
    else:
        if len(tags) > MAX_TAGS:
            errors.append(f"Too many tags: {len(tags)}; Etsy allows max {MAX_TAGS}")
        seen_tags = set()
        for tag in tags:
            tag_text = normalize_text(tag)
            if not tag_text:
                errors.append("Tags cannot include blanks")
                continue
            if len(tag_text) > MAX_TAG_LENGTH:
                errors.append(f"Tag is too long: '{tag_text}' is {len(tag_text)} characters; max is {MAX_TAG_LENGTH}")
            if tag_text.lower() in seen_tags:
                errors.append(f"Duplicate tag: {tag_text}")
            seen_tags.add(tag_text.lower())

    price = payload.get("price")
    min_price = float(config.get("minimum_price", 1.99))
    max_price = float(config.get("maximum_price", 9.99))
    try:
        numeric_price = float(price)
        if numeric_price < min_price or numeric_price > max_price:
            errors.append(f"Price {numeric_price} is outside configured range {min_price}-{max_price}")
    except (TypeError, ValueError):
        errors.append("Price must be numeric")

    expected_taxonomy_id = config.get("taxonomy_id")
    actual_taxonomy_id = payload.get("taxonomy_id")
    if expected_taxonomy_id and actual_taxonomy_id != expected_taxonomy_id:
        errors.append(
            f"taxonomy_id must be {expected_taxonomy_id}; got {actual_taxonomy_id}"
        )

    if not is_url(payload.get("digital_file_url")):
        errors.append("digital_file_url must be a valid http(s) URL")

    if not is_url(payload.get("preview_image_url")):
        errors.append("preview_image_url must be a valid http(s) URL")

    quantity = payload.get("quantity")
    if quantity is not None:
        try:
            if int(quantity) <= 0:
                errors.append("Quantity must be greater than 0")
        except (TypeError, ValueError):
            errors.append("Quantity must be an integer")

    state = normalize_text(payload.get("state") or "draft").lower()
    auto_activate = bool(config.get("auto_activate", False))
    activate_allowed = bool(config.get("publish_rules", {}).get("activate_listings_allowed", False))

    if state == "active" and not (auto_activate and activate_allowed):
        errors.append(
            "Payload is trying to activate a listing, but auto activation is disabled in config"
        )
    elif state not in {"draft", "active"}:
        errors.append("state must be either 'draft' or 'active'")

    combined_text = " ".join(
        [title, description] + [normalize_text(tag) for tag in tags if isinstance(tags, list)]
    )
    config_blocked_terms = set(
        str(term).lower() for term in config.get("blocked_terms_policy", {}).get("examples", [])
    )
    blocked_terms = BLOCKED_TERMS.union(config_blocked_terms)
    blocked_term = contains_blocked_term(combined_text, blocked_terms)
    if blocked_term:
        errors.append(f"Blocked/protected term detected: {blocked_term}")

    return len(errors) == 0, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an Etsy publish payload.")
    parser.add_argument("--payload", required=True, help="Path to a JSON payload file")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to etsy_silo.json")
    args = parser.parse_args()

    payload = load_json(args.payload)
    config = load_json(args.config)

    is_valid, errors = validate_payload(payload, config)

    if is_valid:
        print("VALID: Etsy publish payload passed all checks.")
        return 0

    print("INVALID: Etsy publish payload failed validation:")
    for error in errors:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
