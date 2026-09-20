import { createHash, randomUUID } from "node:crypto";

export const EVENT_TYPES = new Set([
  "page_view", "cta_click", "scroll_depth", "survey_start", "step_view", "step_complete",
  "step_back", "field_focus", "field_error", "form_submit", "lead", "lead_error",
  "page_hidden", "thank_you_view", "js_error"
]);

export function json(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extraHeaders }
  });
}

export function sha256(value) {
  if (value == null) return null;
  const v = String(value).trim().toLowerCase();
  if (!v) return null;
  return createHash("sha256").update(v).digest("hex");
}

export function normalizePhone(raw) {
  if (!raw) return null;
  let d = String(raw).replace(/\D/g, "");
  if (d.length === 11 && d.startsWith("1")) d = d.slice(1);
  if (d.length !== 10) return null;
  return "1" + d; // E.164 without plus, as Meta expects before hashing
}

export function isEmail(s) {
  return typeof s === "string" && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(s.trim());
}

export function clientIp(req, context) {
  return (context && context.ip) || req.headers.get("x-nf-client-connection-ip") || (req.headers.get("x-forwarded-for") || "").split(",")[0].trim() || null;
}

export function dayKey(iso) {
  return (iso || new Date().toISOString()).slice(0, 10);
}

export function newId() {
  return randomUUID();
}

const str = (v, max = 200) => (v == null ? null : String(v).slice(0, max));

/** Validate + trim a browser event into the shape we store. Returns null if invalid. */
export function normalizeEvent(raw, server = {}) {
  if (!raw || typeof raw !== "object") return null;
  if (!EVENT_TYPES.has(raw.type)) return null;
  if (!raw.session_id || typeof raw.session_id !== "string") return null;
  const attr = raw.attr && typeof raw.attr === "object" ? raw.attr : {};
  const ctx = raw.ctx && typeof raw.ctx === "object" ? raw.ctx : {};
  const ts = typeof raw.ts === "string" && !Number.isNaN(Date.parse(raw.ts)) ? new Date(raw.ts).toISOString() : new Date().toISOString();
  let answer = raw.answer;
  if (Array.isArray(answer)) answer = answer.slice(0, 10).map((a) => str(a, 40));
  else if (answer != null && typeof answer !== "number") answer = str(answer, 40);
  return {
    type: raw.type,
    ts,
    received_at: new Date().toISOString(),
    event_id: str(raw.event_id, 64) || newId(),
    session_id: str(raw.session_id, 64),
    visitor_id: str(raw.visitor_id, 64),
    page: str(raw.page, 120),
    survey_version: str(raw.survey_version, 40),
    step: Number.isInteger(raw.step) ? raw.step : null,
    question_id: str(raw.question_id, 40),
    answer: answer == null ? null : answer,
    ms: Number.isFinite(raw.ms) ? Math.round(raw.ms) : null,
    session_ms: Number.isFinite(raw.session_ms) ? Math.round(raw.session_ms) : null,
    fbp: str(raw.fbp, 64),
    fbc: str(raw.fbc, 200),
    attr: {
      utm_source: str(attr.utm_source, 80), utm_medium: str(attr.utm_medium, 80), utm_campaign: str(attr.utm_campaign, 120),
      utm_content: str(attr.utm_content, 120), utm_term: str(attr.utm_term, 120), fbclid: str(attr.fbclid, 200),
      ad_id: str(attr.ad_id, 40), adset_id: str(attr.adset_id, 40), campaign_id: str(attr.campaign_id, 40),
      placement: str(attr.placement, 80), referrer: str(attr.referrer, 300), landing_path: str(attr.landing_path, 120),
      first_seen: str(attr.first_seen, 40)
    },
    ctx: {
      ua: str(ctx.ua, 300), lang: str(ctx.lang, 20), vw: Number.isFinite(ctx.vw) ? ctx.vw : null, vh: Number.isFinite(ctx.vh) ? ctx.vh : null,
      device: ctx.device === "mobile" ? "mobile" : "desktop", tz: str(ctx.tz, 60)
    },
    extra: raw.extra && typeof raw.extra === "object" ? JSON.parse(JSON.stringify(raw.extra).slice(0, 2000)) : null,
    server: {
      ip: server.ip || null,
      country: server.country || null,
      region: server.region || null,
      city: server.city || null
    }
  };
}
