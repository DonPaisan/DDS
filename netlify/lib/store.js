import { getStore } from "@netlify/blobs";

const opts = () => (process.env.NETLIFY_BLOBS_CONTEXT || process.env.NETLIFY ? {} : { siteID: process.env.NETLIFY_SITE_ID, token: process.env.NETLIFY_TOKEN });

export const eventsStore = () => getStore({ name: "events", ...opts() });
export const leadsStore = () => getStore({ name: "leads", ...opts() });

export function eventKey(ev) {
  const day = ev.ts.slice(0, 10);
  const sid = (ev.session_id || "").replace(/[^a-zA-Z0-9-]/g, "").slice(0, 12);
  return `${day}/${ev.ts}-${sid}-${ev.event_id.slice(0, 8)}.json`;
}

export async function writeEvent(ev) {
  await eventsStore().setJSON(eventKey(ev), ev);
}

/** Inclusive day range, YYYY-MM-DD strings. */
export function daysBetween(from, to) {
  const out = [];
  const d = new Date(from + "T00:00:00Z");
  const end = new Date(to + "T00:00:00Z");
  while (d <= end && out.length < 62) {
    out.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}

async function readAll(store, prefix, limit) {
  const keys = [];
  let cursor;
  do {
    const page = await store.list({ prefix, cursor });
    for (const b of page.blobs) keys.push(b.key);
    cursor = page.cursor;
  } while (cursor && keys.length < limit);
  const out = [];
  const CHUNK = 25;
  for (let i = 0; i < keys.length && out.length < limit; i += CHUNK) {
    const batch = await Promise.all(keys.slice(i, i + CHUNK).map((k) => store.get(k, { type: "json" }).catch(() => null)));
    for (const b of batch) if (b) out.push(b);
  }
  return out;
}

export async function readEvents(from, to, limit = 50000) {
  const store = eventsStore();
  const out = [];
  for (const day of daysBetween(from, to)) {
    const chunk = await readAll(store, day + "/", limit - out.length);
    out.push(...chunk);
    if (out.length >= limit) break;
  }
  out.sort((a, b) => (a.ts < b.ts ? -1 : a.ts > b.ts ? 1 : 0));
  return out;
}

export async function readLeads(from, to, limit = 5000) {
  const store = leadsStore();
  const out = [];
  for (const day of daysBetween(from, to)) {
    out.push(...(await readAll(store, day + "/", limit - out.length)));
    if (out.length >= limit) break;
  }
  out.sort((a, b) => (a.created_at < b.created_at ? -1 : 1));
  return out;
}
