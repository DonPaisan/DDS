"""HTML/CSS slide renderer (Chromium via Playwright). Same entry points as slides.py /
onepagers.py so the queue builders and render_queue.py can switch with one import.

Design system v2 "Ledger" (html/theme.css, docs/social-design-research.md): editorial serif
headlines, quiet sans body, navy base with the logo's yellow used as a gold accent, paper
grain, hairline rules, a thin frame, and only true trust cues (site, free review, no obligation).

Themes: navy (default), paper, slate, white, photo. Old names still work: cream → paper,
sky → slate. Slide kinds: cover, text, stat, compare, list, vs (myth vs fact), cta.
One-pagers: did_you_know, story, quote.
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
SITE = "debtdirectsolutions.com"
SIZES = {"feed": (1080, 1350), "story": (1080, 1920)}
THEME_ALIASES = {"cream": "paper", "sky": "slate"}
DARK = {"navy", "slate", "photo"}

_css = (HERE / "theme.css").read_text(encoding="utf-8").replace("__FONTS__", FONTS.as_uri())


def esc(s: str) -> str:
    return html.escape(str(s), quote=False)


def theme_name(t: str | None) -> str:
    return THEME_ALIASES.get(t or "navy", t or "navy")


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


def progress(i: int, total: int) -> str:
    return '<div class="progress">' + "".join(f'<i class="{"on" if k < i else ""}"></i>' for k in range(total)) + "</div>"


def band(i: int | None, total: int | None, credit: str | None = None) -> str:
    right = f'<span class="follow">Follow <b>{HANDLE}</b></span><span class="site">{SITE}</span>'
    if credit:
        right += f'<span class="credit">{esc(credit)}</span>'
    if i and total:
        right += progress(i, total)
    return f'<footer class="band"><img class="logo" src="{LOGO.as_uri()}"><div class="right">{right}</div></footer>'


def top(kicker: str, i: int | None = None, total: int | None = None) -> str:
    idx = f'<span class="idx">{i:02d} / {total:02d}</span>' if i and total else ""
    return f'<header class="top"><span class="kicker">{esc(kicker)}</span>{idx}</header>'


def page(theme: str, body: str, *, surface: str = "feed", photo: Path | None = None, extra_class: str = "") -> str:
    theme = theme_name(theme)
    surface = "story" if surface in ("story", "reel") else surface
    bg = '<div class="bg"><div class="glow g1"></div><div class="glow g2"></div><div class="grain"></div></div>'
    if theme == "photo" and photo:
        bg = f'<div class="bg"><div class="photo" style="background-image:url({Path(photo).resolve().as_uri()})"></div><div class="tint"></div><div class="shade"></div><div class="grain"></div></div>'
    elif theme == "photo":
        theme = "navy"
    dark = " dark" if theme in DARK else ""
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{_css}</style></head><body class="t-{theme} {surface} {extra_class}{dark}">{bg}<div class="frame"></div>{body}</body></html>'


SWIPE = '<div class="swipe">swipe <svg viewBox="0 0 120 40" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h104"/><path d="M92 8l16 12-16 12"/></svg></div>'


def _cls(surface: str) -> str:
    return "reel" if surface == "reel" else ""


# ── carousel slides ──────────────────────────────────────────────────────────
def slide_cover(spec, i, total, theme, photo=None, surface="feed"):
    c = spec["cover"]
    h = rich(c["title"], c.get("highlight"))
    sub = f'<p class="sub">{esc(c["subtitle"])}</p>' if c.get("subtitle") else ""
    serial = f'<div class="serial">{esc(spec.get("serial", f"{total - 2} ideas, {total} slides"))}</div>'
    body = f'{top(spec["kicker"])}<main class="content"><h1 class="{size_class(c["title"], 60, 85)}">{h}</h1>{sub}</main>{serial}{SWIPE}{band(i, total)}'
    return page(theme, body, photo=photo, surface=surface, extra_class=_cls(surface))


def slide_text(s, i, total, theme, kicker, surface="feed"):
    ic = f'<div class="icon-tile">{icon(s["icon"])}</div>' if s.get("icon") else ""
    body = f'{top(kicker, i, total)}<main class="content">{ic}<h2 class="{size_class(s["heading"], 40)}">{rich(s["heading"], s.get("highlight"))}</h2><p class="body">{esc(s["body"])}</p></main>{band(i, total)}'
    return page(theme, body, surface=surface, extra_class=_cls(surface))


def slide_stat(s, i, total, theme, kicker, surface="feed"):
    num_cls = "long" if len(s["value"]) > 7 else ""
    b = f'<p class="body">{esc(s["body"])}</p>' if s.get("body") else ""
    body = f'{top(kicker, i, total)}<main class="content"><h2 class="{size_class(s["heading"], 40)}">{esc(s["heading"])}</h2><div class="stat"><div class="num {num_cls}">{esc(s["value"])}</div><div class="lbl">{esc(s["label"])}</div></div>{b}</main>{band(i, total)}'
    return page(theme, body, surface=surface, extra_class=_cls(surface))


def slide_compare(s, i, total, theme, kicker, surface="feed"):
    vmax = max(b["value"] for b in s["bars"]) or 1
    bars = ""
    for b in s["bars"]:
        pct = max(9, round(100 * b["value"] / vmax))
        outside = pct < 34
        fill = f'<div class="fill {"outside" if outside else ""}" style="width:{pct}%">{"<span>" + esc(b["display"]) + "</span>" if outside else esc(b["display"])}</div>'
        bars += f'<div class="bar {"emph" if b.get("emphasis") else ""}"><div class="lbl">{esc(b["label"])}</div><div class="track">{fill}</div></div>'
    note = f'<p class="note">{esc(s["note"])}</p>' if s.get("note") else ""
    body = f'{top(kicker, i, total)}<main class="content"><h2 class="{size_class(s["heading"], 40)}">{esc(s["heading"])}</h2><div class="bars">{bars}</div>{note}</main>{band(i, total)}'
    return page(theme, body, surface=surface, extra_class=_cls(surface))


def slide_list(s, i, total, theme, kicker, surface="feed"):
    items = ""
    for n, it in enumerate(s["items"], 1):
        bullet = f"{n:02d}" if s.get("numbered") else icon("check")
        items += f'<div class="item"><div class="bullet">{bullet}</div><div>{esc(it)}</div></div>'
    body = f'{top(kicker, i, total)}<main class="content"><h2 class="{size_class(s["heading"], 40)}">{esc(s["heading"])}</h2><div class="list">{items}</div></main>{band(i, total)}'
    return page(theme, body, surface=surface, extra_class=_cls(surface))


def slide_vs(s, i, total, theme, kicker, surface="feed"):
    note = f'<p class="note" style="margin-top:34px">{esc(s["note"])}</p>' if s.get("note") else ""
    body = (f'{top(kicker, i, total)}<main class="content"><h2 class="{size_class(s["heading"], 40)}">{esc(s["heading"])}</h2>'
            f'<div class="vs"><div class="col myth"><div class="tag">{esc(s.get("left_tag", "Myth"))}</div><div class="txt">{esc(s["left"])}</div></div>'
            f'<div class="col fact"><div class="tag">{esc(s.get("right_tag", "Fact"))}</div><div class="txt">{esc(s["right"])}</div></div></div>{note}</main>{band(i, total)}')
    return page(theme, body, surface=surface, extra_class=_cls(surface))


TRUST = ["Free review", "No obligation", SITE]


def slide_cta(i, total, surface="feed"):
    trust = "".join(f"<span>{esc(t)}</span>" for t in TRUST)
    body = (f'<div class="head"><div class="glow"></div><div class="line"></div></div><main class="content cta"><img class="logo" src="{LOGO.as_uri()}">'
            f'<h1>Save this for later.</h1><p class="sub">Send it to someone who could use it.</p>'
            f'<span class="follow">Follow <b>{HANDLE}</b><small>Plain-English money basics, every day. Link in bio for a free, no-judgment money review.</small></span>'
            f'<div class="trust">{trust}</div></main>'
            f'<footer class="band" style="background:transparent;box-shadow:none;justify-content:flex-end">{progress(i, total)}</footer>')
    return page("paper", body, surface=surface, extra_class=_cls(surface))


def render_carousel(out_dir: Path, slug: str, spec: dict, photo: Path | None = None, surface: str = "feed") -> list[Path]:
    """surface: feed (1080×1350) or reel (1080×1920, no swipe cue / progress) for video frames."""
    theme = theme_name(spec.get("theme", "navy"))
    slides = spec["slides"]
    total = len(slides) + 2
    pages = [(f"{slug}-01", slide_cover(spec, 1, total, spec.get("cover_theme", theme), photo, surface))]
    body_theme = spec.get("body_theme", "white" if theme in DARK else theme)
    for k, s in enumerate(slides, start=2):
        fn = {"text": slide_text, "stat": slide_stat, "compare": slide_compare, "list": slide_list, "vs": slide_vs}[s["kind"]]
        pages.append((f"{slug}-{k:02d}", fn(s, k, total, s.get("theme", body_theme), spec["kicker"], surface)))
    pages.append((f"{slug}-{total:02d}", slide_cta(total, total, surface)))
    return _render(out_dir, pages, "story" if surface == "reel" else "feed")


# ── one-pagers ───────────────────────────────────────────────────────────────
def one_dyk(spec, theme, surface, photo, credit):
    body = f'{top("Did you know?")}<main class="content dyk"><div class="icon-tile">{icon(spec.get("icon", "bulb"))}</div><p class="fact {size_class(spec["fact"], 80)}">{rich(spec["fact"], spec.get("highlight"))}</p><p class="so">{esc(spec["so_what"])}</p></main>{band(None, None, credit)}'
    return page(theme, body, surface=surface, photo=photo)


def one_story(spec, theme, surface, photo, credit):
    body = f'{top(spec.get("kicker", "True story"))}<main class="content story"><h1 class="{size_class(spec["headline"], 55, 75)}">{esc(spec["headline"])}</h1><p class="body" style="margin-top:32px;font-size:35px">{esc(spec["summary"])}</p><div class="source">{esc(spec["source"])}</div></main>{band(None, None, credit)}'
    return page(theme, body, surface=surface, photo=photo)


def one_quote(spec, theme, surface, photo, credit):
    body = f'<main class="content quote"><div class="mark">“</div><blockquote>{esc(spec["text"])}</blockquote><div class="attr">{esc(spec["attribution"])}</div></main>{band(None, None, credit)}'
    return page(theme, body, surface=surface, photo=photo)


def render_onepager(out_dir: Path, slug: str, spec: dict, photo: Path | None, credit: str | None, surfaces=("feed",)) -> dict[str, Path]:
    theme = theme_name(spec.get("theme", "photo" if photo else "navy"))
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
