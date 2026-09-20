Weekly creative review for the Debt Direct Solutions Meta ads. Read CLAUDE.md first.

Run `cd agent && python src/fetch_meta.py --days 28` then query `agent/data/ads.sqlite`
(table ad_daily) for ad-level performance over the last 28 days.

1. Flag fatigue: any ad whose CTR in the last 7 days is more than 30% below its own first 7 days.
2. For the two best ads by cost per lead (minimum 20 leads each; if none qualify, say so and use
   link-click rate instead, clearly labeled), describe what the hook is actually doing — the
   emotional job the first line does for someone 55+ who is behind on cards. Not "it performs well".
3. Cross-reference with the landing page: `cd agent && python src/funnel.py --days 28 --json` →
   by_source. An ad with a high click rate but a low survey start rate is promising the wrong
   thing. Say which ones.
4. Draft 5 new primary-text + headline pairs extending the best pattern. Consultative, plain,
   never salesy. Comply with every rule in CLAUDE.md (no guarantees, no percentages, no
   government implication, Credit Special Ad Category).
5. Write to `agent/drafts/<date>-hooks.md`. Do not touch the ad account. Do not create ads.

Personal-attributes rule (Meta rejects violations, and checks the landing page's first screen too):
describe the service, never the reader's situation. No "struggling with debt?", "if you're behind",
"we understand your stress", "for people with bad credit". Say what the service is and what the review does.
