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
from datetime import datetime, timezone
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


def resolve_ids(token: str) -> tuple[str, str | None, str]:
    """Page id, Instagram professional account id, and a PAGE access token.

    Meta's current Pages API rejects user/system-user tokens on Page endpoints
    ("A Page access token is required"), so we mint one from /me/accounts."""
    want = env("FB_PAGE_ID")
    pages = graph("GET", "me/accounts", fields="id,name,access_token,instagram_business_account", limit=50, access_token=token).get("data", [])
    if not pages:
        sys.exit("[publish] the token can see no Pages. Either the Page is not assigned to the system user in Business Settings, "
                 "or the token was generated without pages_show_list (a regenerated token needs pages_show_list, pages_manage_posts, "
                 "pages_read_engagement, instagram_basic, instagram_content_publish, instagram_manage_insights, business_management)")
    if want:
        match = [x for x in pages if x["id"] == want]
        if not match:
            sys.exit(f"[publish] FB_PAGE_ID {want} is not among the Pages this token can see")
        pg = match[0]
    elif len(pages) > 1:
        names = ", ".join(f"{x['name']} ({x['id']})" for x in pages)
        sys.exit(f"[publish] token can see several Pages, set FB_PAGE_ID: {names}")
    else:
        pg = pages[0]
    page = pg["id"]
    ig = env("IG_USER_ID") or (pg.get("instagram_business_account") or {}).get("id")
    page_token = pg.get("access_token") or token
    print(f"[publish] using Page {pg['name']} ({page})" + (f", Instagram {ig}" if ig else ", no Instagram account linked"))
    return page, ig, page_token


def public_urls(p: dict) -> list[str]:
    """Prefer the site URLs; fall back to GitHub's public raw URL for each image
    (the repo is public) so posting never waits on a Netlify deploy."""
    urls = list(p.get("image_urls") or [p["image_url"]])
    paths = list(p.get("image_paths") or [p.get("image_path")])
    repo = env("GITHUB_REPOSITORY") or load_config()["social"].get("github_repo") or "DonPaisan/DDS"
    ref = env("GITHUB_REF_NAME") or load_config()["social"].get("github_branch") or "main"
    out = []
    for u, path in zip(urls, paths):
        ok = False
        try:
            ok = requests.head(u, timeout=20, allow_redirects=True).status_code == 200
        except requests.RequestException:
            pass
        if ok:
            out.append(u)
        elif path:
            out.append(f"https://raw.githubusercontent.com/{repo}/{ref}/{path}")
        else:
            out.append(u)
    return out


def caption_text(p: dict) -> str:
    tags = " ".join("#" + t.strip("#") for t in p.get("hashtags", []))
    return f"{p['caption']}\n\n{tags}".strip()


def _wait_ready(container_id: str, token: str) -> None:
    for _ in range(60):   # video containers can take a couple of minutes
        st = graph("GET", container_id, fields="status_code,status", access_token=token)
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container {container_id} {code}: {st.get('status')}")
        time.sleep(3)
    raise RuntimeError(f"Instagram container {container_id} not ready after 90s")


def collab(p: dict) -> dict:
    """Instagram Collab: up to 3 usernames who co-author the post once they accept the invite in
    the app. Their followers then see it in their feeds. Set `collaborators` on a queue entry,
    or `social.default_collaborators` in config for every feed post."""
    names = p.get("collaborators")
    if names is None:
        names = load_config()["social"].get("default_collaborators") or []
    names = [n.lstrip("@") for n in names][:3]
    import json as _json
    return {"collaborators": _json.dumps(names)} if names else {}


def post_instagram(p: dict, token: str, ig: str) -> dict:
    """Container model: create → poll status_code until FINISHED → publish.
    Carousels: one container per slide (is_carousel_item), then a CAROUSEL parent.
    Stories: media_type=STORIES with a 9:16 image, no caption."""
    urls = public_urls(p)
    if p.get("kind") == "reel":
        creation = graph("POST", f"{ig}/media", media_type="REELS", video_url=urls[0], caption=caption_text(p), share_to_feed="true", access_token=token, **collab(p))
        _wait_ready(creation["id"], token)
        return graph("POST", f"{ig}/media_publish", creation_id=creation["id"], access_token=token)
    if p.get("surface") == "story":
        creation = graph("POST", f"{ig}/media", media_type="STORIES", image_url=urls[0], access_token=token)
        _wait_ready(creation["id"], token)
        return graph("POST", f"{ig}/media_publish", creation_id=creation["id"], access_token=token)
    if len(urls) > 1:
        children = []
        for u in urls[:10]:
            c = graph("POST", f"{ig}/media", image_url=u, is_carousel_item="true", access_token=token)
            _wait_ready(c["id"], token)
            children.append(c["id"])
        creation = graph("POST", f"{ig}/media", media_type="CAROUSEL", children=",".join(children), caption=caption_text(p), access_token=token, **collab(p))
        _wait_ready(creation["id"], token)
        return graph("POST", f"{ig}/media_publish", creation_id=creation["id"], access_token=token)
    creation = graph("POST", f"{ig}/media", image_url=urls[0], caption=caption_text(p), access_token=token, **collab(p))
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
    """Single photo → /photos. Several → unpublished photos attached to one feed post.
    Stories → an unpublished photo, then /photo_stories."""
    urls = public_urls(p)
    if p.get("kind") == "reel":
        return graph("POST", f"{page}/videos", file_url=urls[0], description=caption_text(p), access_token=token)
    if p.get("surface") == "story":
        pid = graph("POST", f"{page}/photos", url=urls[0], published="false", access_token=token)["id"]
        return graph("POST", f"{page}/photo_stories", photo_id=pid, access_token=token)
    if len(urls) == 1:
        return graph("POST", f"{page}/photos", url=urls[0], message=caption_text(p), access_token=token)
    ids = [graph("POST", f"{page}/photos", url=u, published="false", access_token=token)["id"] for u in urls]
    params = {"message": caption_text(p), "access_token": token}
    for i, pid in enumerate(ids):
        params[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    return graph("POST", f"{page}/feed", **params)


def due_posts(t: str | None = None, slot: str | None = None):
    """Queued posts scheduled on or before `t`. With a slot (am/pm), today's posts
    only publish in their own slot; overdue ones from earlier days always go."""
    t = t or today().isoformat()
    for f in sorted(QUEUE_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for p in data["posts"]:
            if p["status"] not in ("queued", "partial") or p["scheduled_for"] > t:
                continue
            if p.get("needs_audio"):
                print(f"[publish] {p['id']}: reel has no licensed music track yet (agent/assets/audio/) — skipping", file=sys.stderr)
                continue
            if slot and p["scheduled_for"] == t and p.get("slot", slot) != slot:
                continue
            yield f, data, p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--really", action="store_true", help="actually post")
    ap.add_argument("--date", default=None, help="treat this YYYY-MM-DD as today (default: today UTC)")
    ap.add_argument("--slot", choices=["am", "noon", "pm"], default=None, help="only post items in this slot for today")
    args = ap.parse_args(argv)
    load_env()
    cfg = load_config()["social"]
    live = args.really and cfg["enabled"]
    if args.really and not cfg["enabled"]:
        print("[publish] social.enabled is false in config.yml — dry run only.")
    token = (env("FB_PAGE_TOKEN") or env("META_TOKEN")) if live else None
    if live and not token:
        sys.exit("[publish] FB_PAGE_TOKEN or META_TOKEN not set")
    page, ig, page_token = resolve_ids(token) if live else (None, None, None)
    if page_token:
        token = page_token   # Page token works for both Page and Instagram publishing

    n = 0
    for f, data, p in due_posts(args.date, args.slot):
        n += 1
        if not live:
            n = len(p.get("image_urls") or [1])
            print(f"[publish:DRY-RUN] {p['scheduled_for']} {p.get('slot', '-'):>4} {p.get('surface', 'feed'):>5} {p['id']} ({n} image{'s' if n > 1 else ''}) → {', '.join(p['platforms'])}: {p.get('title') or p.get('card_text')}")
            continue
        # Check the image is really public before Meta tries to fetch it.
        missing = [u for u in public_urls(p) if requests.head(u, timeout=20, allow_redirects=True).status_code != 200]
        if missing:
            print(f"[publish] {p['id']}: {len(missing)} image(s) not reachable ({missing[0]}) — skipping", file=sys.stderr)
            continue
        results = dict(p.get("results") or {})
        for platform in p["platforms"]:
            if "error" not in (results.get(platform) or {"error": 1}):
                continue   # already posted there; only retry the platform that failed
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
        p["posted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        p["results"] = results
        f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        log_action({"mode": "APPLY", "action": "social_post", "post_id": p["id"], "results": results})
        print(f"[publish] {p['id']} → {p['status']}")
    if not n:
        print("[publish] nothing due today.")


if __name__ == "__main__":
    main()
