"""Daily digest: ad spend + landing page funnel + what the rules would have done.

  python src/digest.py                 # fetch fresh data, write reports/YYYY-MM-DD.md, print, email if configured
  python src/digest.py --no-fetch      # use whatever is already in sqlite
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

import requests

from common import AGENT_DIR, REPORTS_DIR, db, days_ago, env, fmt_money, load_config, load_env, pct, today
from funnel import diagnose, load_events, render_text, summarize
from rules import evaluate


def ad_table(conn, since: str) -> list[dict]:
    rows = conn.execute(
        """SELECT ad_id, MAX(ad_name) AS ad_name, MAX(adset_name) AS adset_name, SUM(spend) AS spend, SUM(impressions) AS impressions,
                  SUM(link_clicks) AS link_clicks, SUM(landing_page_views) AS lpv, SUM(leads) AS leads
           FROM ad_daily WHERE day >= ? GROUP BY ad_id ORDER BY spend DESC""", (since,)).fetchall()
    return [dict(r) for r in rows]


def totals(rows: list[dict]) -> dict:
    t = {k: sum(r[k] or 0 for r in rows) for k in ("spend", "impressions", "link_clicks", "lpv", "leads")}
    t["cpl"] = t["spend"] / t["leads"] if t["leads"] else None
    t["ctr"] = pct(t["link_clicks"], t["impressions"])
    return t


def build_report(conn, cfg: dict) -> str:
    F = cfg["funnel"]
    days = F["lookback_days"]
    y = days_ago(1).isoformat()
    since = days_ago(days).isoformat()

    ads_y = ad_table(conn, y)
    ads_w = ad_table(conn, since)
    ty, tw = totals(ads_y), totals(ads_w)

    events = load_events(days)
    summary = summarize(events)
    findings = diagnose(summary, link_clicks=tw["link_clicks"] or None, min_sessions=F["min_sessions_for_diagnosis"])
    actions = evaluate(conn, cfg)

    L = [f"# DDS daily digest — {today().isoformat()}", ""]
    L += ["## Yesterday", f"Spend {fmt_money(ty['spend'])} · link clicks {ty['link_clicks']} · landing page views {ty['lpv']} · leads {ty['leads']} · CPL {fmt_money(ty['cpl'])}", ""]
    L += [f"## Last {days} days", f"Spend {fmt_money(tw['spend'])} · CTR {tw['ctr'] or 0}% · link clicks {tw['link_clicks']} · LP views {tw['lpv']} · leads {tw['leads']} · CPL {fmt_money(tw['cpl'])}", ""]

    if tw["link_clicks"]:
        gap = pct(summary["sessions"], tw["link_clicks"])
        L += [f"**Ad → page:** {tw['link_clicks']} clicks became {summary['sessions']} tracked sessions ({gap}%). "
              + ("Healthy." if gap and gap >= 60 else "Below 60% means people click and never see the page: check load time, the URL in the ad, and that the domain resolves."), ""]

    L += ["## Ads (last %d days)" % days, "", "| Ad | Ad set | Spend | Clicks | LPV | Leads | CPL |", "|---|---|---:|---:|---:|---:|---:|"]
    for r in ads_w[:15]:
        cpl = r["spend"] / r["leads"] if r["leads"] else None
        L.append(f"| {r['ad_name'] or r['ad_id']} | {r['adset_name'] or '-'} | {fmt_money(r['spend'])} | {r['link_clicks']} | {r['lpv']} | {r['leads']} | {fmt_money(cpl)} |")
    if not ads_w:
        L.append("| (no Meta data yet — run fetch_meta.py) | | | | | | |")

    L += ["", "## Landing page funnel", "", "```", render_text(summary, findings), "```", ""]

    review = (AGENT_DIR / "social" / "review.md")
    if review.exists():
        L += ["## Social", "", review.read_text(encoding="utf-8").split("\n", 1)[-1].strip(), ""]

    L += ["## What the rules engine would do", ""]
    if actions:
        for a in actions:
            L.append(f"- **{a['action']}** {a['adset_name'] or a['adset_id']} — {a['reason']}")
    else:
        L.append("- Nothing. Either no ad set crossed a threshold or there isn't enough data yet.")
    L += ["", f"_rules.enabled = {cfg['rules']['enabled']}, safety_only = {cfg['rules']['safety_only']}_", ""]
    return "\n".join(L)


def email_report(md: str) -> None:
    load_env()
    key, to = env("RESEND_API_KEY"), env("DIGEST_TO")
    if not key or not to:
        return
    r = requests.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {key}"}, json={
        "from": env("DIGEST_FROM", "digest@debtdirectsolutions.com"), "to": [t.strip() for t in to.split(",")],
        "subject": f"DDS digest {today().isoformat()}", "text": md}, timeout=30)
    print(f"[digest] email {'sent' if r.ok else 'failed: ' + r.text[:200]}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--no-email", action="store_true")
    args = ap.parse_args(argv)
    load_env()
    cfg = load_config()
    if not args.no_fetch:
        import fetch_funnel, fetch_meta
        try:
            if env("META_TOKEN"):
                fetch_meta.main(["--days", str(cfg["funnel"]["lookback_days"] + 1)])
            else:
                print("[digest] META_TOKEN not set; skipping Meta fetch", file=sys.stderr)
            if env("REPORT_TOKEN") and env("SITE_URL"):
                fetch_funnel.main(["--days", str(cfg["funnel"]["lookback_days"] + 1)])
            else:
                print("[digest] SITE_URL/REPORT_TOKEN not set; skipping funnel fetch", file=sys.stderr)
        except SystemExit as e:
            print(f"[digest] fetch failed: {e}", file=sys.stderr)
    conn = db()
    md = build_report(conn, cfg)
    path = REPORTS_DIR / f"{today().isoformat()}.md"
    path.write_text(md, encoding="utf-8")
    print(md)
    print(f"\n[digest] written to {path}")
    if not args.no_email:
        email_report(md)


if __name__ == "__main__":
    main()
