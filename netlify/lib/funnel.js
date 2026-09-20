/* Pure funnel math over a list of normalized events. No I/O.
 * Mirrors agent/src/funnel.py — keep the two in sync. */

function pct(n, d) { return d ? Math.round((n / d) * 1000) / 10 : null; }
function median(arr) {
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : Math.round((s[m - 1] + s[m]) / 2);
}

/** Group events by session and build one record per session. */
export function sessionize(events) {
  const sessions = new Map();
  for (const e of events) {
    if (!e || !e.session_id) continue;
    let s = sessions.get(e.session_id);
    if (!s) {
      s = {
        session_id: e.session_id, visitor_id: e.visitor_id, first_ts: e.ts, last_ts: e.ts,
        device: e.ctx && e.ctx.device, attr: e.attr || {}, survey_version: e.survey_version,
        page_view: false, cta_click: false, survey_start: false, form_submit: false, lead: false, lead_error: false,
        max_scroll: 0, steps_viewed: new Set(), steps_completed: new Set(), step_ms: {}, field_errors: [],
        last_step: null, last_question: null, load_ms: null, js_errors: 0, backs: 0
      };
      sessions.set(e.session_id, s);
    }
    if (e.ts < s.first_ts) s.first_ts = e.ts;
    if (e.ts > s.last_ts) s.last_ts = e.ts;
    if (!s.survey_version && e.survey_version) s.survey_version = e.survey_version;
    switch (e.type) {
      case "page_view": s.page_view = true; if (e.extra && e.extra.load_ms != null) s.load_ms = e.extra.load_ms; break;
      case "cta_click": s.cta_click = true; break;
      case "scroll_depth": s.max_scroll = Math.max(s.max_scroll, Number(e.answer) || 0); break;
      case "survey_start": s.survey_start = true; break;
      case "step_view": if (e.step != null) { s.steps_viewed.add(e.step); s.last_step = e.step; s.last_question = e.question_id; } break;
      case "step_complete":
        if (e.step != null) { s.steps_completed.add(e.step); if (e.ms != null) (s.step_ms[e.step] ||= []).push(e.ms); }
        break;
      case "step_back": s.backs++; break;
      case "field_error": s.field_errors.push((e.extra && e.extra.field) || "unknown"); break;
      case "form_submit": s.form_submit = true; break;
      case "lead": s.lead = true; break;
      case "lead_error": s.lead_error = true; break;
      case "js_error": s.js_errors++; break;
      default: break;
    }
  }
  return [...sessions.values()];
}

/**
 * @param events normalized events
 * @param steps  optional [{id, question}] from survey config, for labels
 */
export function summarize(events, steps = null) {
  const sessions = sessionize(events);
  const n = sessions.length;
  const c = (fn) => sessions.filter(fn).length;

  const stepIds = new Map();
  for (const e of events) if (e.type === "step_view" && e.step != null) stepIds.set(e.step, e.question_id);
  const maxStep = stepIds.size ? Math.max(...stepIds.keys()) : -1;

  const stepStats = [];
  for (let i = 0; i <= maxStep; i++) {
    const viewed = c((s) => s.steps_viewed.has(i));
    const completed = c((s) => s.steps_completed.has(i));
    const abandonedHere = c((s) => s.last_step === i && !s.steps_completed.has(i));
    const ms = sessions.flatMap((s) => s.step_ms[i] || []);
    stepStats.push({
      step: i,
      question_id: stepIds.get(i) || (steps && steps[i] && steps[i].id) || null,
      viewed, completed,
      completion_rate: pct(completed, viewed),
      abandoned_here: abandonedHere,
      abandon_rate: pct(abandonedHere, viewed),
      median_ms: median(ms)
    });
  }

  const pageViews = c((s) => s.page_view);
  const starts = c((s) => s.survey_start);
  const submits = c((s) => s.form_submit);
  const leads = c((s) => s.lead);
  const leadErrors = c((s) => s.lead_error);

  const byDevice = {};
  for (const d of ["mobile", "desktop"]) {
    const ss = sessions.filter((s) => s.device === d);
    byDevice[d] = { sessions: ss.length, starts: ss.filter((s) => s.survey_start).length, leads: ss.filter((s) => s.lead).length,
      start_rate: pct(ss.filter((s) => s.survey_start).length, ss.length), lead_rate: pct(ss.filter((s) => s.lead).length, ss.length) };
  }

  const bySource = {};
  for (const s of sessions) {
    const k = [s.attr.utm_source || (s.attr.fbclid ? "facebook" : "direct"), s.attr.utm_campaign || "-", s.attr.utm_content || s.attr.ad_id || "-"].join(" / ");
    const b = (bySource[k] ||= { sessions: 0, starts: 0, leads: 0 });
    b.sessions++; if (s.survey_start) b.starts++; if (s.lead) b.leads++;
  }
  for (const b of Object.values(bySource)) { b.start_rate = pct(b.starts, b.sessions); b.lead_rate = pct(b.leads, b.sessions); }

  const fieldErrors = {};
  for (const s of sessions) for (const f of s.field_errors) fieldErrors[f] = (fieldErrors[f] || 0) + 1;

  const byVersion = {};
  for (const s of sessions) {
    const b = (byVersion[s.survey_version || "unknown"] ||= { sessions: 0, starts: 0, leads: 0 });
    b.sessions++; if (s.survey_start) b.starts++; if (s.lead) b.leads++;
  }

  const scrollNoStart = sessions.filter((s) => !s.survey_start);
  const loadTimes = sessions.map((s) => s.load_ms).filter((v) => v != null);

  return {
    sessions: n,
    page_views: pageViews,
    survey_starts: starts,
    form_submits: submits,
    leads,
    lead_errors: leadErrors,
    js_error_sessions: c((s) => s.js_errors > 0),
    rates: {
      start_rate: pct(starts, n),
      submit_rate_of_starts: pct(submits, starts),
      lead_rate_of_sessions: pct(leads, n),
      lead_rate_of_submits: pct(leads, submits)
    },
    no_start: {
      sessions: scrollNoStart.length,
      never_scrolled_past_25: scrollNoStart.filter((s) => s.max_scroll < 25).length,
      clicked_cta_but_no_start: scrollNoStart.filter((s) => s.cta_click).length,
      median_visible_ms: median(scrollNoStart.map((s) => Date.parse(s.last_ts) - Date.parse(s.first_ts)))
    },
    load: { median_ms: median(loadTimes), over_3s: loadTimes.filter((v) => v > 3000).length },
    steps: stepStats,
    by_device: byDevice,
    by_source: bySource,
    by_version: byVersion,
    field_errors: fieldErrors,
    back_presses: sessions.reduce((a, s) => a + s.backs, 0)
  };
}

/** Plain-English diagnosis from a summary. Rules only, no model. */
export function diagnose(summary, extra = {}) {
  const out = [];
  const s = summary;
  const minN = extra.min_sessions || 30;
  if (s.sessions < minN) {
    out.push({ level: "info", code: "low_volume", text: `Only ${s.sessions} sessions in this window; below ${minN} the rates are noise. Keep collecting.` });
    return out;
  }
  if (extra.link_clicks != null && s.sessions < extra.link_clicks * 0.6) {
    out.push({ level: "critical", code: "click_to_view_gap", text: `Meta reports ${extra.link_clicks} link clicks but only ${s.sessions} sessions reached the page (${pct(s.sessions, extra.link_clicks)}%). That is a loading, redirect, or domain problem, not a page-content problem. Check the ad's URL, the site is up, and load time.` });
  }
  if (s.load.over_3s > s.sessions * 0.25) {
    out.push({ level: "critical", code: "slow_load", text: `${s.load.over_3s} of ${s.sessions} sessions took over 3s to load (median ${s.load.median_ms}ms). Mobile users on ads bounce on slow pages before reading a word.` });
  }
  if (s.js_error_sessions > s.sessions * 0.05) {
    out.push({ level: "critical", code: "js_errors", text: `${s.js_error_sessions} sessions hit a JavaScript error. The survey may be broken for some browsers.` });
  }
  if (s.form_submits > 0 && s.lead_errors > 0 && s.lead_errors >= s.form_submits * 0.2) {
    out.push({ level: "critical", code: "lead_endpoint_failing", text: `${s.lead_errors} submissions failed to save against ${s.form_submits} attempts. The lead function is failing; people are trying to convert and can't.` });
  }
  if (s.rates.start_rate != null && s.rates.start_rate < 25) {
    const ns = s.no_start;
    if (ns.never_scrolled_past_25 > ns.sessions * 0.5) {
      out.push({ level: "high", code: "bounce_above_fold", text: `Only ${s.rates.start_rate}% start the survey and most non-starters never scrolled. The first screen isn't matching what the ad promised. Fix the headline/subhead to echo the ad hook before touching the questions.` });
    } else {
      out.push({ level: "high", code: "low_start_rate", text: `Only ${s.rates.start_rate}% start the survey even though people are scrolling. The offer or first question isn't compelling enough, or the survey isn't obviously the next step. Consider making the first question the hero.` });
    }
  }
  const worst = [...s.steps].filter((st) => st.viewed >= 10).sort((a, b) => (b.abandon_rate || 0) - (a.abandon_rate || 0))[0];
  if (worst && worst.abandon_rate >= 30) {
    const isContact = worst.step === s.steps.length - 1;
    out.push({ level: "high", code: isContact ? "contact_step_dropoff" : "step_dropoff",
      text: isContact
        ? `${worst.abandon_rate}% of people who reach the contact step leave without submitting. They're interested but don't trust you with a phone number yet. Add reassurance, show what happens next, ask for less (email or phone, not both), or move the consent text below the button.`
        : `Step ${worst.step + 1} (${worst.question_id}) loses ${worst.abandon_rate}% of the people who see it. Reword it, make it lower-commitment, or move it later.` });
  }
  const topField = Object.entries(s.field_errors).sort((a, b) => b[1] - a[1])[0];
  if (topField && topField[1] >= Math.max(5, s.form_submits * 0.3)) {
    out.push({ level: "medium", code: "field_friction", text: `The "${topField[0]}" field produced ${topField[1]} validation errors. Loosen validation or improve the hint text.` });
  }
  const m = s.by_device.mobile, d = s.by_device.desktop;
  if (m.sessions >= 20 && d.sessions >= 20 && m.lead_rate != null && d.lead_rate != null && m.lead_rate < d.lead_rate * 0.5) {
    out.push({ level: "medium", code: "mobile_gap", text: `Mobile converts at ${m.lead_rate}% vs desktop ${d.lead_rate}%. Almost all ad traffic is mobile, so test the page on a real phone.` });
  }
  if (!out.length) out.push({ level: "info", code: "healthy", text: "No structural problem detected. Improvements now come from creative/audience and survey copy tests." });
  return out;
}
