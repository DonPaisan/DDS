"""Funnel math over stored events. Mirrors netlify/lib/funnel.js — keep in sync.

  python src/funnel.py            # print summary + findings for last 7 days
  python src/funnel.py --days 14 --json
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict

from common import db, days_ago, load_config, pct, today


def load_events(days: int) -> list[dict]:
    conn = db()
    rows = conn.execute("SELECT raw FROM funnel_events WHERE day >= ? ORDER BY ts", (days_ago(days).isoformat(),)).fetchall()
    return [json.loads(r["raw"]) for r in rows]


def _median(xs):
    return int(statistics.median(xs)) if xs else None


def sessionize(events: list[dict]) -> list[dict]:
    sessions: dict[str, dict] = {}
    for e in events:
        sid = e.get("session_id")
        if not sid:
            continue
        s = sessions.get(sid)
        if s is None:
            s = sessions[sid] = {
                "session_id": sid, "first_ts": e["ts"], "last_ts": e["ts"], "device": (e.get("ctx") or {}).get("device"),
                "attr": e.get("attr") or {}, "survey_version": e.get("survey_version"),
                "page_view": False, "cta_click": False, "survey_start": False, "form_submit": False, "lead": False, "lead_error": False,
                "max_scroll": 0, "steps_viewed": set(), "steps_completed": set(), "step_ms": defaultdict(list), "field_errors": [],
                "last_step": None, "last_question": None, "load_ms": None, "js_errors": 0, "backs": 0,
            }
        s["first_ts"] = min(s["first_ts"], e["ts"])
        s["last_ts"] = max(s["last_ts"], e["ts"])
        t = e["type"]
        extra = e.get("extra") or {}
        if t == "page_view":
            s["page_view"] = True
            if extra.get("load_ms") is not None:
                s["load_ms"] = extra["load_ms"]
        elif t == "cta_click":
            s["cta_click"] = True
        elif t == "scroll_depth":
            try:
                s["max_scroll"] = max(s["max_scroll"], int(e.get("answer") or 0))
            except (TypeError, ValueError):
                pass
        elif t == "survey_start":
            s["survey_start"] = True
        elif t == "step_view" and e.get("step") is not None:
            s["steps_viewed"].add(e["step"]); s["last_step"] = e["step"]; s["last_question"] = e.get("question_id")
        elif t == "step_complete" and e.get("step") is not None:
            s["steps_completed"].add(e["step"])
            if e.get("ms") is not None:
                s["step_ms"][e["step"]].append(e["ms"])
        elif t == "step_back":
            s["backs"] += 1
        elif t == "field_error":
            s["field_errors"].append(extra.get("field") or "unknown")
        elif t == "form_submit":
            s["form_submit"] = True
        elif t == "lead":
            s["lead"] = True
        elif t == "lead_error":
            s["lead_error"] = True
        elif t == "js_error":
            s["js_errors"] += 1
    return list(sessions.values())


def summarize(events: list[dict]) -> dict:
    sessions = sessionize(events)
    n = len(sessions)
    count = lambda f: sum(1 for s in sessions if f(s))  # noqa: E731

    step_ids: dict[int, str] = {}
    for e in events:
        if e["type"] == "step_view" and e.get("step") is not None:
            step_ids[e["step"]] = e.get("question_id")
    max_step = max(step_ids) if step_ids else -1

    steps = []
    for i in range(max_step + 1):
        viewed = count(lambda s: i in s["steps_viewed"])
        completed = count(lambda s: i in s["steps_completed"])
        abandoned = count(lambda s: s["last_step"] == i and i not in s["steps_completed"])
        ms = [m for s in sessions for m in s["step_ms"].get(i, [])]
        steps.append({"step": i, "question_id": step_ids.get(i), "viewed": viewed, "completed": completed,
                      "completion_rate": pct(completed, viewed), "abandoned_here": abandoned, "abandon_rate": pct(abandoned, viewed),
                      "median_ms": _median(ms)})

    starts = count(lambda s: s["survey_start"]); submits = count(lambda s: s["form_submit"]); leads = count(lambda s: s["lead"])
    by_device = {}
    for d in ("mobile", "desktop"):
        ss = [s for s in sessions if s["device"] == d]
        st = sum(1 for s in ss if s["survey_start"]); ld = sum(1 for s in ss if s["lead"])
        by_device[d] = {"sessions": len(ss), "starts": st, "leads": ld, "start_rate": pct(st, len(ss)), "lead_rate": pct(ld, len(ss))}

    by_source: dict[str, dict] = {}
    for s in sessions:
        a = s["attr"]
        k = " / ".join([a.get("utm_source") or ("facebook" if a.get("fbclid") else "direct"), a.get("utm_campaign") or "-", a.get("utm_content") or a.get("ad_id") or "-"])
        b = by_source.setdefault(k, {"sessions": 0, "starts": 0, "leads": 0})
        b["sessions"] += 1; b["starts"] += s["survey_start"]; b["leads"] += s["lead"]
    for b in by_source.values():
        b["start_rate"] = pct(b["starts"], b["sessions"]); b["lead_rate"] = pct(b["leads"], b["sessions"])

    field_errors: dict[str, int] = defaultdict(int)
    for s in sessions:
        for f in s["field_errors"]:
            field_errors[f] += 1

    by_version: dict[str, dict] = {}
    for s in sessions:
        b = by_version.setdefault(s["survey_version"] or "unknown", {"sessions": 0, "starts": 0, "leads": 0})
        b["sessions"] += 1; b["starts"] += s["survey_start"]; b["leads"] += s["lead"]

    no_start = [s for s in sessions if not s["survey_start"]]
    load_times = [s["load_ms"] for s in sessions if s["load_ms"] is not None]

    return {
        "sessions": n, "page_views": count(lambda s: s["page_view"]), "survey_starts": starts, "form_submits": submits, "leads": leads,
        "lead_errors": count(lambda s: s["lead_error"]), "js_error_sessions": count(lambda s: s["js_errors"] > 0),
        "rates": {"start_rate": pct(starts, n), "submit_rate_of_starts": pct(submits, starts), "lead_rate_of_sessions": pct(leads, n), "lead_rate_of_submits": pct(leads, submits)},
        "no_start": {"sessions": len(no_start), "never_scrolled_past_25": sum(1 for s in no_start if s["max_scroll"] < 25),
                     "clicked_cta_but_no_start": sum(1 for s in no_start if s["cta_click"])},
        "load": {"median_ms": _median(load_times), "over_3s": sum(1 for v in load_times if v > 3000)},
        "steps": steps, "by_device": by_device, "by_source": by_source, "by_version": by_version,
        "field_errors": dict(field_errors), "back_presses": sum(s["backs"] for s in sessions),
    }


def diagnose(s: dict, link_clicks: int | None = None, min_sessions: int = 30) -> list[dict]:
    out: list[dict] = []
    if s["sessions"] < min_sessions:
        return [{"level": "info", "code": "low_volume", "text": f"Only {s['sessions']} sessions in this window; below {min_sessions} the rates are noise. Keep collecting."}]
    if link_clicks is not None and s["sessions"] < link_clicks * 0.6:
        out.append({"level": "critical", "code": "click_to_view_gap", "text": f"Meta reports {link_clicks} link clicks but only {s['sessions']} sessions reached the page ({pct(s['sessions'], link_clicks)}%). That is a loading, redirect, or domain problem, not a page-content problem. Check the ad URL, that the site is up, and load time."})
    if s["load"]["over_3s"] > s["sessions"] * 0.25:
        out.append({"level": "critical", "code": "slow_load", "text": f"{s['load']['over_3s']} of {s['sessions']} sessions took over 3s to load (median {s['load']['median_ms']}ms). Mobile ad traffic bounces on slow pages before reading a word."})
    if s["js_error_sessions"] > s["sessions"] * 0.05:
        out.append({"level": "critical", "code": "js_errors", "text": f"{s['js_error_sessions']} sessions hit a JavaScript error. The survey may be broken for some browsers."})
    if s["form_submits"] and s["lead_errors"] >= s["form_submits"] * 0.2:
        out.append({"level": "critical", "code": "lead_endpoint_failing", "text": f"{s['lead_errors']} submissions failed to save against {s['form_submits']} attempts. People are trying to convert and can't."})
    sr = s["rates"]["start_rate"]
    if sr is not None and sr < 25:
        ns = s["no_start"]
        if ns["never_scrolled_past_25"] > ns["sessions"] * 0.5:
            out.append({"level": "high", "code": "bounce_above_fold", "text": f"Only {sr}% start the survey and most non-starters never scrolled. The first screen isn't matching what the ad promised. Fix the headline/subhead to echo the ad hook before touching the questions."})
        else:
            out.append({"level": "high", "code": "low_start_rate", "text": f"Only {sr}% start the survey even though people are scrolling. The offer or first question isn't compelling enough, or the survey isn't obviously the next step."})
    eligible = [st for st in s["steps"] if st["viewed"] >= 10]
    if eligible:
        worst = max(eligible, key=lambda st: st["abandon_rate"] or 0)
        if (worst["abandon_rate"] or 0) >= 30:
            is_contact = worst["step"] == len(s["steps"]) - 1
            out.append({"level": "high", "code": "contact_step_dropoff" if is_contact else "step_dropoff",
                        "text": (f"{worst['abandon_rate']}% of people who reach the contact step leave without submitting. They're interested but don't trust you with a phone number yet. Add reassurance, show what happens next, ask for less, or move consent text below the button."
                                 if is_contact else f"Step {worst['step'] + 1} ({worst['question_id']}) loses {worst['abandon_rate']}% of the people who see it. Reword it, make it lower-commitment, or move it later.")})
    if s["field_errors"]:
        f, c = max(s["field_errors"].items(), key=lambda kv: kv[1])
        if c >= max(5, s["form_submits"] * 0.3):
            out.append({"level": "medium", "code": "field_friction", "text": f'The "{f}" field produced {c} validation errors. Loosen validation or improve the hint text.'})
    m, d = s["by_device"]["mobile"], s["by_device"]["desktop"]
    if m["sessions"] >= 20 and d["sessions"] >= 20 and m["lead_rate"] is not None and d["lead_rate"] and m["lead_rate"] < d["lead_rate"] * 0.5:
        out.append({"level": "medium", "code": "mobile_gap", "text": f"Mobile converts at {m['lead_rate']}% vs desktop {d['lead_rate']}%. Almost all ad traffic is mobile, so test the page on a real phone."})
    if not out:
        out.append({"level": "info", "code": "healthy", "text": "No structural problem detected. Improvements now come from creative/audience and survey copy tests."})
    return out


def render_text(summary: dict, findings: list[dict]) -> str:
    s = summary
    lines = [
        f"Sessions {s['sessions']} → started survey {s['survey_starts']} ({s['rates']['start_rate']}%) → submitted {s['form_submits']} → leads {s['leads']} ({s['rates']['lead_rate_of_sessions']}% of sessions)",
        "",
        "Step-by-step:",
    ]
    for st in s["steps"]:
        lines.append(f"  {st['step'] + 1}. {st['question_id'] or '?':<16} viewed {st['viewed']:>5}  completed {st['completed']:>5}  abandoned here {st['abandoned_here']:>5} ({st['abandon_rate'] or 0}%)  median {st['median_ms'] or '-'} ms")
    lines += ["", f"Mobile: {s['by_device']['mobile']['sessions']} sessions, {s['by_device']['mobile']['lead_rate']}% lead rate · Desktop: {s['by_device']['desktop']['sessions']} sessions, {s['by_device']['desktop']['lead_rate']}% lead rate"]
    if s["by_source"]:
        lines += ["", "By ad (source / campaign / content):"]
        for k, b in sorted(s["by_source"].items(), key=lambda kv: -kv[1]["sessions"])[:10]:
            lines.append(f"  {k:<50} {b['sessions']:>5} sessions  {b['start_rate'] or 0:>5}% start  {b['leads']:>3} leads")
    lines += ["", "Findings:"]
    for f in findings:
        lines.append(f"  [{f['level'].upper()}] {f['text']}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--link-clicks", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_config()["funnel"]
    events = load_events(args.days or cfg["lookback_days"])
    summary = summarize(events)
    findings = diagnose(summary, args.link_clicks, cfg["min_sessions_for_diagnosis"])
    if args.json:
        print(json.dumps({"summary": summary, "findings": findings}, indent=2, default=list))
    else:
        print(render_text(summary, findings))


if __name__ == "__main__":
    main()
