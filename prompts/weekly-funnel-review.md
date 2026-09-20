You are reviewing the Debt Direct Solutions landing page funnel for the past 7 days.
Read CLAUDE.md first. Then run, from the repo root:

    cd agent && python src/digest.py --no-email
    cd agent && python src/funnel.py --days 7 --json

Using ONLY that data, write `agent/reports/weekly-<YYYY-MM-DD>.md` with:

1. The one number that matters: leads per 100 sessions this week vs last week.
2. The single biggest leak, stated as "X% of people who reach <step> leave", and whether the
   sample is large enough to trust (see funnel.min_sessions_per_step_for_rewrite in agent/config.yml).
3. Ad → page: link clicks vs tracked sessions. If under 60%, say so first; it outranks everything else.
4. Which ads (utm_content) bring people who start the survey vs people who bounce. Name the best and worst.
5. Mobile vs desktop.
6. ONE recommended change, with the data that justifies it, and what you'd expect to move.
   If the sample is too small, say "collect more data" and stop. Do not invent a recommendation.

Do not edit site files in this job. Do not touch the ad account. Do not email anyone.
