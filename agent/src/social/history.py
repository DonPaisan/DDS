"""Every post the Instagram account has ever made, with whatever numbers the token can read.

  python src/social/history.py

Likes and comments come from the media list (instagram_basic, always readable). Reach and
views come from insights (instagram_manage_insights, readable only once the Instagram account
is assigned to the system user). Account-level reach split into followers vs non-followers
for the last 30 days is pulled when the permission allows.

Writes agent/social/history.json and agent/social/history.md. The .md answers the standing
question: did older posts reach non-followers, and are the new ones?
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import AGENT_DIR, env, load_env  # noqa: E402
from social.publish import graph, resolve_ids  # noqa: E402
from social.metrics import media_insights  # noqa: E402

OUT_JSON = AGENT_DIR / "social" / "history.json"
OUT_MD = AGENT_DIR / "social" / "history.md"


def all_media(ig: str, token: str) -> list[dict]:
    out, after = [], None
    while True:
        kw = dict(fields="id,caption,media_type,media_product_type,timestamp,like_count,comments_count,permalink", limit=100, access_token=token)
        if after:
            kw["after"] = after
        r = graph("GET", f"{ig}/media", **kw)
        out += r.get("data", [])
        after = (r.get("paging") or {}).get("cursors", {}).get("after")
        if not after or not r.get("paging", {}).get("next"):
            break
    return out


def follow_split(ig: str, token: str) -> dict:
    """Account reach for the last 30 days split by follower / non-follower, if readable."""
    since = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
    until = int(datetime.now(timezone.utc).timestamp())
    try:
        d = graph("GET", f"{ig}/insights", metric="reach", period="day", metric_type="total_value", breakdown="follow_type", since=since, until=until, access_token=token).get("data", [])
        res = ((d[0].get("total_value") or {}).get("breakdowns") or [{}])[0].get("results", []) if d else []
        return {r["dimension_values"][0]: r["value"] for r in res}
    except (RuntimeError, KeyError, IndexError) as e:
        return {"error": str(e)[:200]}


def kind_of(m: dict) -> str:
    pt = (m.get("media_product_type") or "").upper()
    if pt == "REELS":
        return "reel"
    if pt == "STORY":
        return "story"
    return "feed"


def main():
    load_env()
    token = env("META_TOKEN") or env("FB_PAGE_TOKEN")
    if not token:
        sys.exit("META_TOKEN missing")
    page, ig, page_token = resolve_ids(token)
    if not ig:
        sys.exit("no Instagram account linked to the Page")
    media = all_media(ig, page_token)
    rows = []
    for m in media:
        row = {"id": m["id"], "date": m["timestamp"][:10], "type": m.get("media_type"), "kind": kind_of(m), "likes": m.get("like_count"), "comments": m.get("comments_count"),
               "caption": (m.get("caption") or "")[:80].replace("\n", " "), "permalink": m.get("permalink")}
        ins = media_insights(m["id"], row["kind"], page_token)
        if "error" in ins:
            row["insights_error"] = ins["error"][:80]
        else:
            row.update({k: ins.get(k) for k in ("reach", "views", "saved", "shares") if ins.get(k) is not None})
        rows.append(row)
    rows.sort(key=lambda r: r["date"], reverse=True)
    split = follow_split(ig, page_token)
    snap = {"pulled_at": datetime.now(timezone.utc).isoformat(timespec="minutes"), "ig": ig, "posts": rows, "reach_split_30d": split}
    OUT_JSON.write_text(json.dumps(snap, indent=1, ensure_ascii=False))

    readable = [r for r in rows if "reach" in r]
    lines = [f"# Post history — pulled {snap['pulled_at']}", ""]
    if "error" in split:
        lines.append("**Followers vs non-followers (last 30 days):** not readable yet. The token needs `instagram_manage_insights`, which comes with assigning the Instagram account to the system user (Business Settings → System users → Instagram row → Manage → Everything).")
    else:
        f, nf = split.get("FOLLOWER", 0), split.get("NON_FOLLOWER", 0)
        lines.append(f"**Reach, last 30 days:** {f} followers, {nf} non-followers.")
    lines.append("")
    if readable:
        lines.append("Reach is readable, so the question is answered below by date: posts before September 2026 vs after.")
    else:
        lines.append("Reach is not readable, so likes and comments stand in. A post nobody saw has zero of both; a post that reached people usually has at least a few.")
    lines += ["", "| Date | Type | Likes | Comments | Reach | Views | Caption |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['date']} | {r['kind']} | {r.get('likes', '')} | {r.get('comments', '')} | {r.get('reach', '')} | {r.get('views', '')} | {r['caption'][:50]} |")
    old = [r for r in rows if r["date"] < "2026-09-20"]
    new = [r for r in rows if r["date"] >= "2026-09-20"]
    def tot(rs, k): return sum((r.get(k) or 0) for r in rs)
    lines += ["", "## Then vs now", ""]
    lines.append(f"- Before 2026-09-20: {len(old)} posts, {tot(old, 'likes')} likes, {tot(old, 'comments')} comments" + (f", {tot(old, 'reach')} reach" if readable else "") + ".")
    lines.append(f"- Since 2026-09-20: {len(new)} posts, {tot(new, 'likes')} likes, {tot(new, 'comments')} comments" + (f", {tot(new, 'reach')} reach" if readable else "") + ".")
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(f"[history] {len(rows)} posts, {len(readable)} with insights; split={split}")


if __name__ == "__main__":
    main()
