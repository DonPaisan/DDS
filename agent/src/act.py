"""The ONLY file that writes to the Meta ad account. Two verbs: pause, set_budget.

Never call this from a model prompt. rules.py calls execute() after its own checks.

  python src/act.py pause <adset_id> --dry-run
  python src/act.py set_budget <adset_id> <daily_budget_cents> --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys

import requests

from common import env, load_config, load_env, log_action


def _post(path: str, data: dict) -> dict:
    load_env()
    token = env("META_TOKEN", required=True)
    version = env("META_API_VERSION", "v26.0")
    r = requests.post(f"https://graph.facebook.com/{version}/{path}", data={**data, "access_token": token}, timeout=60)
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"Meta write failed: {body['error']}")
    return body


def pause_adset(adset_id: str, dry_run: bool = True) -> dict:
    if dry_run:
        return {"dry_run": True, "would": f"POST /{adset_id} status=PAUSED"}
    return _post(adset_id, {"status": "PAUSED"})


def set_budget(adset_id: str, daily_budget_cents: int, dry_run: bool = True) -> dict:
    R = load_config()["rules"]
    lo, hi = R["budget_floor_usd"] * 100, R["budget_ceiling_usd"] * 100
    if not (lo <= daily_budget_cents <= hi):
        raise ValueError(f"budget {daily_budget_cents} outside hard bounds {lo}–{hi} cents")
    if dry_run:
        return {"dry_run": True, "would": f"POST /{adset_id} daily_budget={daily_budget_cents}"}
    return _post(adset_id, {"daily_budget": daily_budget_cents})


def execute(action: dict, dry_run: bool = True) -> dict:
    if action["action"] == "pause":
        return pause_adset(action["adset_id"], dry_run)
    if action["action"] == "set_budget":
        return set_budget(action["adset_id"], int(action["new_budget_cents"]), dry_run)
    raise ValueError(f"unknown action {action['action']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["pause", "set_budget"])
    ap.add_argument("adset_id")
    ap.add_argument("cents", nargs="?", type=int)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--really", action="store_true", help="actually write (overrides --dry-run)")
    args = ap.parse_args(argv)
    dry = not args.really
    if not dry and not load_config()["rules"]["enabled"]:
        sys.exit("[act] rules.enabled is false in config.yml; refusing to write.")
    action = {"action": args.verb, "adset_id": args.adset_id, "new_budget_cents": args.cents, "rule": "manual"}
    res = execute(action, dry_run=dry)
    log_action({"mode": "DRY-RUN" if dry else "APPLY", **action, "result": res})
    print(json.dumps(res))


if __name__ == "__main__":
    main()
