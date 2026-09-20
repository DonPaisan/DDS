"""Pull ad-level daily insights from the Meta Marketing API into sqlite.

Idempotent by (day, ad_id). Safe to run hourly. Read-only against Meta.

  python src/fetch_meta.py            # last 7 days
  python src/fetch_meta.py --days 28
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import requests

from common import db, days_ago, env, load_config, load_env, today

FIELDS = ",".join([
    "ad_id", "ad_name", "adset_id", "adset_name", "campaign_id", "campaign_name",
    "spend", "impressions", "reach", "clicks", "inline_link_clicks", "ctr", "cpc", "cpm", "frequency", "actions",
])


class MetaError(RuntimeError):
    pass


def graph_get(path: str, params: dict) -> dict:
    load_env()
    token = env("META_TOKEN", required=True)
    version = env("META_API_VERSION", "v26.0")
    url = f"https://graph.facebook.com/{version}/{path}"
    r = requests.get(url, params={**params, "access_token": token}, timeout=60)
    try:
        data = r.json()
    except ValueError:
        raise MetaError(f"non-JSON response {r.status_code}: {r.text[:300]}")
    if "error" in data:
        e = data["error"]
        code = e.get("code")
        # 190 = invalid/expired token. Fail loudly; a silent no-op here hides a broken pipeline.
        raise MetaError(f"Meta API error {code} ({e.get('type')}): {e.get('message')}" + (" — TOKEN INVALID, regenerate the system user token" if code == 190 else ""))
    return data


def paged(path: str, params: dict):
    data = graph_get(path, params)
    while True:
        for row in data.get("data", []):
            yield row
        nxt = data.get("paging", {}).get("next")
        if not nxt:
            break
        r = requests.get(nxt, timeout=60)
        data = r.json()
        if "error" in data:
            raise MetaError(str(data["error"]))


def action_sum(actions: list | None, types: list[str]) -> int:
    if not actions:
        return 0
    return int(sum(float(a.get("value", 0)) for a in actions if a.get("action_type") in types))


def fetch_insights(days: int) -> int:
    cfg = load_config()["meta"]
    account = env("META_AD_ACCOUNT_ID", required=True)
    since, until = days_ago(days).isoformat(), today().isoformat()
    rows = paged(f"{account}/insights", {
        "level": "ad", "fields": FIELDS, "time_increment": 1, "limit": 500,
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
    })
    conn = db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    for r in rows:
        conn.execute(
            """INSERT OR REPLACE INTO ad_daily
               (day, ad_id, ad_name, adset_id, adset_name, campaign_id, campaign_name, spend, impressions, reach, clicks,
                link_clicks, landing_page_views, leads, ctr, cpc, cpm, frequency, fetched_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                r["date_start"], r["ad_id"], r.get("ad_name"), r.get("adset_id"), r.get("adset_name"),
                r.get("campaign_id"), r.get("campaign_name"),
                float(r.get("spend", 0)), int(r.get("impressions", 0)), int(r.get("reach", 0)), int(r.get("clicks", 0)),
                int(r.get("inline_link_clicks", 0)),
                action_sum(r.get("actions"), cfg["landing_page_view_action_types"]),
                action_sum(r.get("actions"), cfg["lead_action_types"]),
                float(r["ctr"]) if r.get("ctr") else None, float(r["cpc"]) if r.get("cpc") else None,
                float(r["cpm"]) if r.get("cpm") else None, float(r["frequency"]) if r.get("frequency") else None, now,
            ),
        )
        n += 1
    conn.commit()
    return n


def fetch_adsets() -> int:
    account = env("META_AD_ACCOUNT_ID", required=True)
    conn = db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    for a in paged(f"{account}/adsets", {"fields": "id,name,status,effective_status,daily_budget", "limit": 200}):
        conn.execute("INSERT OR REPLACE INTO adset_status (adset_id, name, status, daily_budget_cents, fetched_at) VALUES (?,?,?,?,?)",
                     (a["id"], a.get("name"), a.get("effective_status") or a.get("status"), int(a["daily_budget"]) if a.get("daily_budget") else None, now))
        n += 1
    conn.commit()
    return n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args(argv)
    try:
        n = fetch_insights(args.days)
        m = fetch_adsets()
    except MetaError as e:
        print(f"[fetch_meta] {e}", file=sys.stderr)
        sys.exit(2)
    print(f"[fetch_meta] stored {n} ad-day rows, {m} ad sets")


if __name__ == "__main__":
    main()
