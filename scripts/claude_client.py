"""
Thin wrapper around the Anthropic Messages API for the pipeline's
text-generation steps (keyword briefs, listing copy, pricing rationale).
"""

import json
import os
import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"


def call_claude(prompt: str, system: str = None, max_tokens: int = 2000) -> str:
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return "".join(
        block["text"] for block in data["content"] if block["type"] == "text"
    )


def call_claude_json(prompt: str, system: str = None, max_tokens: int = 2000) -> dict:
    """Same as call_claude but strips code fences and parses JSON output.
    Always instruct the prompt to return ONLY raw JSON, no markdown."""
    raw = call_claude(prompt, system=system, max_tokens=max_tokens)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())
