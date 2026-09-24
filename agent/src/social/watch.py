"""Compose the body of the standing 'Social reach watch' GitHub issue from review.md,
history.md and the latest snapshots, with an ALERT line when recent feed posts are at zero.

  python src/social/watch.py > body.md
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import AGENT_DIR  # noqa: E402

SOCIAL = AGENT_DIR / "social"


def main():
    now = datetime.now(timezone.utc)
    review = (SOCIAL / "review.md").read_text() if (SOCIAL / "review.md").exists() else ""
    history = (SOCIAL / "history.md").read_text() if (SOCIAL / "history.md").exists() else ""
    alerts = []
    hist = json.loads((SOCIAL / "history.json").read_text()) if (SOCIAL / "history.json").exists() else {}
    posts = hist.get("posts", [])
    recent = [p for p in posts if p["kind"] != "story" and (now - datetime.fromisoformat(p["date"] + "T00:00:00+00:00")).days >= 2][:3]
    if recent:
        readable = all("reach" in p for p in recent)
        if readable and all((p.get("reach") or 0) == 0 for p in recent):
            alerts.append("ALERT: the last three feed posts older than 48 hours have zero reach. Instagram is not showing them to anyone. Check Settings → Account status, and consider a small promotion to seed an audience.")
        elif not readable and all((p.get("likes") or 0) == 0 and (p.get("comments") or 0) == 0 for p in recent):
            alerts.append("Watch: the last three feed posts older than 48 hours have zero likes and comments. Reach itself is not readable until the Instagram account is assigned to the system user.")
    split = hist.get("reach_split_30d", {})
    if split and "error" not in split:
        nf = split.get("NON_FOLLOWER", 0)
        alerts.append(f"Non-follower reach, last 30 days: {nf}." + (" Zero non-follower reach means no discovery; Reels, collabs or promotion are the levers." if nf == 0 else ""))
    body = [f"_Updated {now.strftime('%Y-%m-%d %H:%M UTC')} by the daily metrics job. Do not edit; it is overwritten every morning._", ""]
    if alerts:
        body += ["## Alerts", ""] + [f"- {a}" for a in alerts] + [""]
    body += [review.strip(), "", "---", "", history.strip()]
    sys.stdout.write("\n".join(body) + "\n")


if __name__ == "__main__":
    main()
