/* Local dev server: serves site/ and stubs /api/track, /api/lead, /api/report
 * into a JSONL file so you can click through the funnel without Netlify.
 *   node scripts/serve.mjs [port]     → http://localhost:8787
 * Events land in .local/events.jsonl, leads in .local/leads.jsonl. */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { normalizeEvent, newId } from "../netlify/lib/util.js";
import { summarize, diagnose } from "../netlify/lib/funnel.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const site = path.join(root, "site");
const local = path.join(root, ".local");
fs.mkdirSync(local, { recursive: true });
const eventsFile = path.join(local, "events.jsonl");
const leadsFile = path.join(local, "leads.jsonl");
const port = Number(process.argv[2] || process.env.PORT || 8787);
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml" };

const readBody = (req) => new Promise((res) => { let b = ""; req.on("data", (c) => (b += c)); req.on("end", () => res(b)); });
const send = (res, status, body, type = "application/json") => { res.writeHead(status, { "content-type": type }); res.end(typeof body === "string" ? body : JSON.stringify(body)); };
const readJsonl = (f) => (fs.existsSync(f) ? fs.readFileSync(f, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l)) : []);

http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://x");
  if (url.pathname === "/api/track" && req.method === "POST") {
    let raw; try { raw = JSON.parse(await readBody(req)); } catch { return send(res, 400, { error: "bad json" }); }
    const list = Array.isArray(raw) ? raw : raw.events || [raw];
    const evs = list.map((e) => normalizeEvent(e, { ip: "127.0.0.1" })).filter(Boolean);
    fs.appendFileSync(eventsFile, evs.map((e) => JSON.stringify(e)).join("\n") + (evs.length ? "\n" : ""));
    return send(res, 200, { ok: true, stored: evs.length });
  }
  if (url.pathname === "/api/lead" && req.method === "POST") {
    let body; try { body = JSON.parse(await readBody(req)); } catch { return send(res, 400, { error: "bad json" }); }
    if (!body.contact || !body.contact.phone || !body.contact.email) return send(res, 400, { error: "invalid" });
    const lead = { lead_id: newId(), created_at: new Date().toISOString(), ...body };
    fs.appendFileSync(leadsFile, JSON.stringify(lead) + "\n");
    const ev = normalizeEvent({ type: "lead", session_id: body.session_id, visitor_id: body.visitor_id, event_id: body.event_id, page: "/api/lead", survey_version: body.survey_version, attr: body.attr, ctx: {}, extra: { lead_id: lead.lead_id, source: "server" } });
    if (ev) fs.appendFileSync(eventsFile, JSON.stringify(ev) + "\n");
    return send(res, 200, { ok: true, lead_id: lead.lead_id });
  }
  if (url.pathname === "/api/report") {
    const events = readJsonl(eventsFile);
    const type = url.searchParams.get("type") || "summary";
    if (type === "events") return send(res, 200, { count: events.length, events });
    if (type === "leads") return send(res, 200, { leads: readJsonl(leadsFile) });
    const summary = summarize(events);
    return send(res, 200, { summary, findings: diagnose(summary) });
  }
  let p = url.pathname === "/" ? "/index.html" : url.pathname;
  const file = path.join(site, path.normalize(p));
  if (!file.startsWith(site) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return send(res, 404, "not found", "text/plain");
  res.writeHead(200, { "content-type": MIME[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
}).listen(port, () => console.log(`DDS local server → http://localhost:${port}  (events: ${eventsFile})`));
