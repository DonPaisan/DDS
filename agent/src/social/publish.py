"""Publish queued posts to Instagram and the Facebook Page via the Graph API.

  python src/social/publish.py            # dry run: shows what is due today
  python src/social/publish.py --really   # posts anything due today (requires social.enabled: true)

Instagram needs a PUBLIC JPEG URL, which is why generate.py writes JPEGs into
site/social/ — Netlify deploys them. Make sure that deploy has happened.

Token: a Page access token from a user who admins the Page, with
pages_manage_posts, pages_read_engagement, instagram_basic, and
instagram_content_publish. IG_USER_ID is the Instagram professional account
linked to the Page: GET /{page-id}?fields=instagram_business_account.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import AGENT_DIR, env, load_config, load_env, log_action, today  # noqa: E402

QUEUE_DIR = AGENT_DIR / "social" / "queue"


def graph(method: str, path: str, **params) -> dict:
    version = env("META_API_VERSION", "v26.0")
    r = requests.request(method, f"https://graph.facebook.com/{version}/{path}", params=params, timeout=60)
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"Graph API error: {body['error']}")
    return body


def resolve_ids(token: str) -> tuple[str, str | None]:
    """Page id and Instagram professional account id, from env or looked up via the token."""
    page = env("FB_PAGE_ID")
    if not page:
        pages = graph("GET", "me/accounts", fields="id,name,instagram_business_account", access_token=token).get("data", [])
        if not pages:
            sys.exit("[publish] the token can see no Pages; assign the Page to the system user in Business Settings")
        if len(pages) > 1:
            names = ", ".join(f"{x['name']} ({x['id']})" for x in pages)
            sys.exit(f"[publish] token can see several Pages, set FB_PAGE_ID: {names}")
        page = pages[0]["id"]
        ig = (pages[0].get("instagram_business_account") or {}).get("id")
        print(f"[publish] using Page {pages[0]['name']} ({page})" + (f", Instagram {ig}" if ig else ", no Instagram account linked"))
        return page, env("IG_USER_ID") or ig
    ig = env("IG_USER_ID")
    if not ig:
        ig = (graph("GET", page, fields="instagram_business_account", access_token=token).get("instagram_business_account") or {}).get("id")
    return page, ig


def caption_text(p: dict) -> str:
    tags = " ".join("#" + t.strip("#") for t in p.get("hashtags", []))
    return f"{p['caption']}\n\n{tags}".strip()


def post_instagram(p: dict, token: str, ig: str) -> dict:
    """Container model: create → poll status_code until FINISHED → publish."""
    creation = graph("POST", f"{ig}/media", image_url=p["image_url"], caption=caption_text(p), access_token=token)
    for _ in range(20):
        st = graph("GET", creation["id"], fields="status_code,status", access_token=token)
        code = st.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container {creation['id']} {code}: {st.get('status')}")
        time.sleep(3)
    else:
        raise RuntimeError(f"Instagram container {creation['id']} not ready after 60s")
    return graph("POST", f"{ig}/media_publish", creation_id=creation["id"], access_token=token)


def post_facebook(p: dict, token: str, page: str) -> dict:
    return graph("POST", f"{page}/photos", url=p["image_url"], message=caption_text(p), access_token=token)


def due_posts(t: str | None = None):
    t = t or today().isoformat()
    for f in sorted(QUEUE_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for p in data["posts"]:
            if p["status"] == "queued" and p["scheduled_for"] <= t:
                yield f, data, p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--really", action="store_true", help="actually post")
    ap.add_argument("--date", default=None, help="treat this YYYY-MM-DD as today (default: today UTC)")
    args = ap.parse_args(argv)
    load_env()
    cfg = load_config()["social"]
    live = args.really and cfg["enabled"]
    if args.really and not cfg["enabled"]:
        print("[publish] social.enabled is false in config.yml — dry run only.")
    token = (env("FB_PAGE_TOKEN") or env("META_TOKEN")) if live else None
    if live and not token:
        sys.exit("[publish] FB_PAGE_TOKEN or META_TOKEN not set")
    page, ig = resolve_ids(token) if live else (None, None)

    n = 0
    for f, data, p in due_posts(args.date):
        n += 1
        if not live:
            print(f"[publish:DRY-RUN] {p['scheduled_for']} {p['id']} → {', '.join(p['platforms'])}: {p['card_text']}")
            continue
        # Check the image is really public before Meta tries to fetch it.
        head = requests.head(p["image_url"], timeout=20)
        if head.status_code != 200:
            print(f"[publish] {p['id']}: image not public yet ({head.status_code}) — deploy site/social first", file=sys.stderr)
            continue
        results = {}
        for platform in p["platforms"]:
            if platform == "instagram" and not ig:
                results[platform] = {"error": "no Instagram professional account linked to the Page"}
                print(f"[publish] {p['id']}: skipping Instagram, no IG account linked to the Page", file=sys.stderr)
                continue
            try:
                results[platform] = post_instagram(p, token, ig) if platform == "instagram" else post_facebook(p, token, page)
            except Exception as e:  # noqa: BLE001
                results[platform] = {"error": str(e)}
                print(f"[publish] {p['id']} {platform} failed: {e}", file=sys.stderr)
        p["status"] = "posted" if all("error" not in r for r in results.values()) else "partial"
        p["results"] = results
        f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        log_action({"mode": "APPLY", "action": "social_post", "post_id": p["id"], "results": results})
        print(f"[publish] {p['id']} → {p['status']}")
    if not n:
        print("[publish] nothing due today.")


if __name__ == "__main__":
    main()
