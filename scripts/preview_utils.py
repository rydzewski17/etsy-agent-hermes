"""
Preview image utilities for Etsy listings.

Etsy listing images render more reliably as PNG/JPG than raw SVG. This
module converts the first SVG in a generated bundle into a square PNG
preview that Make.com can upload as the Etsy listing image.
"""

from __future__ import annotations

import os
from typing import Optional

import cairosvg

DEFAULT_PREVIEW_SIZE = 2000
DEFAULT_BACKGROUND = "white"


class PreviewGenerationError(Exception):
    """Raised when a preview image cannot be generated."""


def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def generate_png_preview(
    svg_path: str,
    output_png_path: str,
    size: int = DEFAULT_PREVIEW_SIZE,
    background_color: Optional[str] = DEFAULT_BACKGROUND,
) -> str:
    """
    Convert an SVG file into a square PNG preview image.

    Args:
        svg_path: Path to the source SVG file.
        output_png_path: Where to write the generated PNG.
        size: Width/height in pixels for Etsy-friendly preview quality.
        background_color: Optional background color. Defaults to white.

    Returns:
        The output PNG path.

    Raises:
        PreviewGenerationError: if the SVG is missing or conversion fails.
    """
    if not svg_path:
        raise PreviewGenerationError("Missing SVG path")

    if not os.path.exists(svg_path):
        raise PreviewGenerationError(f"SVG file does not exist: {svg_path}")

    if not svg_path.lower().endswith(".svg"):
        raise PreviewGenerationError(f"Preview source must be an SVG file: {svg_path}")

    ensure_directory(os.path.dirname(output_png_path))

    try:
        cairosvg.svg2png(
            url=svg_path,
            write_to=output_png_path,
            output_width=size,
            output_height=size,
            background_color=background_color,
        )
    except Exception as exc:
        raise PreviewGenerationError(
            f"Could not generate PNG preview for {svg_path}: {exc}"
        ) from exc

    if not os.path.exists(output_png_path):
        raise PreviewGenerationError(f"PNG preview was not created: {output_png_path}")

    return output_png_path
