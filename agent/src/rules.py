"""Deterministic rules engine. Reads sqlite, returns a list of proposed actions.

DRY RUN BY DEFAULT. Nothing touches the ad account unless:
  • config.yml  rules.enabled: true, AND
  • you pass --apply (or --apply-safety-only)

  python src/rules.py                    # print what it WOULD do
  python src/rules.py --apply-safety-only
  python src/rules.py --apply            # includes budget scaling (only if safety_only: false)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from common import db, days_ago, load_config, log_action, today


def adset_metrics(conn, lookback_days: int) -> list[dict]:
    rows = conn.execute(
        """SELECT adset_id, MAX(adset_name) AS adset_name, SUM(spend) AS spend, SUM(leads) AS leads,
                  SUM(link_clicks) AS link_clicks, SUM(impressions) AS impressions
           FROM ad_daily WHERE day >= ? GROUP BY adset_id""",
        (days_ago(lookback_days).isoformat(),),
    ).fetchall()
    status = {r["adset_id"]: dict(r) for r in conn.execute("SELECT * FROM adset_status").fetchall()}
    out = []
    for r in rows:
        st = status.get(r["adset_id"], {})
        out.append({
            "adset_id": r["adset_id"], "adset_name": r["adset_name"], "spend": float(r["spend"] or 0), "leads": int(r["leads"] or 0),
            "link_clicks": int(r["link_clicks"] or 0), "impressions": int(r["impressions"] or 0),
            "cpl": (float(r["spend"]) / r["leads"]) if r["leads"] else None,
            "status": st.get("status"), "daily_budget_cents": st.get("daily_budget_cents"),
        })
    return out


def runaway_spend(conn, adset_id: str, hours: int) -> tuple[float, int]:
    days = max(1, round(hours / 24))
    r = conn.execute("SELECT SUM(spend) AS spend, SUM(leads) AS leads FROM ad_daily WHERE adset_id = ? AND day >= ?",
                     (adset_id, days_ago(days - 1).isoformat())).fetchone()
    return float(r["spend"] or 0), int(r["leads"] or 0)


def budget_changes_today(conn, adset_id: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM budget_changes WHERE adset_id = ? AND day = ?", (adset_id, today().isoformat())).fetchone()[0]


def evaluate(conn, cfg: dict) -> list[dict]:
    """Pure decision function. Returns proposed actions; never executes."""
    R = cfg["rules"]
    actions: list[dict] = []
    metrics = adset_metrics(conn, R["lookback_days"])
    active = [m for m in metrics if (m["status"] or "ACTIVE") == "ACTIVE"]

    # Account kill switch: yesterday's total spend
    y = conn.execute("SELECT SUM(spend) AS s FROM ad_daily WHERE day = ?", (days_ago(1).isoformat(),)).fetchone()["s"] or 0
    if y > R["account_daily_spend_kill_usd"]:
        for m in active:
            actions.append({"rule": "account_kill_switch", "action": "pause", "adset_id": m["adset_id"], "adset_name": m["adset_name"],
                            "reason": f"Account spent ${y:,.2f} yesterday, above the ${R['account_daily_spend_kill_usd']} kill switch. Pausing everything."})
        return actions

    total_spend = sum(m["spend"] for m in active)
    total_leads = sum(m["leads"] for m in active)
    acct_cpl = total_spend / total_leads if total_leads else None

    for m in active:
        # Runaway: spent > X with zero leads in the window → broken pixel, dead page, or dead audience
        spend_w, leads_w = runaway_spend(conn, m["adset_id"], R["runaway_hours"])
        if spend_w > R["runaway_spend_usd"] and leads_w == 0:
            actions.append({"rule": "spend_runaway", "action": "pause", **_ids(m),
                            "reason": f"Spent ${spend_w:,.2f} in the last {R['runaway_hours']}h with 0 leads (threshold ${R['runaway_spend_usd']}). Pausing; check the pixel and the page before resuming."})
            continue

        # Minimum evidence gate for everything below
        if m["leads"] < R["min_conversions_for_decision"] or acct_cpl is None:
            continue

        if m["cpl"] and m["cpl"] > acct_cpl * R["kill_cpl_multiple"]:
            actions.append({"rule": "kill_loser", "action": "pause", **_ids(m),
                            "reason": f"CPL ${m['cpl']:,.2f} is {m['cpl'] / acct_cpl:.1f}× the account average ${acct_cpl:,.2f} over {R['lookback_days']}d with {m['leads']} leads."})
            continue

        if R["safety_only"]:
            continue

        if m["cpl"] and m["cpl"] < acct_cpl * R["scale_cpl_multiple"] and m["daily_budget_cents"]:
            if budget_changes_today(conn, m["adset_id"]) >= R["max_budget_changes_per_day"]:
                continue
            old = m["daily_budget_cents"]
            new = int(old * (1 + R["scale_step_pct"] / 100))
            new = max(R["budget_floor_usd"] * 100, min(R["budget_ceiling_usd"] * 100, new))
            if new != old:
                actions.append({"rule": "scale_winner", "action": "set_budget", **_ids(m), "old_budget_cents": old, "new_budget_cents": new,
                                "reason": f"CPL ${m['cpl']:,.2f} is {m['cpl'] / acct_cpl:.2f}× account average with {m['leads']} leads. +{R['scale_step_pct']}% clamped to ${R['budget_floor_usd']}–${R['budget_ceiling_usd']}/day."})
    return actions


def _ids(m):
    return {"adset_id": m["adset_id"], "adset_name": m["adset_name"], "metrics": {k: m[k] for k in ("spend", "leads", "cpl", "link_clicks")}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true", help="execute all actions (requires rules.enabled and safety_only: false for scaling)")
    g.add_argument("--apply-safety-only", action="store_true", help="execute pause actions only")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    cfg = load_config()
    conn = db()
    actions = evaluate(conn, cfg)
    mode = "APPLY" if (args.apply or args.apply_safety_only) and cfg["rules"]["enabled"] else "DRY-RUN"
    if (args.apply or args.apply_safety_only) and not cfg["rules"]["enabled"]:
        print("[rules] rules.enabled is false in config.yml — running as dry-run.")

    if args.json:
        print(json.dumps({"mode": mode, "actions": actions}, indent=2))
    elif not actions:
        print(f"[rules:{mode}] no actions.")
    else:
        for a in actions:
            print(f"[rules:{mode}] {a['action']:<10} {a['adset_name'] or a['adset_id']:<40} ({a['rule']}) — {a['reason']}")

    for a in actions:
        if args.apply_safety_only and a["action"] != "pause":
            continue
        entry = {"mode": mode, **a}
        if mode == "APPLY":
            from act import execute
            entry["result"] = execute(a, dry_run=False)
            if a["action"] == "set_budget":
                conn.execute("INSERT INTO budget_changes (day, adset_id, old_cents, new_cents, at) VALUES (?,?,?,?,?)",
                             (today().isoformat(), a["adset_id"], a["old_budget_cents"], a["new_budget_cents"], datetime.now(timezone.utc).isoformat()))
                conn.commit()
        log_action(entry)


if __name__ == "__main__":
    main()
