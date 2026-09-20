"""Render (or re-render) the single-image posts in the queue, fetching a real photo first.

  python src/social/render_queue.py                 # render every queued single lacking images
  python src/social/render_queue.py --photos-only   # in CI: fetch photos for singles that have none, re-render those
  python src/social/render_queue.py --force         # re-render all singles
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import AGENT_DIR, REPO_DIR, load_config  # noqa: E402
from social.onepagers import render_onepager  # noqa: E402
from social.photos import PHOTO_DIR, _manifest, get_photo  # noqa: E402

QUEUE_DIR = AGENT_DIR / "social" / "queue"
IMG_DIR = REPO_DIR / "site" / "social"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos-only", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    site = load_config()["social"]["site_public_url"].rstrip("/")
    changed = 0
    for qf in sorted(QUEUE_DIR.glob("*.json")):
        data = json.loads(qf.read_text(encoding="utf-8"))
        dirty = False
        for p in data["posts"]:
            if p.get("kind") != "single" or p["status"] not in ("queued", "partial"):
                continue
            has_photo = bool(p.get("photo")) and (REPO_DIR / p["photo"]).exists()
            has_images = all((REPO_DIR / x).exists() for x in p.get("image_paths", []))
            if args.photos_only and has_photo:
                continue
            if not args.force and not args.photos_only and has_images and has_photo:
                continue
            photo = get_photo(p["photo_query"], p.get("photo_tags", []), p["photo_slug"])
            credit = None
            if photo:
                meta = _manifest().get(photo.name, {})
                credit = f"Photo: {meta['photographer']} / Pexels" if meta.get("photographer") else None
                p["photo"] = str(photo.relative_to(REPO_DIR))
            if args.photos_only and not photo:
                continue
            surfaces = ("feed", "story") if p.get("surface") == "feed" else ("story",)
            out = render_onepager(IMG_DIR, p["render_slug"], p["spec"], photo, credit, surfaces)
            key = "feed" if p.get("surface") == "feed" else "story"
            rel = str(out[key].relative_to(REPO_DIR))
            p["image_paths"] = [rel]
            p["image_urls"] = [f"{site}/social/{Path(rel).name}"]
            p["photo_credit"] = credit
            dirty = True
            changed += 1
        if dirty:
            qf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[render_queue] rendered {changed} single(s)")


if __name__ == "__main__":
    main()
