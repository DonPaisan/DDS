/* DDS funnel tracker.
 * Fires one structured event per funnel action to /api/track (own event store)
 * and mirrors the key ones to the Meta Pixel with a shared event_id so the
 * server-side Conversions API call deduplicates against the browser pixel.
 *
 * Every event: { type, ts, event_id, session_id, visitor_id, page, survey_version,
 *                step, question_id, answer, ms, attr:{...}, ctx:{...} }
 */
(function () {
  var cfg = window.DDS_CONFIG || {};
  var ENDPOINT = cfg.trackEndpoint || "/api/track";

  function uid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "x" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }
  function store(kind, key, val) {
    try {
      var s = kind === "local" ? localStorage : sessionStorage;
      if (val === undefined) return s.getItem(key);
      s.setItem(key, val);
      return val;
    } catch (e) { return val === undefined ? null : val; }
  }
  function getCookie(name) {
    var m = document.cookie.match("(?:^|; )" + name + "=([^;]*)");
    return m ? decodeURIComponent(m[1]) : null;
  }
  function setCookie(name, value, days) {
    try {
      var d = new Date(Date.now() + days * 864e5).toUTCString();
      document.cookie = name + "=" + encodeURIComponent(value) + "; expires=" + d + "; path=/; SameSite=Lax";
    } catch (e) {}
  }

  // ── identity ──────────────────────────────────────────────────────────────
  var visitorId = store("local", "dds_vid") || store("local", "dds_vid", uid());
  var sessionId = store("session", "dds_sid") || store("session", "dds_sid", uid());
  var isNewSession = !store("session", "dds_seen");
  store("session", "dds_seen", "1");

  // ── attribution: captured once per session on the first page view ─────────
  var attr = null;
  try { attr = JSON.parse(store("session", "dds_attr") || "null"); } catch (e) {}
  if (!attr) {
    var q = new URLSearchParams(location.search);
    attr = {
      utm_source: q.get("utm_source") || null,
      utm_medium: q.get("utm_medium") || null,
      utm_campaign: q.get("utm_campaign") || null,
      utm_content: q.get("utm_content") || null,   // put {{ad.name}} here in Meta URL params
      utm_term: q.get("utm_term") || null,         // put {{adset.name}} here
      fbclid: q.get("fbclid") || null,
      ad_id: q.get("ad_id") || null,               // {{ad.id}}
      adset_id: q.get("adset_id") || null,         // {{adset.id}}
      campaign_id: q.get("campaign_id") || null,   // {{campaign.id}}
      placement: q.get("placement") || null,       // {{placement}}
      referrer: document.referrer || null,
      landing_path: location.pathname,
      first_seen: new Date().toISOString()
    };
    store("session", "dds_attr", JSON.stringify(attr));
  }
  // Build _fbc ourselves so CAPI gets click attribution even if the pixel is blocked.
  if (attr.fbclid && !getCookie("_fbc")) {
    setCookie("_fbc", "fb.1." + Date.now() + "." + attr.fbclid, 90);
  }

  var ctx = {
    ua: navigator.userAgent,
    lang: navigator.language,
    vw: window.innerWidth,
    vh: window.innerHeight,
    dpr: window.devicePixelRatio || 1,
    device: /Mobi|Android/i.test(navigator.userAgent) ? "mobile" : "desktop",
    tz: (Intl.DateTimeFormat().resolvedOptions().timeZone || null)
  };

  var surveyVersion = (window.DDS_SURVEY && window.DDS_SURVEY.version) || null;
  var currentStep = null;      // updated by app.js via DDS.setStep
  var currentQuestion = null;
  var sessionStart = Date.now();

  // ── transport ─────────────────────────────────────────────────────────────
  function send(payload, useBeacon) {
    var body = JSON.stringify(payload);
    if (cfg.debug) console.log("[dds]", payload.type, payload);
    if (useBeacon && navigator.sendBeacon) {
      try {
        return navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "application/json" }));
      } catch (e) {}
    }
    try {
      fetch(ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" }, body: body, keepalive: true })
        .catch(function () {});
    } catch (e) {}
  }

  // ── pixel mirror ──────────────────────────────────────────────────────────
  var PIXEL_STANDARD = { page_view: "PageView", survey_start: "ViewContent", lead: "Lead", form_submit: "InitiateCheckout" };
  function pixel(type, eventId, data) {
    if (!window.fbq) return;
    try {
      if (PIXEL_STANDARD[type]) fbq("track", PIXEL_STANDARD[type], data || {}, { eventID: eventId });
      else if (type === "step_complete") fbq("trackCustom", "SurveyStep", data || {}, { eventID: eventId });
    } catch (e) {}
  }

  function track(type, fields, opts) {
    opts = opts || {};
    var ev = {
      type: type,
      ts: new Date().toISOString(),
      event_id: uid(),
      session_id: sessionId,
      visitor_id: visitorId,
      page: location.pathname,
      survey_version: surveyVersion,
      step: fields && fields.step != null ? fields.step : currentStep,
      question_id: fields && fields.question_id ? fields.question_id : currentQuestion,
      answer: fields && fields.answer !== undefined ? fields.answer : null,
      ms: fields && fields.ms != null ? fields.ms : null,
      session_ms: Date.now() - sessionStart,
      fbp: getCookie("_fbp"),
      fbc: getCookie("_fbc"),
      attr: attr,
      ctx: ctx,
      extra: fields && fields.extra ? fields.extra : null
    };
    pixel(type, ev.event_id, { step: ev.step, question_id: ev.question_id, survey_version: surveyVersion });
    send(ev, opts.beacon);
    return ev.event_id;
  }

  // ── page-level events ─────────────────────────────────────────────────────
  var pageViewSent = false;
  function pageView() {
    if (pageViewSent) return;
    pageViewSent = true;
    var nav = performance.getEntriesByType && performance.getEntriesByType("navigation")[0];
    track("page_view", {
      step: null,
      question_id: null,
      extra: {
        new_session: isNewSession,
        load_ms: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
        ttfb_ms: nav ? Math.round(nav.responseStart) : null
      }
    });
  }

  // scroll depth milestones (helps tell "never saw the form" from "saw it, bailed")
  var marks = [25, 50, 75, 100], seen = {};
  function onScroll() {
    var h = document.documentElement.scrollHeight - window.innerHeight;
    var pct = h > 0 ? Math.round((window.scrollY / h) * 100) : 100;
    for (var i = 0; i < marks.length; i++) {
      if (pct >= marks[i] && !seen[marks[i]]) {
        seen[marks[i]] = true;
        track("scroll_depth", { step: null, question_id: null, answer: marks[i] });
      }
    }
  }
  window.addEventListener("scroll", onScroll, { passive: true });

  // exit: last known step is what tells us where they abandoned
  var hiddenSent = false;
  function onHide() {
    if (hiddenSent) return;
    hiddenSent = true;
    track("page_hidden", { extra: { visible_ms: Date.now() - sessionStart } }, { beacon: true });
  }
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") onHide();
    else hiddenSent = false; // came back — allow another exit event later
  });
  window.addEventListener("pagehide", onHide);

  window.addEventListener("error", function (e) {
    track("js_error", { extra: { message: String(e.message || e).slice(0, 200), src: (e.filename || "").slice(0, 120), line: e.lineno || null } });
  });

  // ── public API ────────────────────────────────────────────────────────────
  window.DDS = {
    track: track,
    pageView: pageView,
    sessionId: sessionId,
    visitorId: visitorId,
    attr: attr,
    setStep: function (step, questionId) { currentStep = step; currentQuestion = questionId; },
    getStep: function () { return { step: currentStep, question_id: currentQuestion }; }
  };

  if (document.readyState === "complete") pageView();
  else window.addEventListener("load", pageView);
})();
