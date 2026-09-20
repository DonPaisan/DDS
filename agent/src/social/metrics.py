"""Pull engagement for every post in the last N days into a dated snapshot log.

  python src/social/metrics.py            # last 14 days
  python src/social/metrics.py --days 30

Writes agent/social/metrics.jsonl (one line per post per snapshot) and
agent/social/account.jsonl (one line per day: followers, reach, follows).
Instagram metric names changed in 2025 (views replaced impressions/plays), so
each media type has a preferred metric set with fallbacks.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import AGENT_DIR, env, load_env  # noqa: E402
from social.publish import graph, resolve_ids  # noqa: E402

QUEUE_DIR = AGENT_DIR / "social" / "queue"
METRICS = AGENT_DIR / "social" / "metrics.jsonl"
ACCOUNT = AGENT_DIR / "social" / "account.jsonl"

MEDIA_METRICS = {
    "feed":  [["reach", "views", "likes", "comments", "saved", "shares", "total_interactions"], ["reach", "likes", "comments", "saved", "shares", "total_interactions"], ["reach", "likes", "comments", "saved"]],
    "reel":  [["reach", "views", "likes", "comments", "saved", "shares", "total_interactions"], ["reach", "plays", "likes", "comments", "saved", "shares", "total_interactions"], ["reach", "likes", "comments", "saved"]],
    "story": [["reach", "views", "replies", "shares", "total_interactions"], ["reach", "impressions", "replies"], ["reach"]],
}


def media_insights(media_id: str, kind: str, token: str) -> dict:
    last_err = None
    for metrics in MEDIA_METRICS[kind]:
        try:
            data = graph("GET", f"{media_id}/insights", metric=",".join(metrics), access_token=token).get("data", [])
            out = {}
            for m in data:
                vals = m.get("values") or []
                out[m["name"]] = (vals[0].get("value") if vals else m.get("total_value", {}).get("value"))
            return out
        except RuntimeError as e:
            last_err = str(e)
            continue
    return {"error": (last_err or "unknown")[:200]}


def account_snapshot(ig: str, token: str) -> dict:
    out = {"date": date.today().isoformat()}
    try:
        prof = graph("GET", ig, fields="followers_count,follows_count,media_count", access_token=token)
        out.update({"followers": prof.get("followers_count"), "following": prof.get("follows_count"), "media": prof.get("media_count")})
    except RuntimeError as e:
        out["profile_error"] = str(e)[:200]
    since = int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp())
    try:
        d = graph("GET", f"{ig}/insights", metric="reach", period="day", since=since, access_token=token).get("data", [])
        vals = (d[0].get("values") or []) if d else []
        out["reach_yesterday"] = vals[-1]["value"] if vals else None
    except RuntimeError as e:
        out["reach_error"] = str(e)[:120]
    try:
        d = graph("GET", f"{ig}/insights", metric="follows_and_unfollows", period="day", metric_type="total_value", since=since, access_token=token).get("data", [])
        out["follows_2d"] = (d[0].get("total_value") or {}).get("value") if d else None
    except RuntimeError as e:
        out["follows_error"] = str(e)[:120]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args(argv)
    load_env()
    token = env("FB_PAGE_TOKEN") or env("META_TOKEN") or sys.exit("[metrics] META_TOKEN not set")
    page, ig, page_token = resolve_ids(token)
    token = page_token
    if not ig:
        sys.exit("[metrics] no Instagram account linked")
    cutoff = (date.today() - timedelta(days=args.days)).isoformat()
    now = datetime.now(timezone.utc).isoformat(timespec="minutes")
    rows = []
    for qf in sorted(QUEUE_DIR.glob("*.json")):
        for p in json.loads(qf.read_text(encoding="utf-8"))["posts"]:
            if p["status"] not in ("posted", "partial") or p["scheduled_for"] < cutoff:
                continue
            ig_res = (p.get("results") or {}).get("instagram") or {}
            mid = ig_res.get("id")
            if not mid:
                continue
            kind = "reel" if p.get("kind") == "reel" else ("story" if p.get("surface") == "story" else "feed")
            ins = media_insights(mid, kind, token)
            posted_at = p.get("posted_at") or p["scheduled_for"]
            age_h = None
            try:
                age_h = round((datetime.now(timezone.utc) - datetime.fromisoformat(posted_at.replace("Z", "+00:00"))).total_seconds() / 3600, 1)
            except Exception:
                pass
            rows.append({"snapshot": now, "post_id": p["id"], "media_id": mid, "kind": p.get("kind"), "surface": p.get("surface", "feed"), "subkind": p.get("subkind"),
                         "theme": (p.get("spec") or {}).get("theme") or p.get("theme"), "topic": p.get("theme") or p.get("subkind"), "title": (p.get("title") or "")[:80],
                         "scheduled_for": p["scheduled_for"], "slot": p.get("slot"), "age_hours": age_h, **{k: v for k, v in ins.items()}})
    with open(METRICS, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    acct = account_snapshot(ig, token)
    acct["snapshot"] = now
    with open(ACCOUNT, "a", encoding="utf-8") as f:
        f.write(json.dumps(acct, ensure_ascii=False) + "\n")
    print(f"[metrics] {len(rows)} post snapshots; followers={acct.get('followers')} reach_yesterday={acct.get('reach_yesterday')}")


if __name__ == "__main__":
    main()
