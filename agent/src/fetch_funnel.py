"""Pull landing-page funnel events from the site's /api/report endpoint into sqlite.

  python src/fetch_funnel.py            # last 7 days
  python src/fetch_funnel.py --days 30
"""
from __future__ import annotations

import argparse
import json
import sys

import requests

from common import db, days_ago, env, load_env, today


def pull_events(days: int) -> list[dict]:
    load_env()
    site = env("SITE_URL", required=True).rstrip("/")
    token = env("REPORT_TOKEN", required=True)
    r = requests.get(f"{site}/api/report", params={"type": "events", "from": days_ago(days).isoformat(), "to": today().isoformat()},
                     headers={"Authorization": f"Bearer {token}"}, timeout=120)
    if r.status_code != 200:
        sys.exit(f"[fetch_funnel] {r.status_code}: {r.text[:300]}")
    return r.json().get("events", [])


def store_events(events: list[dict]) -> int:
    conn = db()
    n = 0
    for e in events:
        attr = e.get("attr") or {}
        ctx = e.get("ctx") or {}
        answer = e.get("answer")
        conn.execute(
            """INSERT OR IGNORE INTO funnel_events
               (event_id, ts, day, type, session_id, visitor_id, step, question_id, answer, ms, survey_version, device,
                utm_source, utm_campaign, utm_content, utm_term, ad_id, adset_id, fbclid, extra, raw)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                e["event_id"], e["ts"], e["ts"][:10], e["type"], e.get("session_id"), e.get("visitor_id"), e.get("step"),
                e.get("question_id"), json.dumps(answer) if isinstance(answer, list) else answer, e.get("ms"),
                e.get("survey_version"), ctx.get("device"), attr.get("utm_source"), attr.get("utm_campaign"),
                attr.get("utm_content"), attr.get("utm_term"), attr.get("ad_id"), attr.get("adset_id"), attr.get("fbclid"),
                json.dumps(e.get("extra")) if e.get("extra") else None, json.dumps(e),
            ),
        )
        n += conn.total_changes and 1
    conn.commit()
    return len(events)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args(argv)
    events = pull_events(args.days)
    n = store_events(events)
    print(f"[fetch_funnel] pulled {n} events")


if __name__ == "__main__":
    main()
