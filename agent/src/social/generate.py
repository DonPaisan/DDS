"""Generate a week of Instagram/Facebook posts with Claude, render quote cards,
and queue them for publish.py.

  python src/social/generate.py                 # posts_per_week from config.yml
  python src/social/generate.py --count 5 --week 2026-09-22

Output:
  agent/social/queue/<week>.json      the posts (caption, hashtags, card text, scheduled day)
  site/social/<week>-<n>.jpg          the images (deployed by Netlify → public URL for the Graph API; JPEG is required by Instagram)

Nothing here posts anything. publish.py does that, and only when social.enabled is true.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import AGENT_DIR, REPO_DIR, load_config, load_env, today  # noqa: E402
from social.cards import render_card  # noqa: E402

PROMPT_PATH = REPO_DIR / "prompts" / "social-content.md"
QUEUE_DIR = AGENT_DIR / "social" / "queue"
IMG_DIR = REPO_DIR / "site" / "social"

SCHEMA = {
    "type": "object",
    "properties": {
        "posts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "description": "one of: myth-busting, practical tip, encouragement, how-it-works, faq"},
                    "card_text": {"type": "string", "description": "≤ 110 characters, the sentence on the image"},
                    "caption": {"type": "string", "description": "60–140 words, plain, warm, no hype, ends with a soft invitation"},
                    "hashtags": {"type": "array", "items": {"type": "string"}, "description": "5–8, lowercase, no #"},
                    "compliance_check": {"type": "string", "description": "one sentence confirming no guarantees, no percentages, no government implication"},
                },
                "required": ["theme", "card_text", "caption", "hashtags", "compliance_check"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["posts"],
    "additionalProperties": False,
}

# Claims that get a debt-relief post rejected. Percentages are allowed for education
# (APR, utilization, interest) but not next to a savings/settlement promise.
BANNED = re.compile(
    r"\b(guarantee[ds]?|eliminate|erase|wipe out|government program|irs|stimulus|debt[- ]free in)\b"
    r"|\b(save|saving|saved|reduce[sd]?|reduction|cut|lower(ed|ing)?|settle[sd]?|settling|forgive[ns]?|forgiven|pay(ing)? (only|just))\b[^.%\n]{0,40}\d{1,3}\s?%"
    r"|\d{1,3}\s?%[^.%\n]{0,15}\b(off|less|savings?|reduction|settlement)\b", re.I)


def recent_posts(n: int = 20) -> list[str]:
    out = []
    for f in sorted(QUEUE_DIR.glob("*.json"), reverse=True)[:4]:
        try:
            out += [p["card_text"] for p in json.loads(f.read_text())["posts"]]
        except Exception:
            pass
    return out[:n]


def generate(count: int, week: date) -> list[dict]:
    load_env()
    client = anthropic.Anthropic()
    brief = PROMPT_PATH.read_text(encoding="utf-8")
    avoid = recent_posts()
    user = (
        f"Write {count} posts for the week starting {week.isoformat()}. Vary the theme across posts.\n"
        + (f"Do not repeat these recent card texts:\n- " + "\n- ".join(avoid) if avoid else "")
    )
    resp = client.beta.messages.create(
        model="claude-opus-5",
        max_tokens=8000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=brief,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    if resp.stop_reason == "refusal":
        sys.exit(f"[social] model declined: {getattr(resp.stop_details, 'explanation', '')}")
    text = next(b.text for b in resp.content if b.type == "text")
    posts = json.loads(text)["posts"]

    # Hard compliance gate, independent of the model's own check.
    clean = []
    for p in posts:
        blob = p["card_text"] + " " + p["caption"]
        m = BANNED.search(blob)
        if m:
            print(f"[social] dropped a post for banned phrase '{m.group(0)}': {p['card_text'][:60]}", file=sys.stderr)
            continue
        clean.append(p)
    return clean


def queue(posts: list[dict], week: date, cfg: dict) -> Path:
    S = cfg["social"]
    days = [0, 2, 4, 1, 3, 5, 6][: len(posts)]  # Mon/Wed/Fri first, then fill
    out = {"week": week.isoformat(), "generated_at": today().isoformat(), "posts": []}
    for i, (p, d) in enumerate(zip(posts, sorted(days)), 1):
        slug = f"{week.isoformat()}-{i}"
        img = render_card(p["card_text"], IMG_DIR / f"{slug}.jpg", color=S["brand_color"], kicker=p["theme"])
        out["posts"].append({
            **p, "id": slug, "scheduled_for": (week + timedelta(days=d)).isoformat(),
            "image_path": str(img.relative_to(REPO_DIR)), "image_url": f"{S['site_public_url'].rstrip('/')}/social/{slug}.jpg",
            "status": "queued", "platforms": S["platforms"],
        })
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    path = QUEUE_DIR / f"{week.isoformat()}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=None)
    ap.add_argument("--week", type=str, default=None, help="Monday of the target week, YYYY-MM-DD")
    args = ap.parse_args(argv)
    cfg = load_config()
    count = args.count or cfg["social"]["posts_per_week"]
    if args.week:
        week = date.fromisoformat(args.week)
    else:
        t = today(); week = t + timedelta(days=(7 - t.weekday()) % 7 or 7)
    posts = generate(count, week)
    if not posts:
        sys.exit("[social] no posts survived the compliance gate")
    path = queue(posts, week, cfg)
    print(f"[social] queued {len(posts)} posts → {path}")
    print("[social] commit site/social/*.jpg so the images deploy, then publish.py can post them.")


if __name__ == "__main__":
    main()
