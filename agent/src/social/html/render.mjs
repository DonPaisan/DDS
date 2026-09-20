// Screenshot HTML slides with headless Chromium.
//   node render.mjs jobs.json
// jobs.json: [{ "html": "/abs/slide.html", "out": "/abs/slide.jpg", "width": 1080, "height": 1350 }, ...]
import fs from "node:fs";
import { pathToFileURL } from "node:url";

async function loadPlaywright() {
  try { return await import("playwright"); } catch {}
  try { return await import("/opt/node22/lib/node_modules/playwright/index.mjs"); } catch {}
  throw new Error("playwright not found: npm i playwright && npx playwright install chromium");
}

const jobs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const { chromium } = await loadPlaywright();
const launch = { args: ["--font-render-hinting=none"] };
if (process.env.CHROME_PATH) launch.executablePath = process.env.CHROME_PATH;
let browser;
try { browser = await chromium.launch(launch); }
catch (e) {
  if (fs.existsSync("/opt/pw-browsers/chromium/chrome-linux/chrome")) browser = await chromium.launch({ ...launch, executablePath: "/opt/pw-browsers/chromium/chrome-linux/chrome" });
  else throw e;
}
const ctx = await browser.newContext({ deviceScaleFactor: 1 });
const page = await ctx.newPage();
for (const j of jobs) {
  await page.setViewportSize({ width: j.width, height: j.height });
  await page.goto(pathToFileURL(j.html).href, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: j.out, type: "jpeg", quality: 92, clip: { x: 0, y: 0, width: j.width, height: j.height } });
}
await browser.close();
console.log(`rendered ${jobs.length}`);
