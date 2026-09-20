"""Turn metric snapshots into a plain-English review with a trend verdict.

  python src/social/review.py            # writes agent/social/review.md and prints it
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import AGENT_DIR  # noqa: E402

METRICS = AGENT_DIR / "social" / "metrics.jsonl"
ACCOUNT = AGENT_DIR / "social" / "account.jsonl"
OUT = AGENT_DIR / "social" / "review.md"


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def latest_per_post(rows: list[dict]) -> dict[str, dict]:
    """Most recent snapshot for each post (metrics accumulate, so latest is the fullest)."""
    best: dict[str, dict] = {}
    for r in rows:
        if r["post_id"] not in best or r["snapshot"] > best[r["post_id"]]["snapshot"]:
            best[r["post_id"]] = r
    return best


def rate(n, d):
    return round(100 * n / d, 1) if d else None


def enrich(r: dict) -> dict:
    reach = r.get("reach") or 0
    inter = r.get("total_interactions")
    if inter is None:
        inter = sum((r.get(k) or 0) for k in ("likes", "comments", "saved", "shares", "replies"))
    return {**r, "reach": reach, "interactions": inter, "views": r.get("views") or r.get("plays") or r.get("impressions"),
            "eng_rate": rate(inter, reach), "save_rate": rate(r.get("saved") or 0, reach), "share_rate": rate(r.get("shares") or 0, reach)}


def median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def build() -> str:
    rows = [enrich(r) for r in latest_per_post(load(METRICS)).values()]
    acct = load(ACCOUNT)
    today = date.today()
    L = [f"# Social review — {today.isoformat()}", ""]

    # ── account trend ────────────────────────────────────────────────────────
    if acct:
        by_day = {a["date"]: a for a in acct}
        days = sorted(by_day)
        cur = by_day[days[-1]]
        L += [f"**Followers:** {cur.get('followers')}"]
        if len(days) >= 2:
            prev = by_day[days[-2]]
            d1 = (cur.get("followers") or 0) - (prev.get("followers") or 0)
            L[-1] += f" ({'+' if d1 >= 0 else ''}{d1} since yesterday)"
        wk = [d for d in days if d >= (today - timedelta(days=7)).isoformat()]
        prior = [d for d in days if (today - timedelta(days=14)).isoformat() <= d < (today - timedelta(days=7)).isoformat()]
        if wk and prior:
            g1 = (by_day[wk[-1]].get("followers") or 0) - (by_day[wk[0]].get("followers") or 0)
            g0 = (by_day[prior[-1]].get("followers") or 0) - (by_day[prior[0]].get("followers") or 0)
            L.append(f"**Follower growth:** +{g1} this week vs +{g0} the week before.")
        L.append("")

    errors = [r for r in rows if r.get("error")]
    rows = [r for r in rows if r.get("reach") is not None]
    if not rows:
        if errors and "permission" in errors[0]["error"].lower():
            L += ["Post insights are not readable yet: the Meta token needs the `instagram_manage_insights` permission. Regenerate it in Business Settings → System users, replace the `META_TOKEN` secret, and this fills in the next morning.", ""]
        else:
            L += ["No post metrics yet. The first snapshot lands the morning after the first post.", ""]
        OUT.write_text("\n".join(L), encoding="utf-8")
        return "\n".join(L)

    # ── trend verdict: this week's posts vs last week's, on median engagement rate and save rate ──
    feed = [r for r in rows if r["surface"] == "feed" and r["reach"]]
    this_wk = [r for r in feed if r["scheduled_for"] >= (today - timedelta(days=7)).isoformat()]
    last_wk = [r for r in feed if (today - timedelta(days=14)).isoformat() <= r["scheduled_for"] < (today - timedelta(days=7)).isoformat()]
    verdict = "Not enough history for a trend yet (need two weeks of posts with reach)."
    if this_wk and last_wk:
        a, b = median([r["eng_rate"] for r in this_wk]), median([r["eng_rate"] for r in last_wk])
        ra, rb = median([r["reach"] for r in this_wk]), median([r["reach"] for r in last_wk])
        sa, sb = median([r["save_rate"] for r in this_wk]), median([r["save_rate"] for r in last_wk])
        def arrow(x, y):
            if x is None or y is None: return "flat"
            return "up" if x > y * 1.1 else ("down" if x < y * 0.9 else "flat")
        verdict = (f"**Trend: reach {arrow(ra, rb)}** ({rb} → {ra} median per post), **engagement {arrow(a, b)}** ({b}% → {a}%), "
                   f"**saves {arrow(sa, sb)}** ({sb}% → {sa}%).")
    L += ["## Verdict", verdict, ""]

    # ── benchmarks ───────────────────────────────────────────────────────────
    L += ["## Benchmarks (Instagram 2026: carousels ≈ 0.5% of followers, ≈ 5–7% of reach; saves are the strongest signal)", ""]
    L += [f"Median per feed post: reach {median([r['reach'] for r in feed])}, engagement {median([r['eng_rate'] for r in feed])}% of reach, saves {median([r['save_rate'] for r in feed])}% of reach.", ""]

    # ── by format / theme / topic ────────────────────────────────────────────
    def group(key, label):
        g = defaultdict(list)
        for r in rows:
            if r["reach"]:
                g[r.get(key) or "-"].append(r)
        if len(g) < 2:
            return
        L.append(f"## By {label}")
        L.append("| " + label + " | posts | median reach | eng % | save % |")
        L.append("|---|---:|---:|---:|---:|")
        for k, rs in sorted(g.items(), key=lambda kv: -(median([r['eng_rate'] for r in kv[1]]) or 0)):
            L.append(f"| {k} | {len(rs)} | {median([r['reach'] for r in rs])} | {median([r['eng_rate'] for r in rs])} | {median([r['save_rate'] for r in rs])} |")
        L.append("")
    group("kind", "format")
    group("subkind", "one-pager type")
    group("theme", "theme")
    group("topic", "topic")

    # ── best and worst ───────────────────────────────────────────────────────
    ranked = sorted(feed, key=lambda r: (r["save_rate"] or 0, r["eng_rate"] or 0), reverse=True)
    if ranked:
        L += ["## Top posts (by save rate, then engagement)", ""]
        for r in ranked[:5]:
            L.append(f"- **{r['title']}** ({r['kind']}, {r['scheduled_for']}): reach {r['reach']}, saves {r.get('saved') or 0}, shares {r.get('shares') or 0}, eng {r['eng_rate']}%")
        L += ["", "## Weakest posts", ""]
        for r in ranked[-3:]:
            L.append(f"- {r['title']} ({r['kind']}, {r['scheduled_for']}): reach {r['reach']}, eng {r['eng_rate']}%")
        L.append("")

    # ── what to do next ──────────────────────────────────────────────────────
    L += ["## What to do with this", ""]
    if ranked:
        top_topics = defaultdict(list)
        for r in ranked[:5]:
            top_topics[r.get("topic")].append(r)
        L.append(f"- Lean into: {', '.join(k for k in top_topics if k)}. Write the next batch's carousels from these angles first.")
        low = [r for r in ranked if (r['reach'] or 0) < 0.5 * (median([x['reach'] for x in feed]) or 1)]
        if low:
            L.append(f"- {len(low)} post(s) reached under half the median. Check the hook slide first; the cover is 80% of the swipe.")
    L.append("- Saves and shares outrank likes. A post with few likes but a high save rate is a win; repeat its format.")
    L.append("- Read this before writing the next batch (prompts/social-carousels.md tells the generator to).")
    text = "\n".join(L)
    OUT.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    print(build())
