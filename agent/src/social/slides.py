"""Branded 4:5 carousel slides in the Debt Direct Solutions palette (from the logo).

Slide kinds: cover, text, stat, compare (two bars), list, cta. Every slide carries the
logo and a progress strip. Copy limits are enforced by the caller (≤ 30 words per slide).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
FONT_DIR = ROOT / "agent" / "assets" / "fonts"
LOGO_PATH = ROOT / "site" / "brand" / "logo.png"
LOGO_LIGHT_PATH = ROOT / "site" / "brand" / "logo-light.png"

W, H = 1080, 1350
M = 84  # margin

# Palette sampled from the logo
NAVY = (0x18, 0x28, 0x38)
YELLOW = (0xF8, 0xD8, 0x58)
BLUE = (0x30, 0x98, 0xF0)
BLUE_DEEP = (0x08, 0x70, 0xD0)
BLUE_LIGHT = (0x88, 0xC8, 0xF8)
PEACH = (0xF8, 0xD0, 0xA8)
WHITE = (255, 255, 255)
CREAM = (0xFF, 0xFC, 0xF4)
INK = NAVY
MUTED = (0x4A, 0x56, 0x68)
LINE = (0xE3, 0xE8, 0xEF)


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    names = {"bold": "Poppins-Bold", "semibold": "Poppins-SemiBold", "medium": "Poppins-Medium", "regular": "Poppins-Regular", "bolditalic": "Poppins-BoldItalic"}
    p = FONT_DIR / f"{names[weight]}.ttf"
    if p.exists():
        return ImageFont.truetype(str(p), size)
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if weight in ("bold", "semibold") else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)


def wrap(d: ImageDraw.ImageDraw, text: str, f, max_w: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(d, text, weight, start, min_size, max_w, max_lines):
    size = start
    while size > min_size:
        f = font(weight, size)
        lines = wrap(d, text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines, size
        size -= 4
    f = font(weight, min_size)
    return f, wrap(d, text, f, max_w), min_size


_logo_cache: dict = {}


def logo(height: int, light: bool = False) -> Image.Image:
    key = (height, light)
    if key not in _logo_cache:
        im = Image.open(LOGO_LIGHT_PATH if light and LOGO_LIGHT_PATH.exists() else LOGO_PATH).convert("RGBA")
        bbox = im.getbbox()
        im = im.crop(bbox)
        r = height / im.height
        _logo_cache[key] = im.resize((int(im.width * r), height), Image.LANCZOS)
    return _logo_cache[key]


def paste_logo(img: Image.Image, x: int, y: int, height: int, card: bool = False):
    lg = logo(height)
    img.paste(lg, (x, y), lg)
    return lg.width, lg.height


BAND = 200  # white footer band on dark slides


def progress(d: ImageDraw.ImageDraw, index: int, total: int, dark: bool, y: int | None = None):
    """Segmented progress strip, bottom-right."""
    seg_w, gap, h = 34, 8, 8
    total_w = total * seg_w + (total - 1) * gap
    x = W - M - total_w
    y = (H - M - 30) if y is None else y
    for i in range(total):
        on = i < index
        col = NAVY if on else LINE
        d.rounded_rectangle([x, y, x + seg_w, y + h], radius=4, fill=col)
        x += seg_w + gap


def footer(img: Image.Image, d: ImageDraw.ImageDraw, index: int, total: int, dark: bool):
    """Original logo on white: on dark slides that means a white band across the bottom."""
    if dark:
        d.rectangle([0, H - BAND, W, H], fill=WHITE)
        paste_logo(img, M, H - BAND + (BAND - 130) // 2, 130)
        progress(d, index, total, dark=False, y=H - BAND // 2 - 4)
    else:
        paste_logo(img, M, H - M - 130, 130)
        progress(d, index, total, dark=False)


def draw_rich(d, x, y, words_lines, f, color, highlight_words, hl_color):
    """Draw wrapped lines word by word so highlighted words get a second color."""
    hl = {w.lower().strip(".,!?:;") for w in highlight_words}
    for line in words_lines:
        cx = x
        for w in line.split(" "):
            col = hl_color if w.lower().strip(".,!?:;“”\"'()") in hl else color
            d.text((cx, y), w, font=f, fill=col)
            cx += d.textlength(w + " ", font=f)
        y += int(f.size * 1.18)
    return y


# ── slide kinds ──────────────────────────────────────────────────────────────
def cover(path: Path, *, title: str, kicker: str, subtitle: str | None, highlight: list[str], index: int, total: int):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    # soft blue glow top-right
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W - 520, -380, W + 260, 400], fill=(*BLUE_DEEP, 110))
    img.paste(Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"))
    d = ImageDraw.Draw(img)

    kf = font("semibold", 30)
    d.rounded_rectangle([M, M + 10, M + d.textlength(kicker.upper(), font=kf) + 44, M + 66], radius=28, fill=YELLOW)
    d.text((M + 22, M + 20), kicker.upper(), font=kf, fill=NAVY)

    f, lines, size = fit(d, title, "bold", 92, 60, W - 2 * M, 5)
    y = M + 150
    y = draw_rich(d, M, y, lines, f, WHITE, highlight, YELLOW)
    if subtitle:
        sf, slines, _ = fit(d, subtitle, "medium", 38, 30, W - 2 * M, 3)
        y += 26
        for ln in slines:
            d.text((M, y), ln, font=sf, fill=BLUE_LIGHT)
            y += int(sf.size * 1.35)

    # swipe cue: yellow arrow bleeding off the right edge
    ay = H - BAND - 110
    d.text((W - M - 250, ay - 6), "swipe", font=font("semibold", 34), fill=YELLOW)
    d.line([(W - M - 120, ay + 14), (W + 10, ay + 14)], fill=YELLOW, width=10)
    d.polygon([(W - 60, ay - 26), (W + 10, ay + 14), (W - 60, ay + 54)], fill=YELLOW)

    footer(img, d, index, total, dark=True)
    img.save(path, "JPEG", quality=92, optimize=True)


def _light_base(kicker: str, index: int):
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    nf = font("bold", 34)
    d.text((M, M), f"{index:02d}", font=nf, fill=BLUE)
    d.text((M + 70, M + 4), kicker.upper(), font=font("semibold", 26), fill=MUTED)
    return img, d


CONTENT_TOP, CONTENT_BOTTOM = M + 110, H - M - 190


def _center_y(block_h: int) -> int:
    return max(CONTENT_TOP, CONTENT_TOP + (CONTENT_BOTTOM - CONTENT_TOP - block_h) // 2)


def text_slide(path: Path, *, heading: str, body: str, kicker: str, index: int, total: int):
    img, d = _light_base(kicker, index)
    hf, hl, _ = fit(d, heading, "bold", 66, 44, W - 2 * M - 40, 4)
    bf, bl, _ = fit(d, body, "regular", 42, 32, W - 2 * M, 9)
    y = _center_y(len(hl) * int(hf.size * 1.18) + 36 + len(bl) * int(bf.size * 1.42))
    d.rounded_rectangle([M, y + 8, M + 12, y + len(hl) * int(hf.size * 1.18) - 8], radius=6, fill=YELLOW)
    for ln in hl:
        d.text((M + 40, y), ln, font=hf, fill=INK)
        y += int(hf.size * 1.18)
    y += 36
    for ln in bl:
        d.text((M, y), ln, font=bf, fill=MUTED)
        y += int(bf.size * 1.42)
    footer(img, d, index, total, dark=False)
    img.save(path, "JPEG", quality=92, optimize=True)


def stat_slide(path: Path, *, heading: str, value: str, label: str, body: str | None, kicker: str, index: int, total: int):
    img, d = _light_base(kicker, index)
    hf, hl, _ = fit(d, heading, "bold", 60, 42, W - 2 * M, 3)
    tile_h = 330
    bf, bl = (fit(d, body, "regular", 40, 32, W - 2 * M, 5)[:2] if body else (None, []))
    y = _center_y(len(hl) * int(hf.size * 1.18) + 40 + tile_h + (44 + len(bl) * int(bf.size * 1.42) if bl else 0))
    for ln in hl:
        d.text((M, y), ln, font=hf, fill=INK)
        y += int(hf.size * 1.18)
    y += 40
    d.rounded_rectangle([M, y, W - M, y + tile_h], radius=34, fill=YELLOW)
    vf, vl, _ = fit(d, value, "bold", 150, 80, W - 2 * M - 80, 1)
    vw = d.textlength(vl[0], font=vf)
    d.text(((W - vw) // 2, y + 50), vl[0], font=vf, fill=NAVY)
    lf = font("medium", 36)
    ll = wrap(d, label, lf, W - 2 * M - 80)
    ly = y + tile_h - 60 - (len(ll) - 1) * 44
    for ln in ll:
        lw = d.textlength(ln, font=lf)
        d.text(((W - lw) // 2, ly), ln, font=lf, fill=NAVY)
        ly += 44
    y += tile_h + 44
    if bl:
        for ln in bl:
            d.text((M, y), ln, font=bf, fill=MUTED)
            y += int(bf.size * 1.42)
    footer(img, d, index, total, dark=False)
    img.save(path, "JPEG", quality=92, optimize=True)


def compare_slide(path: Path, *, heading: str, bars: list[dict], note: str | None, kicker: str, index: int, total: int):
    """Two or three horizontal bars of one measure. bars: [{label, value, display, emphasis}]."""
    img, d = _light_base(kicker, index)
    hf, hl, _ = fit(d, heading, "bold", 60, 42, W - 2 * M, 3)
    BAR_H, ROW = 64, 64 + 56 + 40
    nf, nl = (fit(d, note, "regular", 38, 30, W - 2 * M, 5)[:2] if note else (None, []))
    y = _center_y(len(hl) * int(hf.size * 1.18) + 48 + len(bars) * ROW + (10 + len(nl) * int(nf.size * 1.42) if nl else 0))
    for ln in hl:
        d.text((M, y), ln, font=hf, fill=INK)
        y += int(hf.size * 1.18)
    y += 48
    vmax = max(b["value"] for b in bars) or 1
    track_w = W - 2 * M - 160   # leave room for a label past the longest bar
    lf, vf = font("semibold", 36), font("bold", 40)
    for b in bars:
        d.text((M, y), b["label"], font=lf, fill=INK)
        y += 56
        bw = max(40, int(track_w * b["value"] / vmax))
        col = BLUE_DEEP if b.get("emphasis") else BLUE_LIGHT
        d.rounded_rectangle([M, y, M + bw, y + BAR_H], radius=8, fill=col)
        d.rectangle([M, y, M + 10, y + BAR_H], fill=col)  # square at the baseline
        disp = b["display"]
        tw = d.textlength(disp, font=vf)
        if tw + 48 <= bw:
            d.text((M + bw - tw - 24, y + 8), disp, font=vf, fill=WHITE if b.get("emphasis") else INK)
        else:
            d.text((M + bw + 20, y + 8), disp, font=vf, fill=INK)
        y += BAR_H + 40
    if nl:
        y += 10
        for ln in nl:
            d.text((M, y), ln, font=nf, fill=MUTED)
            y += int(nf.size * 1.42)
    footer(img, d, index, total, dark=False)
    img.save(path, "JPEG", quality=92, optimize=True)


def list_slide(path: Path, *, heading: str, items: list[str], kicker: str, index: int, total: int, numbered: bool = False):
    img, d = _light_base(kicker, index)
    hf, hl, _ = fit(d, heading, "bold", 60, 42, W - 2 * M, 3)
    itf = font("medium", 40)
    est = sum(max(len(wrap(d, it, itf, W - 2 * M - 80)) * int(itf.size * 1.32), 60) + 26 for it in items)
    y = _center_y(len(hl) * int(hf.size * 1.18) + 40 + est)
    for ln in hl:
        d.text((M, y), ln, font=hf, fill=INK)
        y += int(hf.size * 1.18)
    y += 40
    for i, item in enumerate(items, 1):
        d.ellipse([M, y + 2, M + 52, y + 54], fill=YELLOW)
        if numbered:
            nf = font("bold", 28)
            tw = d.textlength(str(i), font=nf)
            d.text((M + 26 - tw / 2, y + 10), str(i), font=nf, fill=NAVY)
        else:
            d.line([(M + 14, y + 29), (M + 23, y + 39), (M + 40, y + 17)], fill=NAVY, width=6, joint="curve")
        lines = wrap(d, item, itf, W - 2 * M - 80)
        ty = y
        for ln in lines:
            d.text((M + 78, ty), ln, font=itf, fill=INK)
            ty += int(itf.size * 1.32)
        y = max(ty, y + 60) + 26
    footer(img, d, index, total, dark=False)
    img.save(path, "JPEG", quality=92, optimize=True)


def cta_slide(path: Path, *, index: int, total: int, line1: str = "Save this for later.", line2: str = "Send it to someone who could use it.", pill: str = "Free, no-judgment review. Link in bio."):
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    # navy top band with a soft glow, original logo on white below it
    d.rectangle([0, 0, W, 220], fill=NAVY)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W - 520, -380, W + 260, 400], fill=(*BLUE_DEEP, 110))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 220, W, H], fill=WHITE)
    lg = logo(380)
    img.paste(lg, ((W - lg.width) // 2, 220 + 50), lg)
    y = 220 + 50 + lg.height + 60
    f1, l1, _ = fit(d, line1, "bold", 84, 56, W - 2 * M, 2)
    for ln in l1:
        d.text((M, y), ln, font=f1, fill=NAVY)
        y += int(f1.size * 1.18)
    y += 16
    f2, l2, _ = fit(d, line2, "medium", 42, 30, W - 2 * M, 3)
    for ln in l2:
        d.text((M, y), ln, font=f2, fill=MUTED)
        y += int(f2.size * 1.35)
    y += 56
    pf = font("semibold", 36)
    pw = d.textlength(pill, font=pf) + 64
    d.rounded_rectangle([M, y, M + pw, y + 82], radius=41, fill=YELLOW)
    d.text((M + 32, y + 20), pill, font=pf, fill=NAVY)
    progress(d, index, total, dark=False)
    img.save(path, "JPEG", quality=92, optimize=True)


def render_carousel(out_dir: Path, slug: str, spec: dict) -> list[Path]:
    """spec: {kicker, cover:{title, highlight, subtitle}, slides:[{kind, ...}]}; CTA appended automatically."""
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = spec["slides"]
    total = len(slides) + 2
    paths = []
    c = spec["cover"]
    p = out_dir / f"{slug}-01.jpg"
    cover(p, title=c["title"], kicker=spec["kicker"], subtitle=c.get("subtitle"), highlight=c.get("highlight", []), index=1, total=total)
    paths.append(p)
    for i, s in enumerate(slides, start=2):
        p = out_dir / f"{slug}-{i:02d}.jpg"
        k = s["kind"]
        common = dict(kicker=spec["kicker"], index=i, total=total)
        if k == "text":
            text_slide(p, heading=s["heading"], body=s["body"], **common)
        elif k == "stat":
            stat_slide(p, heading=s["heading"], value=s["value"], label=s["label"], body=s.get("body"), **common)
        elif k == "compare":
            compare_slide(p, heading=s["heading"], bars=s["bars"], note=s.get("note"), **common)
        elif k == "list":
            list_slide(p, heading=s["heading"], items=s["items"], numbered=s.get("numbered", False), **common)
        else:
            raise ValueError(k)
        paths.append(p)
    p = out_dir / f"{slug}-{total:02d}.jpg"
    cta_slide(p, index=total, total=total)
    paths.append(p)
    return paths
