"""Ad management for the Meta ad account: videos, creatives, ads, ad set settings.

This is the file Claude uses to build and tune ads from funnel data. What it can do:
upload videos, write creatives (primary text, headline, CTA, tracked landing URL),
create ads (always PAUSED), change ad set optimization / placements / attribution,
pause or activate ads and ad sets.

What it can NEVER do, enforced in code, not by convention:
  • touch any budget, bid, or spend-cap field (BUDGET_FIELDS below)
  • set targeting that the Financial Products / Credit Special Ad Category forbids
  • publish copy that fails the compliance gate (guards.check_copy)

Every write is logged to logs/actions.jsonl with its reason. Dry run unless --really.

  python src/ads.py list
  python src/ads.py upload-video path/or/url --name "hook-3-medical"
  python src/ads.py create-creative --video-id V --page-id P --ig-id I \\
      --primary "..." --headline "..." --link https://www.debtdirectsolutions.com --name "hook-3" --reason "..."
  python src/ads.py create-ad --adset-id A --creative-id C --name "hook-3 / feed" --reason "..."
  python src/ads.py update-adset A --optimize leads|survey_starts|landing_page_views \\
      --placements auto|feeds|reels|feeds+reels --reason "..."
  python src/ads.py set-status ad|adset ID PAUSED|ACTIVE --reason "..."
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

from common import REPO_DIR, env, load_config, load_env, log_action

# ── hard guardrails ─────────────────────────────────────────────────────────
BUDGET_FIELDS = {"daily_budget", "lifetime_budget", "bid_amount", "spend_cap", "daily_min_spend_target",
                 "daily_spend_cap", "lifetime_min_spend_target", "lifetime_spend_cap", "budget_remaining", "adset_budget_value"}

# Targeting keys the Credit / Financial Products Special Ad Category forbids or that we never use.
FORBIDDEN_TARGETING = {"genders", "custom_audiences", "excluded_custom_audiences", "zips", "interests", "behaviors",
                       "life_events", "income", "education_statuses", "relationship_statuses", "home_ownership", "excluded_geo_locations"}

# Copy that gets a debt-relief ad rejected: claims, guarantees, and asserting the viewer's situation.
BANNED_CLAIMS = re.compile(
    r"\b(guarantee[ds]?|eliminate|erase|wipe out|government program|irs|stimulus|debt[- ]free in)\b"
    r"|\b(save|saving|saved|reduce[sd]?|reduction|cut|lower(ed|ing)?|settle[sd]?|settling|forgive[ns]?|forgiven|pay(ing)? (only|just))\b[^.%\n]{0,40}\d{1,3}\s?%"
    r"|\d{1,3}\s?%[^.%\n]{0,15}\b(off|less|savings?|reduction|settlement)\b", re.I)
PERSONAL_ATTRIBUTES = re.compile(
    r"\b(struggling with|drowning in|buried in|behind on|can't (keep up|afford)|your bad credit|are you in debt|"
    r"if you('re| are) (in debt|behind|struggling)|we (understand|know) (your|how)|for people (with|who))\b", re.I)


class GuardError(ValueError):
    pass


def check_copy(*texts: str) -> None:
    for t in texts:
        if not t:
            continue
        m = BANNED_CLAIMS.search(t)
        if m:
            raise GuardError(f"copy fails compliance (claim): '{m.group(0)}' in: {t[:80]}")
        m = PERSONAL_ATTRIBUTES.search(t)
        if m:
            raise GuardError(f"copy asserts the viewer's situation (Meta personal-attributes policy): '{m.group(0)}' in: {t[:80]}")


def check_no_budget(fields: dict) -> None:
    bad = BUDGET_FIELDS & set(fields)
    if bad:
        raise GuardError(f"refusing to change money fields {sorted(bad)}; budgets are set by a human in Ads Manager")


def check_targeting(targeting: dict) -> None:
    bad = FORBIDDEN_TARGETING & set(targeting)
    if bad:
        raise GuardError(f"targeting keys not allowed under the Special Ad Category: {sorted(bad)}")
    if targeting.get("age_min", 18) != 18 or targeting.get("age_max", 65) != 65:
        raise GuardError("age must stay 18–65+ under the Special Ad Category")


# ── graph api ───────────────────────────────────────────────────────────────
def _version() -> str:
    return env("META_API_VERSION", "v26.0")


def _account() -> str:
    return env("META_AD_ACCOUNT_ID") or load_config()["meta"].get("ad_account_id") or sys.exit("[ads] set META_AD_ACCOUNT_ID")


def graph(method: str, path: str, *, params: dict | None = None, data: dict | None = None, files=None, timeout=120) -> dict:
    load_env()
    token = env("META_TOKEN", required=True)
    url = f"https://graph.facebook.com/{_version()}/{path}"
    r = requests.request(method, url, params={**(params or {}), "access_token": token}, data=data, files=files, timeout=timeout)
    try:
        body = r.json()
    except ValueError:
        raise RuntimeError(f"non-JSON {r.status_code}: {r.text[:300]}")
    if "error" in body:
        e = body["error"]
        hint = " — TOKEN INVALID, regenerate it" if e.get("code") == 190 else ""
        raise RuntimeError(f"Meta API error {e.get('code')} ({e.get('error_subcode')}): {e.get('message')} {e.get('error_user_msg', '')}{hint}")
    return body


def _write(method, path, *, data, reason, dry_run, kind):
    entry = {"mode": "DRY-RUN" if dry_run else "APPLY", "action": kind, "path": path, "data": data, "reason": reason}
    if dry_run:
        print(f"[ads:DRY-RUN] {method} /{path} {json.dumps(data)[:300]}")
        log_action(entry)
        return {"dry_run": True}
    res = graph(method, path, data=data)
    entry["result"] = res
    log_action(entry)
    print(f"[ads:APPLY] {kind} → {json.dumps(res)[:200]}")
    return res


# ── read ────────────────────────────────────────────────────────────────────
def list_all() -> dict:
    acct = _account()
    out = {
        "campaigns": graph("GET", f"{acct}/campaigns", params={"fields": "id,name,status,effective_status,objective,special_ad_categories,daily_budget", "limit": 100}).get("data", []),
        "adsets": graph("GET", f"{acct}/adsets", params={"fields": "id,name,campaign_id,status,effective_status,optimization_goal,billing_event,bid_strategy,promoted_object,attribution_spec,targeting,daily_budget", "limit": 200}).get("data", []),
        "ads": graph("GET", f"{acct}/ads", params={"fields": "id,name,adset_id,status,effective_status,creative{id,name,object_story_spec,url_tags},issues_info", "limit": 500}).get("data", []),
        "videos": graph("GET", f"{acct}/advideos", params={"fields": "id,title,length,status,created_time", "limit": 100}).get("data", []),
    }
    return out


# ── videos ──────────────────────────────────────────────────────────────────
CHUNK = 8 * 1024 * 1024


def upload_video(source: str, name: str, reason: str, dry_run: bool) -> dict:
    """Upload from a public URL or a local file (chunked for large files)."""
    acct = _account()
    if source.startswith("http"):
        return _write("POST", f"{acct}/advideos", data={"file_url": source, "title": name, "name": name}, reason=reason, dry_run=dry_run, kind="upload_video")
    p = Path(source)
    if not p.exists():
        raise FileNotFoundError(source)
    size = p.stat().st_size
    if dry_run:
        print(f"[ads:DRY-RUN] would upload {p.name} ({size / 1e6:.1f} MB) as '{name}'")
        return {"dry_run": True}
    if size <= 50 * 1024 * 1024:
        with open(p, "rb") as f:
            res = graph("POST", f"{acct}/advideos", data={"title": name, "name": name}, files={"source": (p.name, f, "video/mp4")}, timeout=600)
    else:
        start = graph("POST", f"{acct}/advideos", data={"upload_phase": "start", "file_size": size})
        session, off, end = start["upload_session_id"], int(start["start_offset"]), int(start["end_offset"])
        with open(p, "rb") as f:
            while off < size:
                f.seek(off)
                chunk = f.read(end - off)
                r = graph("POST", f"{acct}/advideos", data={"upload_phase": "transfer", "upload_session_id": session, "start_offset": off},
                          files={"video_file_chunk": (p.name, chunk, "video/mp4")}, timeout=600)
                off, end = int(r["start_offset"]), int(r["end_offset"])
        res = graph("POST", f"{acct}/advideos", data={"upload_phase": "finish", "upload_session_id": session, "title": name, "name": name})
        res = {"id": start["video_id"], **res}
    log_action({"mode": "APPLY", "action": "upload_video", "file": p.name, "size": size, "result": res, "reason": reason})
    print(f"[ads:APPLY] uploaded {p.name} → video {res.get('id')}")
    return res


def video_thumbnail(video_id: str) -> str | None:
    thumbs = graph("GET", f"{video_id}/thumbnails", params={"fields": "uri,is_preferred"}).get("data", [])
    if not thumbs:
        return None
    pref = [t for t in thumbs if t.get("is_preferred")]
    return (pref or thumbs)[0]["uri"]


# ── creatives + ads ─────────────────────────────────────────────────────────
DEFAULT_URL_TAGS = ("utm_source={{site_source_name}}&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}"
                    "&utm_term={{adset.name}}&ad_id={{ad.id}}&adset_id={{adset.id}}&campaign_id={{campaign.id}}&placement={{placement}}")


def create_creative(*, video_id: str, page_id: str, ig_id: str | None, primary: str, headline: str, description: str | None,
                    link: str, name: str, cta: str, reason: str, dry_run: bool) -> dict:
    check_copy(primary, headline, description or "")
    thumb = None if dry_run else video_thumbnail(video_id)
    spec = {
        "page_id": page_id,
        "video_data": {
            "video_id": video_id,
            "message": primary,
            "title": headline,
            "link_description": description or "",
            "call_to_action": {"type": cta, "value": {"link": link}},
            **({"image_url": thumb} if thumb else {}),
        },
    }
    if ig_id:
        spec["instagram_user_id"] = ig_id
    data = {"name": name, "object_story_spec": json.dumps(spec), "url_tags": DEFAULT_URL_TAGS}
    return _write("POST", f"{_account()}/adcreatives", data=data, reason=reason, dry_run=dry_run, kind="create_creative")


def create_ad(*, adset_id: str, creative_id: str, name: str, reason: str, dry_run: bool) -> dict:
    cfg = load_config().get("ads", {})
    status = "ACTIVE" if cfg.get("auto_activate") else "PAUSED"
    data = {"name": name, "adset_id": adset_id, "creative": json.dumps({"creative_id": creative_id}), "status": status}
    return _write("POST", f"{_account()}/ads", data=data, reason=reason, dry_run=dry_run, kind="create_ad")


# ── ad set settings (never money) ───────────────────────────────────────────
OPTIMIZE = {
    "leads":               {"optimization_goal": "OFFSITE_CONVERSIONS", "custom_event_type": "LEAD"},
    "survey_starts":       {"optimization_goal": "OFFSITE_CONVERSIONS", "custom_event_type": "CONTENT_VIEW"},
    "landing_page_views":  {"optimization_goal": "LANDING_PAGE_VIEWS"},
    "link_clicks":         {"optimization_goal": "LINK_CLICKS"},
}
PLACEMENTS = {
    "auto": None,
    "feeds":       {"publisher_platforms": ["facebook", "instagram"], "facebook_positions": ["feed", "marketplace", "video_feeds"], "instagram_positions": ["stream", "explore"]},
    "reels":       {"publisher_platforms": ["facebook", "instagram"], "facebook_positions": ["facebook_reels"], "instagram_positions": ["reels"]},
    "feeds+reels": {"publisher_platforms": ["facebook", "instagram"], "facebook_positions": ["feed", "video_feeds", "facebook_reels"], "instagram_positions": ["stream", "explore", "reels"]},
    "stories":     {"publisher_platforms": ["facebook", "instagram"], "facebook_positions": ["story", "facebook_reels"], "instagram_positions": ["story", "reels"]},
}


def update_adset(adset_id: str, *, optimize: str | None, placements: str | None, attribution: str | None, pixel_id: str | None,
                 reason: str, dry_run: bool) -> dict:
    data: dict = {}
    if optimize:
        o = OPTIMIZE[optimize]
        data["optimization_goal"] = o["optimization_goal"]
        data["billing_event"] = "IMPRESSIONS"
        if "custom_event_type" in o:
            pid = pixel_id or env("META_PIXEL_ID") or sys.exit("[ads] --pixel-id or META_PIXEL_ID required for conversion optimization")
            data["promoted_object"] = json.dumps({"pixel_id": pid, "custom_event_type": o["custom_event_type"]})
    if placements:
        current = graph("GET", adset_id, params={"fields": "targeting"})["targeting"] if not dry_run else {}
        t = {k: v for k, v in current.items() if k not in ("publisher_platforms", "facebook_positions", "instagram_positions", "messenger_positions", "audience_network_positions", "device_platforms")}
        if PLACEMENTS[placements]:
            t.update(PLACEMENTS[placements])
        check_targeting(t)
        data["targeting"] = json.dumps(t)
    if attribution:
        window = {"7d_click": [{"event_type": "CLICK_THROUGH", "window_days": 7}, {"event_type": "VIEW_THROUGH", "window_days": 1}],
                  "1d_click": [{"event_type": "CLICK_THROUGH", "window_days": 1}]}[attribution]
        data["attribution_spec"] = json.dumps(window)
    if not data:
        raise GuardError("nothing to change")
    check_no_budget(data)
    return _write("POST", adset_id, data=data, reason=reason, dry_run=dry_run, kind="update_adset")


def set_status(kind: str, object_id: str, status: str, reason: str, dry_run: bool) -> dict:
    if status not in ("PAUSED", "ACTIVE"):
        raise GuardError("status must be PAUSED or ACTIVE")
    return _write("POST", object_id, data={"status": status}, reason=reason, dry_run=dry_run, kind=f"set_{kind}_status")


# ── cli ─────────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--really", action="store_true", help="apply (default is dry run)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")
    p = sub.add_parser("upload-video"); p.add_argument("source"); p.add_argument("--name", required=True); p.add_argument("--reason", default="new creative")
    p = sub.add_parser("create-creative")
    for a in ("--video-id", "--page-id", "--primary", "--headline", "--link", "--name", "--reason"):
        p.add_argument(a, required=True)
    p.add_argument("--ig-id"); p.add_argument("--description"); p.add_argument("--cta", default="LEARN_MORE")
    p = sub.add_parser("create-ad")
    for a in ("--adset-id", "--creative-id", "--name", "--reason"):
        p.add_argument(a, required=True)
    p = sub.add_parser("update-adset"); p.add_argument("adset_id"); p.add_argument("--optimize", choices=list(OPTIMIZE)); p.add_argument("--placements", choices=list(PLACEMENTS))
    p.add_argument("--attribution", choices=["7d_click", "1d_click"]); p.add_argument("--pixel-id"); p.add_argument("--reason", required=True)
    p = sub.add_parser("set-status"); p.add_argument("kind", choices=["ad", "adset"]); p.add_argument("id"); p.add_argument("status"); p.add_argument("--reason", required=True)
    args = ap.parse_args(argv)

    load_env()
    cfg = load_config().get("ads", {})
    dry = not (args.really and cfg.get("enabled"))
    if args.really and not cfg.get("enabled"):
        print("[ads] ads.enabled is false in config.yml — dry run only.")

    try:
        if args.cmd == "list":
            print(json.dumps(list_all(), indent=2))
        elif args.cmd == "upload-video":
            upload_video(args.source, args.name, args.reason, dry)
        elif args.cmd == "create-creative":
            create_creative(video_id=args.video_id, page_id=args.page_id, ig_id=args.ig_id, primary=args.primary, headline=args.headline,
                            description=args.description, link=args.link, name=args.name, cta=args.cta, reason=args.reason, dry_run=dry)
        elif args.cmd == "create-ad":
            create_ad(adset_id=args.adset_id, creative_id=args.creative_id, name=args.name, reason=args.reason, dry_run=dry)
        elif args.cmd == "update-adset":
            update_adset(args.adset_id, optimize=args.optimize, placements=args.placements, attribution=args.attribution, pixel_id=args.pixel_id, reason=args.reason, dry_run=dry)
        elif args.cmd == "set-status":
            set_status(args.kind, args.id, args.status, args.reason, dry)
    except GuardError as e:
        sys.exit(f"[ads] BLOCKED: {e}")


if __name__ == "__main__":
    main()
