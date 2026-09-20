"""Render simple branded quote cards (1080×1080 PNG) for Instagram/Facebook.

Kept deliberately plain: solid brand background, big readable text, company name.
The point is a steady, credible presence, not design awards."""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
FONT_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _font(candidates, size):
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _hex(c: str):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def render_card(text: str, out_path: Path, brand: str = "Debt Direct Solutions", color: str = "#0b5fb0", kicker: str | None = None) -> Path:
    W = H = 1080
    img = Image.new("RGB", (W, H), _hex(color))
    d = ImageDraw.Draw(img)
    margin = 90

    # Fit the text: shrink font until wrapped block fits the safe area.
    size = 72
    while size > 34:
        font = _font(FONT_CANDIDATES, size)
        chars = max(14, int((W - 2 * margin) / (size * 0.55)))
        lines = textwrap.wrap(text, width=chars)
        line_h = int(size * 1.25)
        block_h = line_h * len(lines)
        if block_h <= H - 2 * margin - 160:
            break
        size -= 4
    y = (H - block_h) // 2 - 20
    for line in lines:
        d.text((margin, y), line, font=font, fill="white")
        y += line_h

    if kicker:
        kf = _font(FONT_REGULAR, 30)
        d.text((margin, margin), kicker.upper(), font=kf, fill=(255, 255, 255, 200))

    bf = _font(FONT_REGULAR, 34)
    d.rectangle([margin, H - margin - 60, margin + 80, H - margin - 56], fill="white")
    d.text((margin, H - margin - 40), brand, font=bf, fill="white")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path
