"""Pull what is already on the Facebook Page and Instagram account so new content
can match the existing voice. Read-only. Writes agent/social/inventory.md + .json (committed by the workflow).

  python src/social/inspect.py --limit 30
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import AGENT_DIR, env, load_env  # noqa: E402

OUT_DIR = AGENT_DIR / "social"
from social.publish import graph, resolve_ids  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args(argv)
    load_env()
    token = env("FB_PAGE_TOKEN") or env("META_TOKEN") or sys.exit("[inspect] META_TOKEN not set")
    page, ig, page_token = resolve_ids(token)
    token = page_token
    out = {"page_id": page, "ig_id": ig, "instagram": [], "facebook": []}

    if ig:
        prof = graph("GET", ig, fields="username,name,biography,followers_count,media_count,website", access_token=token)
        out["instagram_profile"] = prof
        media = graph("GET", f"{ig}/media", fields="id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count,children{media_type,media_url}",
                      limit=args.limit, access_token=token).get("data", [])
        out["instagram"] = media
    try:
        posts = graph("GET", f"{page}/posts", fields="id,message,created_time,permalink_url,attachments{media_type,type,subattachments},shares,likes.summary(true),comments.summary(true)",
                      limit=args.limit, access_token=token).get("data", [])
    except RuntimeError as e:
        print(f"[inspect] Facebook posts unavailable: {e}", file=sys.stderr)
        posts = []
        out["facebook_error"] = str(e)
    out["facebook"] = posts

    (OUT_DIR / "inventory.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    L = ["# Social inventory", ""]
    if ig:
        p = out.get("instagram_profile", {})
        L += [f"## Instagram @{p.get('username')} — {p.get('followers_count')} followers, {p.get('media_count')} posts", f"Bio: {p.get('biography')}", f"Website: {p.get('website')}", ""]
        for m in out["instagram"]:
            kids = len((m.get("children") or {}).get("data", []))
            L += [f"### {m.get('timestamp', '')[:10]} · {m.get('media_type')}{f' ({kids} slides)' if kids else ''} · {m.get('like_count', 0)} likes · {m.get('comments_count', 0)} comments", f"{m.get('permalink')}", "", (m.get("caption") or "(no caption)").strip(), ""]
    L += ["## Facebook Page posts", ""]
    if out.get("facebook_error"):
        L += [f"_Could not read Page posts: {out['facebook_error'][:200]}_", ""]
    for p in out["facebook"]:
        att = ((p.get("attachments") or {}).get("data") or [{}])[0]
        L += [f"### {p.get('created_time', '')[:10]} · {att.get('type', 'status')} · {((p.get('likes') or {}).get('summary') or {}).get('total_count', 0)} likes · {((p.get('comments') or {}).get('summary') or {}).get('total_count', 0)} comments",
              f"{p.get('permalink_url')}", "", (p.get("message") or "(no text)").strip(), ""]
    (OUT_DIR / "inventory.md").write_text("\n".join(L), encoding="utf-8")
    print(f"[inspect] {len(out['instagram'])} Instagram posts, {len(out['facebook'])} Facebook posts → agent/social/inventory.md")


if __name__ == "__main__":
    main()
