# Debt Direct Solutions — landing page, funnel tracking, and ads automation

Everything needed to answer one question: **people click the ad, land on the page, and don't fill
out the form — where exactly do they leave, and why?** Plus the tooling to act on the answer.

```
site/                      the landing page (static, no build step)
  index.html               hero + 5-step survey card
  survey.config.js         questions/wording/order — the file the optimization loop edits
  compliance.js            consent + disclosures — LOCKED, humans only
  tracker.js               fires one event per funnel action + mirrors to Meta Pixel
  app.js                   survey renderer, validation, submission
  funnel.html              private dashboard: drop-off by step, by ad, by device
netlify/functions/
  track.js                 POST /api/track  → stores events (Netlify Blobs) + Meta CAPI
  lead.js                  POST /api/lead   → stores lead, CAPI "Lead", webhook, email
  report.js                GET  /api/report → events / leads / funnel summary (token-protected)
agent/                     Python: Meta insights, funnel diagnosis, daily digest, rules engine, social
prompts/                   standing instructions for the scheduled Claude jobs
.github/workflows/         daily digest, tests, weekly social content
```

## What gets tracked

Every visitor gets a session id. Every action fires an event with the session id, the ad that
brought them (`utm_*`, `fbclid`, `ad_id`…), device, and timing:

| Event | Fires when | Tells you |
|---|---|---|
| `page_view` | page loads (with load time) | clicks that actually became visits; slow loads |
| `scroll_depth` | 25/50/75/100% | did they even see the form |
| `cta_click` | hero button tapped | |
| `survey_start` | first answer | how many engage at all |
| `step_view` / `step_complete` | each question, with ms on step | **exactly which question loses people** |
| `step_back` | back button | confusing question |
| `field_focus` / `field_error` | contact fields | which field causes friction |
| `form_submit` → `lead` | submit attempt → saved | broken endpoint shows up as a gap here |
| `page_hidden` | tab closed / backgrounded | last step seen = where they abandoned |
| `js_error` | any script error | broken page for some browsers |

`page_view`, `survey_start`, `form_submit` and `lead` are also sent to Meta (browser pixel and
server-side Conversions API, deduplicated by event id) so Meta can optimize toward people who
start the survey even before you have many leads.

## Setup (once)

### 1. Deploy on Netlify
- New site from this repo. Build settings come from `netlify.toml` (publish `site/`, functions
  `netlify/functions`). No build command needed.
- Point `debtdirectsolutions.com` at it once the domain is renewed.

### 2. Environment variables (Netlify → Site configuration → Environment variables)

| Variable | Required | What |
|---|---|---|
| `REPORT_TOKEN` | yes | long random string; protects `/api/report` and the dashboard |
| `META_PIXEL_ID` | for CAPI | your pixel id |
| `META_CAPI_TOKEN` | for CAPI | Events Manager → your pixel → Settings → Conversions API → Generate access token |
| `META_TEST_EVENT_CODE` | while testing | from Events Manager → Test events; remove when live |
| `LEAD_WEBHOOK_URL` | optional | forward every lead as JSON (GoHighLevel, Zapier, Make, a CRM) |
| `LEAD_WEBHOOK_SECRET` | optional | sent as `x-webhook-secret` |
| `RESEND_API_KEY`, `LEAD_NOTIFY_TO`, `LEAD_NOTIFY_FROM` | optional | email each lead to you |

Then set `metaPixelId` in `site/config.js` (public, not a secret) and commit.

### 3. Point the ads at the page with tracking parameters
In Ads Manager → ad → Tracking → URL parameters, paste:

```
utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}&utm_term={{adset.name}}&ad_id={{ad.id}}&adset_id={{adset.id}}&campaign_id={{campaign.id}}&placement={{placement}}
```

That is what makes "which ad brings people who actually fill the form" answerable.

### 4. Watch it
- Dashboard: `https://<your-site>/funnel.html` → paste the report token.
- Raw: `GET /api/report?from=2026-09-01&to=2026-09-07` with `Authorization: Bearer <token>`
  (`&type=events` for raw events, `&type=leads` for leads, `&full=1` to include contact details).

### 5. Daily digest by email (GitHub Actions)
Add repository secrets: `SITE_URL`, `REPORT_TOKEN`, `META_TOKEN`, and optionally `RESEND_API_KEY`, `DIGEST_TO`, `DIGEST_FROM`. The workflow in
`.github/workflows/daily-digest.yml` runs at 7:00 ET and emails spend, CPL, the funnel, and what the
rules engine *would* have done. Nothing writes to the ad account from CI.

Meta token: developers.facebook.com → app with Marketing API → Business Settings → System Users →
add user (Admin) → assign the app and the ad account with *Manage campaigns* → generate token
with `ads_management` and `ads_read`, expiration *Never*.

## Running things locally

```bash
npm install && npm test                       # funnel math tests
node scripts/serve.mjs                        # http://localhost:8787 — click through the survey,
                                              #   events land in .local/events.jsonl, dashboard at /funnel.html (any token)
cd agent && pip install -r requirements.txt
cp .env.example .env                          # fill in
python -m pytest tests
python src/fetch_meta.py --days 28            # Meta insights → data/ads.sqlite
python src/fetch_funnel.py --days 28          # site events → data/ads.sqlite
python src/funnel.py --days 7                 # drop-off by step/ad/device + plain-English findings
python src/digest.py                          # the daily report
python src/rules.py                           # DRY RUN: what the rules would do
```

## The rules engine

`agent/src/rules.py` reads sqlite and proposes actions. **Nothing is executed** unless
`rules.enabled: true` in `agent/config.yml` *and* you pass `--apply-safety-only` (pause rules) or
`--apply` (also budget scaling, only when `safety_only: false`). Every decision, dry-run or
real, is appended to `agent/logs/actions.jsonl` with the reason.

`.github/workflows/ads-rules.yml` runs the engine every morning. It is a dry run until you
flip the switch, so the safe rollout is:

1. Read the "What the rules engine would do" section of the digest for two weeks.
2. Disagree with a call? Change the threshold in `agent/config.yml`, not the code.
3. Set `rules.enabled: true` → pause rules go live (runaway spend, clear losers, account kill switch).
4. Set `rules.safety_only: false` → budget scaling goes live, +20% steps clamped to $20–$200/day.

The Meta token needs `ads_management` for steps 3 and 4; `ads_read` alone is enough for 1 and 2.
Creative and survey copy changes never run automatically: they arrive as a PR for you to merge.

## Ad management (creatives and settings, never money)

`agent/src/ads.py` is how Claude builds and tunes ads from the funnel data: upload videos, write
primary text and headlines, create ads (always paused), and change an ad set's optimization
event, placements, or attribution window. It refuses any budget or bid field in code, rejects
targeting the Special Ad Category forbids, and runs every line of copy through the same
compliance gate as the page. Dry run until `ads.enabled: true` in `agent/config.yml`.

```bash
cd agent
python src/ads.py list
python src/ads.py upload-video hook-3.mp4 --name "hook-3 medical bills"
python src/ads.py create-creative --video-id V --page-id P --ig-id I --primary "..." --headline "..." \
    --link https://www.debtdirectsolutions.com --name "hook-3" --reason "..."
python src/ads.py create-ad --adset-id A --creative-id C --name "hook-3 / feeds" --reason "..."
python src/ads.py update-adset A --optimize survey_starts --placements feeds+reels --reason "..."
python src/ads.py --really set-status ad AD_ID ACTIVE --reason "approved by Brendon"
```

Tracking parameters are attached at the creative level (`url_tags`), so every ad built this way
reports into the dashboard by ad name automatically.

## Survey optimization loop

1. `funnel.py` shows which step loses people.
2. `prompts/survey-rewrite.md` lets a scheduled Claude Code job propose *one* change to
   `site/survey.config.js` on a branch, with the data, once a step has ≥200 sessions.
3. You review the PR, merge, Netlify deploys. `survey_version` on every event means you can
   compare before/after in the dashboard (`by_version`).

## Social content

Daily: a carousel at 9 AM ET, a Story at noon, a one-pager (fact / true story / quote) at 6 PM ET.
Carousels, rendered by `agent/src/social/slides.py`
in the logo palette with the logo on every slide: navy hook cover, four white content slides
(text, stat tile, two-bar comparison, checklist), and a save/share CTA. The content brief with the
engagement research is `prompts/social-carousels.md`. One-pagers (`agent/src/social/onepagers.py`)
sit on a real photo: drop your own JPGs in `site/social/photos/own/` (filename = tags, e.g.
`kitchen-table-bills.jpg`), or add a free `PEXELS_API_KEY` repository secret and the publish
workflow fetches licensed stock photos and records attribution in `site/social/photos/manifest.json`.
Without either, posts render on the navy brand background.

`agent/src/social/generate.py` asks Claude for a week of posts (themes, compliance rules in
`prompts/social-content.md`, a regex gate on top), renders 1080×1080 JPEG quote cards into
`site/social/` (Instagram's API rejects PNG), and queues them. The weekly workflow opens a PR so you approve captions and images. After merging,
`python src/social/publish.py --really` posts whatever is due that day to Instagram and the
Facebook page (Graph API; needs `IG_USER_ID`, `FB_PAGE_ID`, `FB_PAGE_TOKEN`, and
`social.enabled: true`). The token is a Page access token with `pages_manage_posts`,
`pages_read_engagement`, `instagram_basic`, and `instagram_content_publish`; the IG user id
comes from `GET /{page-id}?fields=instagram_business_account`. Set the repository variable `SOCIAL_CONTENT_ENABLED=true` to turn the
weekly generation on.

## Limits worth knowing

- Netlify synchronous functions time out at 10 s (26 s on Pro by request). `/api/report` rolls
  each past day up into one blob the first time it's read, so repeat reads are fast; a single day
  with tens of thousands of events could still be slow on first read. Today's events are read live.
- Graph API version defaults to `v26.0` (July 2026). Override with `META_API_VERSION` if Meta
  sunsets it.
- Meta's personal-attributes policy is enforced on the landing page's first screen, not just the
  ad. Headlines describe the service ("a free debt settlement review"), never the visitor
  ("struggling with debt?"). Form questions may ask about the visitor's situation.

## Compliance

Consent text and disclosures live in `site/compliance.js` and are never edited by automation.
Copy rules for the page, ads, and social are in `CLAUDE.md`. Have the privacy policy and
disclosures reviewed before launch — they are a reasonable starting template, not legal advice.
