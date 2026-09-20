import { test } from "node:test";
import assert from "node:assert/strict";
import { summarize, diagnose, sessionize } from "../lib/funnel.js";
import { normalizeEvent } from "../lib/util.js";

function ev(type, sid, fields = {}) {
  return normalizeEvent({ type, session_id: sid, visitor_id: "v" + sid, ts: fields.ts || "2026-09-20T10:00:00.000Z", page: "/", survey_version: "t1",
    attr: { utm_source: "facebook", utm_campaign: "c1", utm_content: fields.ad || "adA" }, ctx: { device: fields.device || "mobile", ua: "x" }, ...fields });
}

/** Build a session that gets to `reach` step and completes `done` steps. */
function session(sid, { reach = 0, done = 0, lead = false, device = "mobile", scroll = 50, start = true, ad } = {}) {
  const out = [ev("page_view", sid, { device, ad, extra: { load_ms: 800 } }), ev("scroll_depth", sid, { answer: scroll, device, ad })];
  if (start) out.push(ev("survey_start", sid, { step: 0, question_id: "q0", device, ad }));
  for (let i = 0; i <= reach; i++) {
    out.push(ev("step_view", sid, { step: i, question_id: "q" + i, device, ad }));
    if (i < done) out.push(ev("step_complete", sid, { step: i, question_id: "q" + i, answer: "a", ms: 1000 + i, device, ad }));
  }
  if (lead) { out.push(ev("form_submit", sid, { step: reach, device, ad })); out.push(ev("lead", sid, { step: reach, device, ad })); }
  return out;
}

test("normalizeEvent rejects unknown types and missing session", () => {
  assert.equal(normalizeEvent({ type: "hack", session_id: "a" }), null);
  assert.equal(normalizeEvent({ type: "page_view" }), null);
  const e = normalizeEvent({ type: "page_view", session_id: "s", ts: "garbage", answer: ["x".repeat(100)], attr: { utm_source: "fb" } });
  assert.ok(!Number.isNaN(Date.parse(e.ts)));
  assert.equal(e.answer[0].length, 40);
  assert.equal(e.attr.utm_source, "fb");
  assert.equal(e.ctx.device, "desktop");
});

test("sessionize tracks last step and completions", () => {
  const s = sessionize(session("s1", { reach: 2, done: 2 }))[0];
  assert.equal(s.last_step, 2);
  assert.equal(s.steps_completed.size, 2);
  assert.equal(s.survey_start, true);
  assert.equal(s.lead, false);
});

test("summarize computes per-step abandonment and rates", () => {
  const events = [
    ...session("a", { reach: 4, done: 5, lead: true }),
    ...session("b", { reach: 4, done: 4 }),           // abandoned at contact
    ...session("c", { reach: 1, done: 1 }),           // abandoned at step 1
    ...session("d", { start: false, scroll: 0 })      // bounced
  ];
  const s = summarize(events);
  assert.equal(s.sessions, 4);
  assert.equal(s.survey_starts, 3);
  assert.equal(s.leads, 1);
  assert.equal(s.rates.start_rate, 75);
  assert.equal(s.steps.length, 5);
  assert.equal(s.steps[1].viewed, 3);
  assert.equal(s.steps[1].abandoned_here, 1);
  assert.equal(s.steps[4].viewed, 2);
  assert.equal(s.steps[4].abandoned_here, 1);
  assert.equal(s.steps[4].abandon_rate, 50);
  assert.equal(s.no_start.sessions, 1);
  assert.equal(s.no_start.never_scrolled_past_25, 1);
  assert.equal(s.by_source["facebook / c1 / adA"].sessions, 4);
  assert.equal(s.steps[0].median_ms, 1000);
});

test("diagnose flags low volume first", () => {
  const f = diagnose(summarize(session("a", {})));
  assert.equal(f[0].code, "low_volume");
});

test("diagnose flags contact-step dropoff and click gap", () => {
  const events = [];
  for (let i = 0; i < 40; i++) events.push(...session("s" + i, { reach: 4, done: 4, lead: i < 10 }));
  const s = summarize(events);
  const codes = diagnose(s, { link_clicks: 200 }).map((f) => f.code);
  assert.ok(codes.includes("contact_step_dropoff"), codes.join(","));
  assert.ok(codes.includes("click_to_view_gap"), codes.join(","));
});

test("diagnose flags above-fold bounce", () => {
  const events = [];
  for (let i = 0; i < 40; i++) events.push(...session("s" + i, { start: i < 5, scroll: i < 5 ? 50 : 0, reach: 0, done: i < 5 ? 1 : 0 }));
  const codes = diagnose(summarize(events)).map((f) => f.code);
  assert.ok(codes.includes("bounce_above_fold"), codes.join(","));
});
