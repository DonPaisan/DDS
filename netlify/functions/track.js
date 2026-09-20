import { normalizeEvent, json, clientIp } from "../lib/util.js";
import { writeEvent } from "../lib/store.js";
import { sendCapi, userData, MIRRORED } from "../lib/capi.js";

export default async (req, context) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204 });
  if (req.method !== "POST") return json({ error: "POST only" }, 405);

  let raw;
  try { raw = await req.json(); } catch { return json({ error: "invalid json" }, 400); }

  const geo = (context && context.geo) || {};
  const server = { ip: clientIp(req, context), country: geo.country && geo.country.code, region: geo.subdivision && geo.subdivision.code, city: geo.city };
  const list = Array.isArray(raw) ? raw : Array.isArray(raw.events) ? raw.events : [raw];
  const events = list.slice(0, 50).map((e) => normalizeEvent(e, server)).filter(Boolean);
  if (!events.length) return json({ error: "no valid events" }, 400);

  const results = await Promise.allSettled(events.map(writeEvent));
  const failed = results.filter((r) => r.status === "rejected");
  if (failed.length) console.error("[track] store failures", failed.map((f) => String(f.reason)).join("; "));

  // Mirror key events to Meta server-side (dedupes with the pixel by event_id).
  const mirrored = events.filter((e) => MIRRORED[e.type]).map((e) => ({
    event_name: MIRRORED[e.type],
    event_id: e.event_id,
    event_time: Math.floor(Date.parse(e.ts) / 1000),
    event_source_url: e.page ? `https://${req.headers.get("host")}${e.page}` : undefined,
    user_data: userData({ fbp: e.fbp, fbc: e.fbc, ip: server.ip, ua: e.ctx.ua, externalId: e.visitor_id }),
    custom_data: { step: e.step, question_id: e.question_id, survey_version: e.survey_version }
  }));
  if (mirrored.length) await sendCapi(mirrored);

  return json({ ok: true, stored: events.length - failed.length }, failed.length === events.length ? 500 : 200);
};

export const config = { path: "/api/track" };
