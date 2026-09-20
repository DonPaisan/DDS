import { test } from "node:test";
import assert from "node:assert/strict";
import { readAll, readDay, daysBetween, eventKey } from "../lib/store.js";

/** In-memory stand-in for a Netlify Blobs Store with paginated list(). */
function fakeStore(entries, pageSize = 2) {
  const data = new Map(Object.entries(entries));
  return {
    data,
    async get(key, { type } = {}) { const v = data.get(key); return v == null ? null : type === "json" ? v : JSON.stringify(v); },
    async setJSON(key, v) { data.set(key, v); },
    list({ prefix, paginate }) {
      const keys = [...data.keys()].filter((k) => k.startsWith(prefix)).sort();
      const pages = [];
      for (let i = 0; i < keys.length; i += pageSize) pages.push({ blobs: keys.slice(i, i + pageSize).map((key) => ({ key, etag: "x" })), directories: [] });
      if (!pages.length) pages.push({ blobs: [], directories: [] });
      if (!paginate) return Promise.resolve(pages[0]);
      return (async function* () { for (const p of pages) yield p; })();
    }
  };
}

test("daysBetween is inclusive", () => {
  assert.deepEqual(daysBetween("2026-09-18", "2026-09-20"), ["2026-09-18", "2026-09-19", "2026-09-20"]);
});

test("eventKey is under the day prefix and has no leading slash", () => {
  const k = eventKey({ ts: "2026-09-20T10:00:00.000Z", session_id: "abc/../x", event_id: "0123456789" });
  assert.ok(k.startsWith("2026-09-20/"));
  assert.ok(!k.startsWith("/"));
  assert.ok(Buffer.byteLength(k) < 600);
});

test("readAll walks every page of a paginated list", async () => {
  const s = fakeStore({ "d/1": { a: 1 }, "d/2": { a: 2 }, "d/3": { a: 3 }, "d/4": { a: 4 }, "d/5": { a: 5 }, "e/1": { a: 9 } }, 2);
  const out = await readAll(s, "d/");
  assert.equal(out.length, 5);
  assert.equal((await readAll(s, "d/", 3)).length, 3);
});

test("readDay rolls up a past day once and reuses the rollup", async () => {
  const s = fakeStore({ "2020-01-01/a": { ts: "2020-01-01T00:00:00Z", type: "page_view" }, "2020-01-01/b": { ts: "2020-01-01T00:00:01Z", type: "lead" } });
  const first = await readDay("2020-01-01", { store: s });
  assert.equal(first.length, 2);
  assert.ok(s.data.has("rollup/2020-01-01.json"));
  s.data.delete("2020-01-01/a"); // even if raw keys vanish, the rollup serves
  const second = await readDay("2020-01-01", { store: s });
  assert.equal(second.length, 2);
});

test("readDay never rolls up today", async () => {
  const today = new Date().toISOString().slice(0, 10);
  const s = fakeStore({ [`${today}/a`]: { ts: today, type: "page_view" } });
  await readDay(today, { store: s });
  assert.ok(!s.data.has(`rollup/${today}.json`));
});
