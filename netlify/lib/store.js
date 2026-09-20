import { getStore } from "@netlify/blobs";

// Outside Netlify (local scripts) the store needs explicit credentials.
const opts = () => (process.env.NETLIFY_BLOBS_CONTEXT || process.env.NETLIFY ? {} : { siteID: process.env.NETLIFY_SITE_ID, token: process.env.NETLIFY_TOKEN });

export const eventsStore = (consistency = "eventual") => getStore({ name: "events", consistency, ...opts() });
export const leadsStore = (consistency = "eventual") => getStore({ name: "leads", consistency, ...opts() });

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

/** List every key under a prefix. `list({paginate:true})` yields pages of ≤1000. */
export async function listKeys(store, prefix, limit = Infinity) {
  const keys = [];
  for await (const page of store.list({ prefix, paginate: true })) {
    for (const b of page.blobs) keys.push(b.key);
    if (keys.length >= limit) break;
  }
  return keys.slice(0, limit);
}

/** Read every JSON blob under a prefix, a few at a time. */
export async function readAll(store, prefix, limit = Infinity, concurrency = 25) {
  const keys = await listKeys(store, prefix, limit);
  const out = [];
  for (let i = 0; i < keys.length; i += concurrency) {
    const batch = await Promise.all(keys.slice(i, i + concurrency).map((k) => store.get(k, { type: "json" }).catch(() => null)));
    for (const b of batch) if (b) out.push(b);
  }
  return out;
}

const todayKey = () => new Date().toISOString().slice(0, 10);

/**
 * Events for one day. Past days are rolled up into a single `rollup/<day>.json`
 * blob the first time they're read, so repeat reads (dashboard, daily agent
 * pull) are one request instead of thousands. Today is always read live.
 */
export async function readDay(day, { store = eventsStore("strong"), rollup = true } = {}) {
  const isPast = day < todayKey();
  if (isPast && rollup) {
    const cached = await store.get(`rollup/${day}.json`, { type: "json" }).catch(() => null);
    if (cached && Array.isArray(cached.events)) return cached.events;
  }
  const events = await readAll(store, day + "/");
  if (isPast && rollup && events.length) {
    await store.setJSON(`rollup/${day}.json`, { day, count: events.length, built_at: new Date().toISOString(), events }).catch(() => {});
  }
  return events;
}

export async function readEvents(from, to, limit = 50000) {
  const store = eventsStore("strong");
  const out = [];
  for (const day of daysBetween(from, to)) {
    out.push(...(await readDay(day, { store })));
    if (out.length >= limit) break;
  }
  out.sort((a, b) => (a.ts < b.ts ? -1 : a.ts > b.ts ? 1 : 0));
  return out.slice(0, limit);
}

export async function readLeads(from, to, limit = 5000) {
  const store = leadsStore("strong");
  const out = [];
  for (const day of daysBetween(from, to)) {
    out.push(...(await readAll(store, day + "/", limit - out.length)));
    if (out.length >= limit) break;
  }
  out.sort((a, b) => (a.created_at < b.created_at ? -1 : 1));
  return out;
}
