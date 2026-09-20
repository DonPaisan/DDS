import { json, clientIp, isEmail, normalizePhone, newId, normalizeEvent } from "../lib/util.js";
import { leadsStore, writeEvent } from "../lib/store.js";
import { sendCapi, userData } from "../lib/capi.js";

const str = (v, max = 200) => (v == null ? null : String(v).slice(0, max));

async function forwardWebhook(lead) {
  const url = process.env.LEAD_WEBHOOK_URL;
  if (!url) return { skipped: true };
  try {
    const res = await fetch(url, { method: "POST", headers: { "content-type": "application/json", ...(process.env.LEAD_WEBHOOK_SECRET ? { "x-webhook-secret": process.env.LEAD_WEBHOOK_SECRET } : {}) }, body: JSON.stringify(lead), signal: AbortSignal.timeout(5000) });
    return { ok: res.ok, status: res.status };
  } catch (err) { console.error("[lead] webhook failed", err && err.message); return { ok: false, error: String(err && err.message) }; }
}

async function notifyEmail(lead) {
  const key = process.env.RESEND_API_KEY, to = process.env.LEAD_NOTIFY_TO, from = process.env.LEAD_NOTIFY_FROM || "leads@debtdirectsolutions.com";
  if (!key || !to) return { skipped: true };
  const a = lead.answers || {};
  const text = [
    `New lead from the landing page`,
    ``,
    `Name:   ${lead.contact.first_name}`,
    `Phone:  ${lead.contact.phone}`,
    `Email:  ${lead.contact.email}`,
    `State:  ${a.state || "-"}`,
    `Debt:   ${a.debt_amount || "-"} (${Array.isArray(a.debt_type) ? a.debt_type.join(", ") : a.debt_type || "-"})`,
    `Status: ${a.payment_status || "-"}`,
    ``,
    `Source: ${lead.attr.utm_source || "-"} / ${lead.attr.utm_campaign || "-"} / ${lead.attr.utm_content || "-"}`,
    `Lead ID: ${lead.lead_id}`,
    `Consent: v${lead.consent_version} at ${lead.created_at}`
  ].join("\n");
  try {
    const res = await fetch("https://api.resend.com/emails", { method: "POST", headers: { authorization: `Bearer ${key}`, "content-type": "application/json" }, body: JSON.stringify({ from, to: to.split(",").map((s) => s.trim()), subject: `New lead: ${lead.contact.first_name} (${a.debt_amount || "?"}, ${a.state || "?"})`, text }), signal: AbortSignal.timeout(5000) });
    return { ok: res.ok, status: res.status };
  } catch (err) { console.error("[lead] email failed", err && err.message); return { ok: false, error: String(err && err.message) }; }
}

export default async (req, context) => {
  if (req.method !== "POST") return json({ error: "POST only" }, 405);
  let body;
  try { body = await req.json(); } catch { return json({ error: "invalid json" }, 400); }

  const contact = body.contact || {};
  const phone = normalizePhone(contact.phone);
  const email = isEmail(contact.email) ? String(contact.email).trim().toLowerCase() : null;
  const firstName = str(contact.first_name, 80);
  if (!firstName || !firstName.trim()) return json({ error: "first_name required" }, 400);
  if (!phone) return json({ error: "valid phone required" }, 400);
  if (!email) return json({ error: "valid email required" }, 400);
  if (!body.consent_version) return json({ error: "consent required" }, 400);

  const now = new Date().toISOString();
  const geo = (context && context.geo) || {};
  const ip = clientIp(req, context);
  const ua = req.headers.get("user-agent");
  const lead = {
    lead_id: newId(),
    created_at: now,
    session_id: str(body.session_id, 64),
    visitor_id: str(body.visitor_id, 64),
    event_id: str(body.event_id, 64) || newId(),
    survey_version: str(body.survey_version, 40),
    consent: { version: str(body.consent_version, 40), text: str(body.consent_text, 2000), ip, user_agent: str(ua, 300), at: now },
    consent_version: str(body.consent_version, 40),
    contact: { first_name: firstName.trim(), phone, email },
    answers: body.answers && typeof body.answers === "object" ? JSON.parse(JSON.stringify(body.answers).slice(0, 4000)) : {},
    attr: body.attr && typeof body.attr === "object" ? body.attr : {},
    page_url: str(body.page_url, 300),
    geo: { country: geo.country && geo.country.code, region: geo.subdivision && geo.subdivision.code, city: geo.city },
    fbp: str(body.fbp, 64), fbc: str(body.fbc, 200),
    forward: {}
  };
  delete lead.answers.contact;

  const key = `${now.slice(0, 10)}/${lead.lead_id}.json`;
  try {
    await leadsStore().setJSON(key, lead);
  } catch (err) {
    console.error("[lead] store failed", err && err.message);
    return json({ error: "could not save lead" }, 500);
  }

  // Server-side funnel event so the funnel is complete even if the browser's `lead` event never lands.
  const ev = normalizeEvent({ type: "lead", ts: now, event_id: lead.event_id, session_id: lead.session_id || lead.lead_id, visitor_id: lead.visitor_id,
    page: "/api/lead", survey_version: lead.survey_version, attr: lead.attr, ctx: { ua, device: /Mobi|Android/i.test(ua || "") ? "mobile" : "desktop" }, extra: { lead_id: lead.lead_id, source: "server" } },
    { ip, country: lead.geo.country, region: lead.geo.region, city: lead.geo.city });
  const eventWrite = ev ? writeEvent(ev).catch((e) => console.error("[lead] event write failed", e && e.message)) : Promise.resolve();

  const capi = sendCapi([{
    event_name: "Lead",
    event_id: lead.event_id,
    event_time: Math.floor(Date.now() / 1000),
    event_source_url: lead.page_url || undefined,
    user_data: userData({ email, phone, firstName: lead.contact.first_name, fbp: lead.fbp, fbc: lead.fbc, ip, ua, externalId: lead.visitor_id, country: "us", state: lead.answers.state }),
    custom_data: { debt_amount: lead.answers.debt_amount, payment_status: lead.answers.payment_status, survey_version: lead.survey_version }
  }]);

  const [capiRes, hookRes, mailRes] = await Promise.all([capi, forwardWebhook(lead), notifyEmail(lead), eventWrite]);
  lead.forward = { capi: capiRes, webhook: hookRes, email: mailRes };
  leadsStore().setJSON(key, lead).catch(() => {});

  return json({ ok: true, lead_id: lead.lead_id });
};

export const config = { path: "/api/lead" };
