import sqlite3
from datetime import date, timedelta

import common
from rules import evaluate


def make_db(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "DB_PATH", tmp_path / "t.sqlite")
    conn = common.db()
    return conn


def seed(conn, adset, spend_per_day, leads_per_day, days=7, budget=5000, status="ACTIVE"):
    for i in range(days):
        d = (date.today() - timedelta(days=i)).isoformat()
        conn.execute("INSERT INTO ad_daily (day, ad_id, adset_id, adset_name, spend, leads, link_clicks, fetched_at) VALUES (?,?,?,?,?,?,?,?)",
                     (d, f"ad-{adset}-{i}", adset, adset, spend_per_day, leads_per_day, 10, "now"))
    conn.execute("INSERT OR REPLACE INTO adset_status VALUES (?,?,?,?,?)", (adset, adset, status, budget, "now"))
    conn.commit()


def cfg(**over):
    c = common.load_config()
    c["rules"].update(over)
    return c


def test_no_data_no_actions(tmp_path, monkeypatch):
    conn = make_db(tmp_path, monkeypatch)
    assert evaluate(conn, cfg()) == []


def test_runaway_pauses_zero_lead_spender(tmp_path, monkeypatch):
    conn = make_db(tmp_path, monkeypatch)
    seed(conn, "dead", spend_per_day=80, leads_per_day=0)
    seed(conn, "ok", spend_per_day=40, leads_per_day=10)
    acts = evaluate(conn, cfg())
    assert [(a["action"], a["adset_id"], a["rule"]) for a in acts] == [("pause", "dead", "spend_runaway")]


def test_min_evidence_blocks_kill(tmp_path, monkeypatch):
    conn = make_db(tmp_path, monkeypatch)
    seed(conn, "pricey", spend_per_day=100, leads_per_day=2)   # 14 leads < 50, CPL $50
    seed(conn, "cheap", spend_per_day=100, leads_per_day=20)   # CPL $5
    assert evaluate(conn, cfg()) == []


def test_kill_loser_with_enough_evidence(tmp_path, monkeypatch):
    conn = make_db(tmp_path, monkeypatch)
    seed(conn, "pricey", spend_per_day=200, leads_per_day=8)   # 56 leads, CPL $25
    seed(conn, "cheap", spend_per_day=100, leads_per_day=20)   # 140 leads, CPL $5 ; acct avg ≈ $10.7
    acts = evaluate(conn, cfg())
    assert [(a["action"], a["adset_id"]) for a in acts] == [("pause", "pricey")]


def test_scale_only_when_not_safety_only_and_clamped(tmp_path, monkeypatch):
    conn = make_db(tmp_path, monkeypatch)
    seed(conn, "pricey", spend_per_day=200, leads_per_day=8, budget=5000)
    seed(conn, "cheap", spend_per_day=100, leads_per_day=20, budget=19000)
    assert not any(a["action"] == "set_budget" for a in evaluate(conn, cfg(safety_only=True)))
    acts = [a for a in evaluate(conn, cfg(safety_only=False)) if a["action"] == "set_budget"]
    assert len(acts) == 1 and acts[0]["adset_id"] == "cheap"
    assert acts[0]["new_budget_cents"] == 20000  # 19000*1.2 = 22800 → clamped to $200


def test_account_kill_switch(tmp_path, monkeypatch):
    conn = make_db(tmp_path, monkeypatch)
    seed(conn, "a", spend_per_day=300, leads_per_day=5)
    seed(conn, "b", spend_per_day=300, leads_per_day=5)
    acts = evaluate(conn, cfg(account_daily_spend_kill_usd=500))
    assert {a["adset_id"] for a in acts} == {"a", "b"} and all(a["rule"] == "account_kill_switch" for a in acts)
