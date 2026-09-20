"""Render simple branded quote cards (1080×1080 JPEG) for Instagram/Facebook.

JPEG, not PNG: the Instagram publishing API rejects PNG. sRGB, 1:1, well under 8 MB.

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
    img.save(out_path, "JPEG", quality=92, optimize=True)
    return out_path


# ── carousel slides ──────────────────────────────────────────────────────────
def _wrap_to_width(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_slide(out_path: Path, *, heading: str, body: str | None = None, kicker: str | None = None,
                 index: int | None = None, total: int | None = None, brand: str = "Debt Direct Solutions",
                 color: str = "#0b5fb0", cover: bool = False, footer: str | None = None) -> Path:
    """One 1080×1350 (4:5) carousel slide. Cover slides get a big heading; content
    slides get a heading plus body copy. Same brand block on every slide."""
    W, H = 1080, 1350
    bg = _hex(color) if cover else (255, 255, 255)
    fg = "white" if cover else _hex("#16202e")
    muted = (225, 235, 250) if cover else _hex("#55627a")
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    m = 90
    y = m

    kf = _font(FONT_REGULAR, 30)
    if kicker:
        d.text((m, y), kicker.upper(), font=kf, fill=muted)
    if index and total:
        s = f"{index} / {total}"
        d.text((W - m - d.textlength(s, font=kf), y), s, font=kf, fill=muted)
    y += 90

    size = 88 if cover else 60
    while size > 36:
        hf = _font(FONT_CANDIDATES, size)
        lines = _wrap_to_width(d, heading, hf, W - 2 * m)
        if len(lines) <= (5 if cover else 4):
            break
        size -= 4
    line_h = int(size * 1.2)

    blines, bf, bline_h = [], None, 0
    if body:
        bsize = 40
        while bsize > 28:
            bf = _font(FONT_REGULAR, bsize)
            blines = []
            for para in body.split("\n"):
                blines += _wrap_to_width(d, para, bf, W - 2 * m) if para.strip() else [""]
            bline_h = int(bsize * 1.45)
            if len(lines) * line_h + 30 + len(blines) * bline_h <= H - 2 * m - 220:
                break
            bsize -= 2

    block_h = len(lines) * line_h + (30 + len(blines) * bline_h if blines else 0)
    top, bottom = y, H - m - 110
    y = max(top, top + (bottom - top - block_h) // 2 - 40)
    for ln in lines:
        d.text((m, y), ln, font=hf, fill=fg)
        y += line_h
    if blines:
        y += 30
        for ln in blines:
            d.text((m, y), ln, font=bf, fill=fg if not cover else "white")
            y += bline_h

    ff = _font(FONT_REGULAR, 32)
    d.rectangle([m, H - m - 62, m + 80, H - m - 58], fill=fg if not cover else "white")
    d.text((m, H - m - 40), footer or brand, font=ff, fill=fg if not cover else "white")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path
