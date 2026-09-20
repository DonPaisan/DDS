"""Single-image posts (feed 4:5 and Stories 9:16) on a real photo with the brand overlay.

Kinds:
  did_you_know  — one surprising, true, checkable fact + a one-line "so what"
  story         — a real, sourced story: headline, 2–3 line summary, source line
  quote         — our own words or an attributed quote, big and quiet

If no photo is available the slide falls back to the navy brand background, so a
missing Pexels key never blocks a post.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from social.slides import BAND, BLUE, BLUE_LIGHT, HANDLE, LOGO_PATH, M, MUTED, NAVY, WHITE, YELLOW, fit, font, logo, paste_logo, template, wrap  # noqa: F401

SIZES = {"feed": (1080, 1350), "story": (1080, 1920)}


def _background(size: tuple[int, int], photo: Path | None, darken: float = 0.62) -> Image.Image:
    W, H = size
    if photo and Path(photo).exists():
        im = Image.open(photo).convert("RGB")
        # cover-crop to the target aspect
        r = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
        left, top = (im.width - W) // 2, (im.height - H) // 3   # bias toward the upper part (faces)
        im = im.crop((left, top, left + W, top + H))
        # navy tint + bottom-heavy gradient so text stays readable
        tint = Image.new("RGB", (W, H), NAVY)
        im = Image.blend(im, tint, 0.28)
        grad = Image.new("L", (1, H))
        for y in range(H):
            t = y / H
            grad.putpixel((0, y), int(255 * min(1.0, 0.15 + darken * (t ** 1.4))))
        grad = grad.resize((W, H))
        shade = Image.new("RGB", (W, H), NAVY)
        im = Image.composite(shade, im, grad)
        return im
    tpl = template("story" if H > 1400 else "onepager", (W, H))
    if tpl is not None:
        return tpl
    im = Image.new("RGB", (W, H), NAVY)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W - 560, -420, W + 300, 440], fill=(0x08, 0x70, 0xD0, 110))
    return Image.alpha_composite(im.convert("RGBA"), glow).convert("RGB")


def _brand(img: Image.Image, d: ImageDraw.ImageDraw, surface: str, credit: str | None):
    W, H = img.size
    band = BAND if surface == "feed" else 260   # Stories: keep the band clear of the reply bar
    d.rectangle([0, H - band, W, H], fill=WHITE)
    paste_logo(img, M, H - band + (band - 130) // 2 - (30 if surface == "story" else 0), 130)
    # follow line on the right of the band
    ff_ = font("bold", 30)
    fy = H - band // 2 - 34 - (30 if surface == "story" else 0)
    fw = d.textlength("Follow " + HANDLE, font=ff_)
    d.text((W - M - fw, fy), "Follow ", font=ff_, fill=NAVY)
    d.text((W - M - fw + d.textlength("Follow ", font=ff_), fy), HANDLE, font=ff_, fill=BLUE)
    if credit:
        cf = font("regular", 22)
        tw = d.textlength(credit, font=cf)
        d.text((W - M - tw, fy + 44), credit, font=cf, fill=MUTED)


def _pill(d, x, y, text, fill=YELLOW, ink=NAVY, size=30):
    f = font("semibold", size)
    w = d.textlength(text, font=f) + 44
    d.rounded_rectangle([x, y, x + w, y + size + 26], radius=(size + 26) // 2, fill=fill)
    d.text((x + 22, y + 11), text, font=f, fill=ink)
    return w


def did_you_know(path: Path, *, fact: str, so_what: str, photo: Path | None, surface: str = "feed", credit: str | None = None, highlight: list[str] | None = None):
    W, H = SIZES[surface]
    img = _background((W, H), photo)
    d = ImageDraw.Draw(img)
    top = M + (120 if surface == "story" else 0)
    _pill(d, M, top, "DID YOU KNOW?")
    ff, fl, _ = fit(d, fact, "bold", 84 if surface == "feed" else 92, 52, W - 2 * M, 6)
    lh = int(ff.size * 1.15)
    sf, sl, _ = fit(d, so_what, "medium", 38, 30, W - 2 * M, 4)
    block = len(fl) * lh + 34 + len(sl) * int(sf.size * 1.4)
    y = max(top + 110, (H - BAND - block) // 2)
    hl = {w.lower().strip(".,!?") for w in (highlight or [])}
    for ln in fl:
        cx = M
        for w in ln.split(" "):
            col = YELLOW if w.lower().strip(".,!?%$") in hl else WHITE
            d.text((cx, y), w, font=ff, fill=col)
            cx += d.textlength(w + " ", font=ff)
        y += lh
    y += 34
    for ln in sl:
        d.text((M, y), ln, font=sf, fill=BLUE_LIGHT)
        y += int(sf.size * 1.4)
    _brand(img, d, surface, credit)
    img.save(path, "JPEG", quality=92, optimize=True)


def story(path: Path, *, kicker: str, headline: str, summary: str, source: str, photo: Path | None, surface: str = "feed", credit: str | None = None):
    W, H = SIZES[surface]
    img = _background((W, H), photo, darken=0.72)
    d = ImageDraw.Draw(img)
    top = M + (120 if surface == "story" else 0)
    _pill(d, M, top, kicker.upper())
    hf, hl, _ = fit(d, headline, "bold", 76 if surface == "feed" else 84, 48, W - 2 * M, 5)
    lh = int(hf.size * 1.15)
    bf, bl, _ = fit(d, summary, "regular", 36, 28, W - 2 * M, 7)
    blh = int(bf.size * 1.42)
    src_f = font("medium", 26)
    block = len(hl) * lh + 30 + len(bl) * blh + 40 + 40
    y = max(top + 110, H - BAND - 60 - block)   # anchor just above the white band
    for ln in hl:
        d.text((M, y), ln, font=hf, fill=WHITE)
        y += lh
    y += 30
    for ln in bl:
        d.text((M, y), ln, font=bf, fill=(232, 238, 246))
        y += blh
    y += 24
    d.rounded_rectangle([M, y + 6, M + 10, y + 34], radius=4, fill=YELLOW)
    d.text((M + 26, y), source, font=src_f, fill=BLUE_LIGHT)
    _brand(img, d, surface, credit)
    img.save(path, "JPEG", quality=92, optimize=True)


def quote(path: Path, *, text: str, attribution: str, photo: Path | None, surface: str = "feed", credit: str | None = None):
    W, H = SIZES[surface]
    img = _background((W, H), photo, darken=0.7)
    d = ImageDraw.Draw(img)
    qf = font("bold", 220)
    d.text((M - 10, (H // 2) - 360 if surface == "feed" else (H // 2) - 420), "“", font=qf, fill=YELLOW)
    tf, tl, _ = fit(d, text, "semibold", 68 if surface == "feed" else 76, 44, W - 2 * M, 7)
    lh = int(tf.size * 1.25)
    af = font("medium", 34)
    block = len(tl) * lh + 40 + 44
    y = (H - BAND - block) // 2
    for ln in tl:
        d.text((M, y), ln, font=tf, fill=WHITE)
        y += lh
    y += 40
    d.rounded_rectangle([M, y + 12, M + 70, y + 18], radius=3, fill=YELLOW)
    d.text((M + 90, y), attribution, font=af, fill=BLUE_LIGHT)
    _brand(img, d, surface, credit)
    img.save(path, "JPEG", quality=92, optimize=True)


def render_onepager(out_dir: Path, slug: str, spec: dict, photo: Path | None, credit: str | None, surfaces=("feed",)) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for s in surfaces:
        p = out_dir / f"{slug}{'' if s == 'feed' else '-story'}.jpg"
        k = spec["kind"]
        if k == "did_you_know":
            did_you_know(p, fact=spec["fact"], so_what=spec["so_what"], photo=photo, surface=s, credit=credit, highlight=spec.get("highlight"))
        elif k == "story":
            story(p, kicker=spec.get("kicker", "True story"), headline=spec["headline"], summary=spec["summary"], source=spec["source"], photo=photo, surface=s, credit=credit)
        elif k == "quote":
            quote(p, text=spec["text"], attribution=spec["attribution"], photo=photo, surface=s, credit=credit)
        else:
            raise ValueError(k)
        out[s] = p
    return out
