"""HTML/CSS slide renderer (Chromium via Playwright). Same entry points as slides.py /
onepagers.py so the queue builders and render_queue.py can switch with one import.

Themes: navy (default), cream, sky, white, photo. Each carousel picks a theme so the
feed varies while staying on brand. Slide kinds: cover, text, stat, compare, list,
vs (myth vs fact), cta. One-pagers: did_you_know, story, quote.
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent / "html"
FONTS = ROOT / "agent" / "assets" / "fonts"
ICONS = ROOT / "agent" / "assets" / "icons"
LOGO = ROOT / "site" / "brand" / "logo.png"
HANDLE = "@debt_direct_solutions"
SIZES = {"feed": (1080, 1350), "story": (1080, 1920)}

_css = (HERE / "theme.css").read_text(encoding="utf-8").replace("__FONTS__", FONTS.as_uri())


def esc(s: str) -> str:
    return html.escape(str(s), quote=False)


def rich(text: str, highlight: list[str] | None) -> str:
    """Escape, then wrap highlighted words in <mark>."""
    out = esc(text)
    for w in sorted(set(highlight or []), key=len, reverse=True):
        out = re.sub(rf"(?<![\w-])({re.escape(esc(w))})(?![\w-])", r"<mark>\1</mark>", out)
    return out


def icon(name: str) -> str:
    p = ICONS / f"{name}.svg"
    if not p.exists():
        p = ICONS / "circle-check.svg"
    svg = p.read_text(encoding="utf-8")
    return svg[svg.index("<svg"):]


def size_class(text: str, long_at: int, xlong_at: int | None = None) -> str:
    n = len(text)
    if xlong_at and n > xlong_at:
        return "xlong"
    return "long" if n > long_at else ""


def dots(i: int, total: int) -> str:
    return '<div class="dots">' + "".join(f'<i class="{"on" if k < i else ""}"></i>' for k in range(total)) + "</div>"


def band(i: int | None, total: int | None, credit: str | None = None) -> str:
    right = f'<span class="follow">Follow <b>{HANDLE}</b></span>'
    if credit:
        right += f'<span class="credit">{esc(credit)}</span>'
    if i and total:
        right += dots(i, total)
    return f'<footer class="band"><img class="logo" src="{LOGO.as_uri()}"><div class="right">{right}</div></footer>'


def page(theme: str, body: str, *, surface: str = "feed", photo: Path | None = None, extra_class: str = "") -> str:
    bg = '<div class="bg"><div class="blob b1"></div><div class="blob b2"></div><div class="grid"></div></div>'
    if theme == "photo" and photo:
        bg = f'<div class="bg"><div class="photo" style="background-image:url({Path(photo).resolve().as_uri()})"></div><div class="tint"></div><div class="shade"></div></div>'
    elif theme == "photo":
        theme = "navy"
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{_css}</style></head><body class="t-{theme} {surface} {extra_class}">{bg}{body}</body></html>'


SWIPE = '<div class="swipe">swipe <svg viewBox="0 0 190 70" fill="none" stroke="currentColor" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 35h150"/><path d="M130 12l28 23-28 23"/></svg></div>'


# ── carousel slides ──────────────────────────────────────────────────────────
def slide_cover(spec, i, total, theme, photo=None):
    c = spec["cover"]
    h = rich(c["title"], c.get("highlight"))
    sub = f'<p class="sub">{esc(c["subtitle"])}</p>' if c.get("subtitle") else ""
    body = f'<header class="top"><span class="kicker">{esc(spec["kicker"])}</span></header><main class="content"><h1 class="{size_class(c["title"], 60, 85)}">{h}</h1>{sub}</main>{SWIPE}{band(i, total)}'
    return page(theme, body, photo=photo)


def slide_text(s, i, total, theme, kicker):
    ic = f'<div class="icon-tile">{icon(s["icon"])}</div>' if s.get("icon") else ""
    body = f'<header class="top"><span class="kicker">{esc(kicker)}</span><span class="idx">{i:02d} / {total:02d}</span></header><main class="content">{ic}<h2 class="{size_class(s["heading"], 40)}">{rich(s["heading"], s.get("highlight"))}</h2><p class="body">{esc(s["body"])}</p></main>{band(i, total)}'
    return page(theme, body)


def slide_stat(s, i, total, theme, kicker):
    num_cls = "long" if len(s["value"]) > 7 else ""
    b = f'<p class="body">{esc(s["body"])}</p>' if s.get("body") else ""
    body = f'<header class="top"><span class="kicker">{esc(kicker)}</span><span class="idx">{i:02d} / {total:02d}</span></header><main class="content"><h2 class="{size_class(s["heading"], 40)}">{esc(s["heading"])}</h2><div class="stat"><div class="num {num_cls}">{esc(s["value"])}</div><div class="lbl">{esc(s["label"])}</div></div>{b}</main>{band(i, total)}'
    return page(theme, body)


def slide_compare(s, i, total, theme, kicker):
    vmax = max(b["value"] for b in s["bars"]) or 1
    bars = ""
    for b in s["bars"]:
        pct = max(9, round(100 * b["value"] / vmax))
        outside = pct < 34
        fill = f'<div class="fill {"outside" if outside else ""}" style="width:{pct}%">{"<span>" + esc(b["display"]) + "</span>" if outside else esc(b["display"])}</div>'
        bars += f'<div class="bar {"emph" if b.get("emphasis") else ""}"><div class="lbl">{esc(b["label"])}</div><div class="track">{fill}</div></div>'
    note = f'<p class="note">{esc(s["note"])}</p>' if s.get("note") else ""
    body = f'<header class="top"><span class="kicker">{esc(kicker)}</span><span class="idx">{i:02d} / {total:02d}</span></header><main class="content"><h2 class="{size_class(s["heading"], 40)}">{esc(s["heading"])}</h2><div class="bars">{bars}</div>{note}</main>{band(i, total)}'
    return page(theme, body)


def slide_list(s, i, total, theme, kicker):
    items = ""
    for n, it in enumerate(s["items"], 1):
        bullet = str(n) if s.get("numbered") else icon("check")
        items += f'<div class="item"><div class="bullet">{bullet}</div><div>{esc(it)}</div></div>'
    body = f'<header class="top"><span class="kicker">{esc(kicker)}</span><span class="idx">{i:02d} / {total:02d}</span></header><main class="content"><h2 class="{size_class(s["heading"], 40)}">{esc(s["heading"])}</h2><div class="list">{items}</div></main>{band(i, total)}'
    return page(theme, body)


def slide_vs(s, i, total, theme, kicker):
    body = f'<header class="top"><span class="kicker">{esc(kicker)}</span><span class="idx">{i:02d} / {total:02d}</span></header><main class="content"><h2 class="{size_class(s["heading"], 40)}">{esc(s["heading"])}</h2><div class="vs"><div class="col myth"><div class="tag">{esc(s.get("left_tag", "Myth"))}</div><div class="txt">{esc(s["left"])}</div></div><div class="col fact"><div class="tag">{esc(s.get("right_tag", "Fact"))}</div><div class="txt">{esc(s["right"])}</div></div></div>' + (f'<p class="note" style="margin-top:34px">{esc(s["note"])}</p>' if s.get("note") else "") + f'</main>{band(i, total)}'
    return page(theme, body)


def slide_cta(i, total):
    body = f'<div class="head"><div class="blob"></div></div><main class="content cta"><img class="logo" src="{LOGO.as_uri()}"><h1>Save this for later.</h1><p class="sub">Send it to someone who could use it.</p><span class="pill">Free, no-judgment money review. Link in bio.</span><span class="follow">Follow <b>{HANDLE}</b><small>Plain-English money basics, every day.</small></span></main><footer class="band" style="background:transparent;box-shadow:none;justify-content:flex-end">{dots(i, total)}</footer>'
    return page("white", body)


def render_carousel(out_dir: Path, slug: str, spec: dict, photo: Path | None = None) -> list[Path]:
    theme = spec.get("theme", "navy")
    slides = spec["slides"]
    total = len(slides) + 2
    pages = [(f"{slug}-01", slide_cover(spec, 1, total, spec.get("cover_theme", theme), photo))]
    body_theme = spec.get("body_theme", "white" if theme in ("navy", "photo", "sky") else theme)
    for k, s in enumerate(slides, start=2):
        fn = {"text": slide_text, "stat": slide_stat, "compare": slide_compare, "list": slide_list, "vs": slide_vs}[s["kind"]]
        pages.append((f"{slug}-{k:02d}", fn(s, k, total, s.get("theme", body_theme), spec["kicker"])))
    pages.append((f"{slug}-{total:02d}", slide_cta(total, total)))
    return _render(out_dir, pages, "feed")


# ── one-pagers ───────────────────────────────────────────────────────────────
def one_dyk(spec, theme, surface, photo, credit):
    body = f'<header class="top"><span class="kicker">Did you know?</span></header><main class="content dyk"><div class="icon-tile">{icon(spec.get("icon", "bulb"))}</div><p class="fact {size_class(spec["fact"], 80)}">{rich(spec["fact"], spec.get("highlight"))}</p><p class="so">{esc(spec["so_what"])}</p></main>{band(None, None, credit)}'
    return page(theme, body, surface=surface, photo=photo)


def one_story(spec, theme, surface, photo, credit):
    body = f'<header class="top"><span class="kicker">{esc(spec.get("kicker", "True story"))}</span></header><main class="content story"><h1 class="{size_class(spec["headline"], 55, 75)}">{esc(spec["headline"])}</h1><p class="body" style="margin-top:30px;font-size:36px">{esc(spec["summary"])}</p><div class="source">{esc(spec["source"])}</div></main>{band(None, None, credit)}'
    return page(theme, body, surface=surface, photo=photo)


def one_quote(spec, theme, surface, photo, credit):
    body = f'<main class="content quote"><div class="mark">“</div><blockquote>{esc(spec["text"])}</blockquote><div class="attr">{esc(spec["attribution"])}</div></main>{band(None, None, credit)}'
    return page(theme, body, surface=surface, photo=photo)


def render_onepager(out_dir: Path, slug: str, spec: dict, photo: Path | None, credit: str | None, surfaces=("feed",)) -> dict[str, Path]:
    theme = spec.get("theme", "photo" if photo else "navy")
    fn = {"did_you_know": one_dyk, "story": one_story, "quote": one_quote}[spec["kind"]]
    out = {}
    for s in surfaces:
        name = f"{slug}{'' if s == 'feed' else '-story'}"
        paths = _render(out_dir, [(name, fn(spec, theme, s, photo, credit))], s)
        out[s] = paths[0]
    return out


# ── chromium ─────────────────────────────────────────────────────────────────
def _render(out_dir: Path, pages: list[tuple[str, str]], surface: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    w, h = SIZES[surface]
    tmp = Path(tempfile.mkdtemp(prefix="dds-slides-"))
    jobs, outs = [], []
    for name, html_str in pages:
        hp = tmp / f"{name}.html"
        hp.write_text(html_str, encoding="utf-8")
        op = out_dir / f"{name}.jpg"
        jobs.append({"html": str(hp), "out": str(op), "width": w, "height": h})
        outs.append(op)
    jf = tmp / "jobs.json"
    jf.write_text(json.dumps(jobs))
    env = {**os.environ, "NODE_PATH": os.environ.get("NODE_PATH", "") + ":/opt/node22/lib/node_modules:" + str(ROOT / "node_modules")}
    r = subprocess.run(["node", str(HERE / "render.mjs"), str(jf)], capture_output=True, text=True, env=env, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"render failed: {r.stderr[-2000:]}")
    return outs
