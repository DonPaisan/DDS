You may propose changes to `site/survey.config.js` — and only that file — to reduce drop-off.
Read CLAUDE.md first. It lists what you may and may not change.

Steps:
1. `cd agent && python src/funnel.py --days 14 --json` — read per-step abandonment.
2. If no step has at least `funnel.min_sessions_per_step_for_rewrite` sessions viewed, write
   `agent/reports/survey-<date>.md` saying so and STOP. Do not edit anything.
3. Otherwise pick the single worst step by abandon_rate (ignore steps viewed < threshold).
4. Propose ONE change: wording, help text, option labels, or moving the step later. Prefer
   ordering changes over wording changes; prefer removing words over adding them. Keep the
   `contact` step last. Keep every `id`. Bump `version` to today's date + ".1" (or ".2" if same day).
5. Create a branch `survey/<date>-<step-id>`, commit with a message that states the abandon rate
   before and the hypothesis. Do not push to main. Do not merge. Do not deploy.
6. Write `agent/reports/survey-<date>.md`: the data, the change, the hypothesis, and how you'll
   know in two weeks whether it worked (which number, which direction).

Never touch `site/compliance.js`, `site/app.js`, `netlify/`, or the lead payload.

Personal-attributes rule (Meta rejects violations, and checks the landing page's first screen too):
describe the service, never the reader's situation. No "struggling with debt?", "if you're behind",
"we understand your stress", "for people with bad credit". Say what the service is and what the review does.
