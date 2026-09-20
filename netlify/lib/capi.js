/* Meta Conversions API. Sends server events that dedupe against the browser
 * pixel via event_id. Fails loudly in logs but never throws to the caller. */
import { sha256 } from "./util.js";

const API_VERSION = process.env.META_API_VERSION || "v21.0";

export function capiEnabled() {
  return Boolean(process.env.META_PIXEL_ID && process.env.META_CAPI_TOKEN);
}

/**
 * @param {Array<{event_name:string,event_id:string,event_time?:number,event_source_url?:string,
 *   user_data:object,custom_data?:object,action_source?:string}>} events
 */
export async function sendCapi(events, { timeoutMs = 4000 } = {}) {
  if (!capiEnabled() || !events.length) return { skipped: true };
  const url = `https://graph.facebook.com/${API_VERSION}/${process.env.META_PIXEL_ID}/events`;
  const body = {
    data: events.map((e) => ({
      event_name: e.event_name,
      event_time: e.event_time || Math.floor(Date.now() / 1000),
      event_id: e.event_id,
      event_source_url: e.event_source_url,
      action_source: e.action_source || "website",
      user_data: e.user_data,
      custom_data: e.custom_data || undefined
    })),
    access_token: process.env.META_CAPI_TOKEN
  };
  if (process.env.META_TEST_EVENT_CODE) body.test_event_code = process.env.META_TEST_EVENT_CODE;
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), signal: ctrl.signal });
    const text = await res.text();
    if (!res.ok) {
      console.error("[capi] error", res.status, text.slice(0, 500));
      return { ok: false, status: res.status, body: text.slice(0, 500) };
    }
    return { ok: true, status: res.status };
  } catch (err) {
    console.error("[capi] failed", err && err.message);
    return { ok: false, error: String(err && err.message) };
  } finally {
    clearTimeout(t);
  }
}

/** Build the user_data block Meta wants: hashed PII + raw browser identifiers. */
export function userData({ email, phone, firstName, fbp, fbc, ip, ua, externalId, country, state }) {
  const ud = {};
  if (email) ud.em = [sha256(email)];
  if (phone) ud.ph = [sha256(phone)];
  if (firstName) ud.fn = [sha256(firstName)];
  if (country) ud.country = [sha256(country)];
  if (state) ud.st = [sha256(state)];
  if (externalId) ud.external_id = [sha256(externalId)];
  if (fbp) ud.fbp = fbp;
  if (fbc) ud.fbc = fbc;
  if (ip) ud.client_ip_address = ip;
  if (ua) ud.client_user_agent = ua;
  return ud;
}

/** Map our funnel event types to Meta events mirrored server-side. */
export const MIRRORED = { page_view: "PageView", survey_start: "ViewContent", form_submit: "InitiateCheckout" };
