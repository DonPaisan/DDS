"""Shared helpers: env, config, sqlite, http, logging of actions."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

AGENT_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = AGENT_DIR.parent
DATA_DIR = AGENT_DIR / "data"
LOGS_DIR = AGENT_DIR / "logs"
REPORTS_DIR = AGENT_DIR / "reports"
DB_PATH = DATA_DIR / "ads.sqlite"

for d in (DATA_DIR, LOGS_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def load_env() -> None:
    """Load agent/.env if present (without overriding real env vars)."""
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(AGENT_DIR / ".env", override=False)
    except Exception:
        pass


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    v = os.environ.get(name, default)
    if required and not v:
        sys.exit(f"[config] {name} is not set. Add it to agent/.env or the environment.")
    return v


def load_config() -> dict:
    with open(AGENT_DIR / "config.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def today() -> date:
    return datetime.now(timezone.utc).date()


def days_ago(n: int) -> date:
    return today() - timedelta(days=n)


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ad_daily (
          day TEXT NOT NULL, ad_id TEXT NOT NULL, ad_name TEXT, adset_id TEXT, adset_name TEXT,
          campaign_id TEXT, campaign_name TEXT,
          spend REAL DEFAULT 0, impressions INTEGER DEFAULT 0, reach INTEGER DEFAULT 0,
          clicks INTEGER DEFAULT 0, link_clicks INTEGER DEFAULT 0, landing_page_views INTEGER DEFAULT 0,
          leads INTEGER DEFAULT 0, ctr REAL, cpc REAL, cpm REAL, frequency REAL,
          fetched_at TEXT NOT NULL,
          PRIMARY KEY (day, ad_id)
        );
        CREATE TABLE IF NOT EXISTS adset_status (
          adset_id TEXT PRIMARY KEY, name TEXT, status TEXT, daily_budget_cents INTEGER, fetched_at TEXT
        );
        CREATE TABLE IF NOT EXISTS funnel_events (
          event_id TEXT PRIMARY KEY, ts TEXT NOT NULL, day TEXT NOT NULL, type TEXT NOT NULL,
          session_id TEXT, visitor_id TEXT, step INTEGER, question_id TEXT, answer TEXT, ms INTEGER,
          survey_version TEXT, device TEXT, utm_source TEXT, utm_campaign TEXT, utm_content TEXT, utm_term TEXT,
          ad_id TEXT, adset_id TEXT, fbclid TEXT, extra TEXT, raw TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_funnel_day ON funnel_events(day);
        CREATE INDEX IF NOT EXISTS idx_funnel_session ON funnel_events(session_id);
        CREATE TABLE IF NOT EXISTS budget_changes (
          id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT, adset_id TEXT, old_cents INTEGER, new_cents INTEGER, at TEXT
        );
        """
    )
    return conn


def log_action(action: dict) -> None:
    """Append-only audit log. Every decision, with its reasoning, forever."""
    action = {"at": datetime.now(timezone.utc).isoformat(), **action}
    with open(LOGS_DIR / "actions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(action, ensure_ascii=False) + "\n")


def fmt_money(v: float | None) -> str:
    return "-" if v is None else f"${v:,.2f}"


def pct(n: float, d: float) -> float | None:
    return round(n / d * 100, 1) if d else None
