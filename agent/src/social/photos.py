"""Real photos for one-pager posts.

Order of preference:
  1. Your own photos in site/social/photos/own/ (drop JPGs there; the filename is the tag,
     e.g. kitchen-table-bills.jpg). Real beats stock for trust every time.
  2. Pexels stock (free license, commercial use allowed, no attribution required; we store
     it anyway). Needs PEXELS_API_KEY. Runs in the GitHub workflow, which has open egress.

Never AI-generated imagery: Meta detects it via embedded metadata and cuts reach on
undisclosed AI content, and it undercuts the trust these posts exist to build.

  python src/social/photos.py "older woman reading letter at kitchen table" --out slug
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import REPO_DIR, env, load_env  # noqa: E402

PHOTO_DIR = REPO_DIR / "site" / "social" / "photos"
OWN_DIR = PHOTO_DIR / "own"
MANIFEST = PHOTO_DIR / "manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def _save_manifest(m: dict) -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False))


def find_own(tags: list[str]) -> Path | None:
    """First own photo whose filename contains any tag word."""
    if not OWN_DIR.exists():
        return None
    for f in sorted(OWN_DIR.glob("*.jp*g")):
        name = f.stem.lower()
        if any(t.lower() in name for t in tags):
            return f
    return None


def fetch_pexels(query: str, slug: str, *, orientation: str = "portrait", avoid_ids: set | None = None) -> Path | None:
    load_env()
    key = env("PEXELS_API_KEY")
    if not key:
        print("[photos] PEXELS_API_KEY not set; skipping stock fetch", file=sys.stderr)
        return None
    r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": key},
                     params={"query": query, "orientation": orientation, "size": "large", "per_page": 15}, timeout=30)
    if r.status_code != 200:
        print(f"[photos] pexels {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return None
    photos = r.json().get("photos", [])
    avoid = avoid_ids or set()
    for p in photos:
        if str(p["id"]) in avoid:
            continue
        src = p["src"].get("large2x") or p["src"].get("large") or p["src"]["original"]
        img = requests.get(src, timeout=60)
        if img.status_code != 200:
            continue
        PHOTO_DIR.mkdir(parents=True, exist_ok=True)
        out = PHOTO_DIR / f"{slug}.jpg"
        out.write_bytes(img.content)
        m = _manifest()
        m[out.name] = {"source": "pexels", "id": p["id"], "url": p.get("url"), "photographer": p.get("photographer"),
                       "photographer_url": p.get("photographer_url"), "alt": p.get("alt"), "query": query, "avg_color": p.get("avg_color")}
        _save_manifest(m)
        return out
    return None


def get_photo(query: str, tags: list[str], slug: str) -> Path | None:
    """Own photo if one matches, else cached stock, else fetch stock."""
    own = find_own(tags)
    if own:
        return own
    cached = PHOTO_DIR / f"{slug}.jpg"
    if cached.exists():
        return cached
    used = {str(v.get("id")) for v in _manifest().values() if v.get("source") == "pexels"}
    return fetch_pexels(query, slug, avoid_ids=used)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--out", required=True, help="slug for the saved file")
    ap.add_argument("--tags", default="")
    args = ap.parse_args(argv)
    p = get_photo(args.query, [t for t in args.tags.split(",") if t], args.out)
    print(p or "[photos] no photo found")


if __name__ == "__main__":
    main()
