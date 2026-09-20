# Debt Direct Solutions — landing page + funnel automation

This repo is the source of truth for debtdirectsolutions.com and the tooling
that watches it. Netlify deploys `site/` on every push to `main` that touches
`site/`, `netlify/`, `netlify.toml`, or `package.json`.

## Layout

| Path | What | Who edits |
|---|---|---|
| `site/survey.config.js` | Survey questions, order, wording, hero copy | You, or the weekly survey-rewrite job (via a branch + PR, never direct to main) |
| `site/compliance.js` | Consent text, disclosures | **Humans only.** Never edited by automation. |
| `site/config.js` | Pixel ID, endpoints, phone | You |
| `site/tracker.js`, `site/app.js` | Event tracking + survey renderer | Code changes only, with tests |
| `netlify/functions/*` | `/api/track`, `/api/lead`, `/api/report` | Code changes only |
| `netlify/lib/funnel.js` ↔ `agent/src/funnel.py` | Funnel math, must stay in sync | Change both, run both test suites |
| `agent/config.yml` | Every threshold | You |
| `agent/src/act.py` | The only file that writes to the Meta ad account | Never called by a model. Only `rules.py` calls it. |
| `prompts/*.md` | Standing instructions for the scheduled Claude jobs | You |

## Rules for any automated agent working here

1. **Never edit `site/compliance.js`.** It is legal language.
2. **Never call `agent/src/act.py` directly, never set `rules.enabled: true`, never set `social.enabled: true`.** Those are human decisions.
3. **Never change which fields the lead form collects or the `/api/lead` payload.** You may change question wording, order, options, help text, and step count in `survey.config.js`.
4. **Keep every survey step `id` stable.** Analytics are keyed by id. Bump `version` on every change.
5. **Propose survey changes as a branch + PR with the drop-off data that justifies them.** A human merges. Netlify deploys.
6. **Don't act on fewer than `funnel.min_sessions_per_step_for_rewrite` sessions per step.** Report and wait instead.
7. **Compliance for all copy** (page, ads, social): no guaranteed outcomes, no savings percentages or dollar figures, no implied government affiliation, no timelines, never tell people to stop paying creditors, no legal/tax advice. Debt relief runs under Meta's *Financial Products and Services* Special Ad Category.
8. **Describe the service, never the person** (Meta personal-attributes policy; enforced on the ad *and* the landing page's first screen). Rejected: "Struggling with debt?", "If you're behind on payments", "We understand your stress", "For people with bad credit". Allowed: "Debt settlement options, explained", "A free review of unsecured debt balances". Form questions may ask about the visitor's situation; headlines, ad copy, and captions may not assert it.
9. **Audience is 50+, under real financial stress.** Calm, plain, consultative. Never salesy.

## Commands

```bash
npm test                                  # funnel math + event validation (node)
node scripts/serve.mjs                    # local site + stub API at :8787, events → .local/events.jsonl
cd agent && python -m pytest tests        # rules engine + funnel (python)
cd agent && python src/digest.py          # daily digest (fetches Meta + funnel, writes reports/)
cd agent && python src/rules.py           # dry-run: what the rules would do
cd agent && python src/funnel.py --days 7 # drop-off by step, by ad, with findings
```
