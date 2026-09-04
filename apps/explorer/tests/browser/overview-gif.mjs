// The overview recording: what this package is, in one pass.
//
// Not a reproduction like its neighbours here — those exist because a race was
// found three times and the harness that caught it should outlive the task.
// This one produces an artefact: a GIF showing the catalogue, every scene on
// the stage, and a local model checking and generating through the MCP server.
//
// It lives here anyway, and not in a scripts/ directory, because it needs
// exactly what they need — a real Chromium against a running server — and
// splitting that setup across two places would give the next reader two ways
// to drive this app instead of one.
//
//   frames   write PNG frames to a directory and stop. The GIF is assembled
//            separately, by `scripts/build_overview_gif.py`, because Playwright
//            has no GIF encoder and shelling out to one from here would make
//            this script depend on whatever happens to be installed.
//
// Usage:  node tests/browser/overview-gif.mjs [baseURL] [outDir]
//
// The MCP leg is the slow part and the reason for the long timeouts: a 9.6 GB
// model answering on CPU takes tens of seconds, and the page is deliberately
// not streaming, so nothing appears until it is done.

import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const BASE = process.argv[2] ?? "http://127.0.0.1:8412";
const OUT = process.argv[3] ?? "/tmp/denckring-overview";

// 1280x720 is the stage's own frame — `stage.py` says so, and every scene is
// built with `overflow: hidden` at exactly this size. Recording at any other
// size would crop or letterbox eight of the nine scenes.
const WIDTH = 1280;
const HEIGHT = 720;

let n = 0;
const shot = async (page, label) => {
  const name = `${String(n++).padStart(4, "0")}-${label}.png`;
  await page.screenshot({ path: `${OUT}/${name}` });
};

/** Hold on a frame. Duplicated frames are what makes a GIF readable: without
 *  them every beat lasts one frame and the eye has nothing to settle on. */
const hold = async (page, label, frames) => {
  for (let i = 0; i < frames; i += 1) await shot(page, label);
};

/** Scroll the whole document past the viewport, a frame per step. */
const scrollThrough = async (page, label, steps) => {
  const height = await page.evaluate(() => document.body.scrollHeight);
  const span = Math.max(height - HEIGHT, 0);
  for (let i = 0; i <= steps; i += 1) {
    await page.evaluate((y) => window.scrollTo(0, y), (span * i) / steps);
    await page.waitForTimeout(60);
    await shot(page, label);
  }
};

const main = async () => {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT } });

  // ── 1. the catalogue, scrolled ──────────────────────────────────────────
  // The board rather than the case: it is the one page that shows every
  // catalogued row at once, which is what "all the procedures" has to mean.
  await page.goto(`${BASE}/board`, { waitUntil: "networkidle" });
  await hold(page, "board", 8);
  await scrollThrough(page, "board-scroll", 40);
  await page.evaluate(() => window.scrollTo(0, 0));
  await hold(page, "board-top", 6);

  // ── 2. every scene on the stage ─────────────────────────────────────────
  // `?chrome=off` strips the caption and the surrounding page, which is what
  // that flag exists for: the scenes were built to be recorded.
  const scenes = await page.evaluate(async (base) => {
    const response = await fetch(`${base}/stage`);
    const html = await response.text();
    return [...html.matchAll(/href="\/stage\/([a-z_0-9]+)"/g)]
      .map((m) => m[1])
      .filter((slug, i, all) => all.indexOf(slug) === i);
  }, BASE);
  if (scenes.length === 0) throw new Error("no scenes found on /stage");
  console.log(`scenes: ${scenes.join(", ")}`);

  for (const slug of scenes) {
    await page.goto(`${BASE}/stage/${slug}?chrome=off`, { waitUntil: "networkidle" });
    await page.waitForTimeout(400);
    await hold(page, `scene-${slug}`, 14);
  }

  // ── 3. the local model, through the MCP server ──────────────────────────
  await page.goto(`${BASE}/agent`, { waitUntil: "networkidle" });
  await hold(page, "agent", 10);

  for (const [index, label] of [["0", "check"], ["1", "apply"]]) {
    const buttons = page.locator("button.preset");
    if ((await buttons.count()) <= Number(index)) continue;
    await buttons.nth(Number(index)).click();
    await page.waitForTimeout(300);
    await hold(page, `agent-${label}-asked`, 6);

    // Empty the panel before asking. Without this the second run's wait is
    // satisfied instantly by the *first* run's transcript, which is still in the
    // DOM until htmx swaps — so the frames labelled "answered" showed the
    // previous answer with "asking the model…" still on screen beside it.
    await page.evaluate(() => {
      document.getElementById("transcript").innerHTML = "";
    });
    await page.locator('button[type="submit"]').click();
    // The model is the slow part: tens of seconds on CPU, and the page does
    // not stream, so the transcript appears all at once when it is done.
    await page
      .locator("#transcript .agent-steps, #transcript .agent-problem")
      .first()
      .waitFor({ timeout: 240_000 });
    await page.waitForTimeout(500);
    // Dwell on the transcript, not on the form. Holding at the top of the page
    // shows a frame in which nothing has visibly changed — the calls are below
    // the fold, and they are the entire point of this section.
    await page
      .locator("#transcript")
      .scrollIntoViewIfNeeded()
      .catch(() => {});
    await page.waitForTimeout(250);
    await hold(page, `agent-${label}-answered`, 26);
    await scrollThrough(page, `agent-${label}-scroll`, 14);
    await page.evaluate(() => window.scrollTo(0, 0));
  }

  await browser.close();
  console.log(`${n} frames in ${OUT}`);
};

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
