import json

from funnel import diagnose, sessionize, summarize


def ev(type_, sid, **f):
    base = {"type": type_, "ts": f.pop("ts", "2026-09-20T10:00:00.000Z"), "event_id": f"{sid}-{type_}-{f.get('step', 0)}-{f.get('answer', '')}",
            "session_id": sid, "visitor_id": "v" + sid, "survey_version": "t1", "page": "/",
            "attr": {"utm_source": "facebook", "utm_campaign": "c1", "utm_content": f.pop("ad", "adA")},
            "ctx": {"device": f.pop("device", "mobile")}}
    base.update(f)
    return base


def session(sid, reach=0, done=0, lead=False, device="mobile", scroll=50, start=True, ad="adA"):
    out = [ev("page_view", sid, device=device, ad=ad, extra={"load_ms": 800}), ev("scroll_depth", sid, answer=scroll, device=device, ad=ad)]
    if start:
        out.append(ev("survey_start", sid, step=0, question_id="q0", device=device, ad=ad))
    for i in range(reach + 1):
        out.append(ev("step_view", sid, step=i, question_id=f"q{i}", device=device, ad=ad))
        if i < done:
            out.append(ev("step_complete", sid, step=i, question_id=f"q{i}", answer="a", ms=1000 + i, device=device, ad=ad))
    if lead:
        out += [ev("form_submit", sid, step=reach, device=device, ad=ad), ev("lead", sid, step=reach, device=device, ad=ad)]
    return out


def test_sessionize_tracks_last_step():
    s = sessionize(session("s1", reach=2, done=2))[0]
    assert s["last_step"] == 2 and len(s["steps_completed"]) == 2 and s["survey_start"] and not s["lead"]


def test_summarize_rates_and_abandonment():
    events = session("a", reach=4, done=5, lead=True) + session("b", reach=4, done=4) + session("c", reach=1, done=1) + session("d", start=False, scroll=0)
    s = summarize(events)
    assert s["sessions"] == 4 and s["survey_starts"] == 3 and s["leads"] == 1
    assert s["rates"]["start_rate"] == 75.0
    assert len(s["steps"]) == 5
    assert s["steps"][1]["viewed"] == 3 and s["steps"][1]["abandoned_here"] == 1
    assert s["steps"][4]["abandon_rate"] == 50.0
    assert s["no_start"]["never_scrolled_past_25"] == 1
    assert s["by_source"]["facebook / c1 / adA"]["sessions"] == 4
    assert s["steps"][0]["median_ms"] == 1000


def test_diagnose_low_volume():
    assert diagnose(summarize(session("a")))[0]["code"] == "low_volume"


def test_diagnose_contact_dropoff_and_click_gap():
    events = []
    for i in range(40):
        events += session(f"s{i}", reach=4, done=4, lead=i < 10)
    codes = {f["code"] for f in diagnose(summarize(events), link_clicks=200)}
    assert "contact_step_dropoff" in codes and "click_to_view_gap" in codes


def test_diagnose_bounce_above_fold():
    events = []
    for i in range(40):
        events += session(f"s{i}", start=i < 5, scroll=50 if i < 5 else 0, reach=0, done=1 if i < 5 else 0)
    assert "bounce_above_fold" in {f["code"] for f in diagnose(summarize(events))}


def test_python_matches_js_on_real_events(tmp_path):
    """The JS and Python implementations must agree on the same event log."""
    import subprocess
    from pathlib import Path
    repo = Path(__file__).resolve().parents[2]
    log = repo / ".local" / "events.jsonl"
    if not log.exists():
        import pytest
        pytest.skip("no .local/events.jsonl from a browser run")
    events = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    py = summarize(events)
    js = json.loads(subprocess.check_output(["node", "-e", f"""
      import('{(repo / 'netlify/lib/funnel.js').as_posix()}').then(m => {{
        const fs = require('fs');
        const ev = fs.readFileSync('{log.as_posix()}','utf8').split('\\n').filter(Boolean).map(JSON.parse);
        console.log(JSON.stringify(m.summarize(ev)));
      }})"""], cwd=repo))
    for k in ("sessions", "survey_starts", "form_submits", "leads"):
        assert py[k] == js[k], k
    assert [(s["viewed"], s["completed"], s["abandoned_here"]) for s in py["steps"]] == [(s["viewed"], s["completed"], s["abandoned_here"]) for s in js["steps"]]
    assert py["rates"] == js["rates"]
