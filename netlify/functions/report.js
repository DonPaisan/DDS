import { json } from "../lib/util.js";
import { readEvents, readLeads } from "../lib/store.js";
import { summarize, diagnose } from "../lib/funnel.js";

function authorized(req) {
  const token = process.env.REPORT_TOKEN;
  if (!token) return false;
  const h = req.headers.get("authorization") || "";
  const url = new URL(req.url);
  return h === `Bearer ${token}` || url.searchParams.get("token") === token;
}

const day = (d) => d.toISOString().slice(0, 10);

export default async (req) => {
  if (!process.env.REPORT_TOKEN) return json({ error: "REPORT_TOKEN not configured" }, 503);
  if (!authorized(req)) return json({ error: "unauthorized" }, 401);
  const url = new URL(req.url);
  const to = url.searchParams.get("to") || day(new Date());
  const from = url.searchParams.get("from") || day(new Date(Date.now() - 6 * 864e5));
  if (!/^\d{4}-\d{2}-\d{2}$/.test(from) || !/^\d{4}-\d{2}-\d{2}$/.test(to) || from > to) return json({ error: "bad date range" }, 400);
  const type = url.searchParams.get("type") || "summary";

  try {
    if (type === "events") {
      const events = await readEvents(from, to);
      return json({ from, to, count: events.length, events });
    }
    if (type === "leads") {
      const full = url.searchParams.get("full") === "1";
      const leads = (await readLeads(from, to)).map((l) => full ? l : { ...l, contact: { first_name: l.contact.first_name, phone: "***" + l.contact.phone.slice(-4), email: l.contact.email.replace(/^(.).*(@.*)$/, "$1***$2") }, consent: undefined });
      return json({ from, to, count: leads.length, leads });
    }
    const events = await readEvents(from, to);
    const summary = summarize(events);
    const linkClicks = url.searchParams.get("link_clicks");
    const findings = diagnose(summary, { link_clicks: linkClicks ? Number(linkClicks) : null });
    return json({ from, to, summary, findings });
  } catch (err) {
    console.error("[report] failed", err && err.stack);
    return json({ error: "report failed", detail: String(err && err.message) }, 500);
  }
};

export const config = { path: "/api/report" };
