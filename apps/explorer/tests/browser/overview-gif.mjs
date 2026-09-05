// The overview recording: what this package is, in one pass, with the machines
// actually running.
//
// Not a reproduction like its neighbours here — those exist because a race was
// found three times and the harness that caught it should outlive the task.
// This one produces an artefact: a GIF showing the catalogue, every scene on
// the stage being *driven*, and a local model checking and generating through
// the MCP server.
//
// It lives here anyway, and not in a scripts/ directory, because it needs
// exactly what they need — a real Chromium against a running server — and
// splitting that setup across two places would give the next reader two ways
// to drive this app instead of one.
//
// The GIF is assembled separately, by `scripts/build_overview_gif.py`, because
// Playwright has no GIF encoder and shelling out to one from here would make
// this script depend on whatever happens to be installed.
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
  await page.screenshot({ path: `${OUT}/${String(n++).padStart(4, "0")}-${label}.png` });
};

/** Hold on a still frame. Duplicated frames are what makes a GIF readable, and
 *  the encoder collapses each run into one frame with a longer delay, so a hold
 *  costs almost nothing in the finished file. */
const hold = async (page, label, frames) => {
  for (let i = 0; i < frames; i += 1) await shot(page, label);
};

/** Film *while something moves*. The difference from `hold` is the wait between
 *  shots: these frames are meant to differ, and the encoder keeps every one that
 *  does. A screenshot costs 50-100ms on its own, so the real cadence is that
 *  plus `gap` — close enough to a CSS transition's visible span to catch it in
 *  flight rather than only at its two ends. */
const film = async (page, label, frames, gap = 55) => {
  for (let i = 0; i < frames; i += 1) {
    await shot(page, label);
    await page.waitForTimeout(gap);
  }
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

/** Click a selector if it is there, and report whether it was.
 *
 *  Tolerant on purpose: a scene that gains or loses a control should cost that
 *  scene its motion in this recording, not abort a twenty-minute run. The run
 *  prints a frame count per scene, so a silent miss still shows as a scene that
 *  produced only its holds. */
const clickIfPresent = async (page, selector) => {
  const target = page.locator(selector).first();
  if ((await target.count()) === 0) {
    // Loud, because silent was expensive: a missed selector used to leave a
    // scene with only its holds, and the sole evidence was a frame count in a
    // list of nine. A scene that does not move is the one thing this recording
    // exists to avoid.
    console.log(`    !! nothing matched ${selector} — this scene will not move`);
    return false;
  }
  await target.click();
  return true;
};

// What to do on each scene once it has loaded. Every entry drives the machine
// and films the result: a scene sitting still is a screenshot, and the whole
// argument for the stage is that these things move.
//
// Keyed by slug rather than by position, so a scene added to or reordered in
// `stage.SCENES` cannot silently drive the wrong control.
const CHOREOGRAPHY = {
  // Turn the five rings and read the word they spell. `Turn them for me` is the
  // server-side spin; the drag is the other way in and cannot be filmed without
  // simulating a pointer, which `drag-turn.mjs` already does properly.
  denckring: async (page) => {
    await hold(page, "scene-denckring", 6);
    if (await clickIfPresent(page, 'button[name="turn"]')) {
      await film(page, "scene-denckring-turn", 14);
    }
    await hold(page, "scene-denckring-read", 8);
  },

  ideenwuerfeln: async (page) => {
    await hold(page, "scene-ideenwuerfeln", 5);
    // A headword first, or the throw is a *random* draw and the scene shows one
    // slip. The collision across fields is the procedure; a single slip is the
    // fallback it degrades to. Typed rather than picked from the datalist so
    // the field is visibly filled on camera.
    const field = page.locator('input[name="headword"]').first();
    if ((await field.count()) > 0) {
      await field.fill("control");
      await page.waitForTimeout(200);
      await hold(page, "scene-ideenwuerfeln-headword", 5);
    }
    // `form.throw-form`, not `form.actions` — this scene's form carries the
    // corpus picker and is classed for it. The wrong selector cost two whole
    // recordings: `clickIfPresent` returned false, the scene produced its holds
    // and nothing else, and a frame count is not something anyone reads.
    if (await clickIfPresent(page, 'form.throw-form button[type="submit"]')) {
      // Long enough for every slip to arrive. The throw returns three across
      // three distinct fields — that collision *is* the procedure — and they
      // fade in one after another, so a short film plus a back-to-back hold
      // caught only the first and showed the scene as a single excerpt.
      await film(page, "scene-ideenwuerfeln-throw", 20);
      await page.waitForTimeout(700);
    }
    await hold(page, "scene-ideenwuerfeln-thrown", 10);
  },

  n_plus_7: async (page) => {
    await hold(page, "scene-n_plus_7", 5);
    if (await clickIfPresent(page, 'form.actions button[type="submit"]')) {
      await film(page, "scene-n_plus_7-displace", 12);
    }
    await hold(page, "scene-n_plus_7-displaced", 8);
  },

  // Deal a fresh sonnet, then flip a single strip: the deal shows the machine,
  // the flip shows what the machine is *for* — one line changing while the
  // other thirteen hold.
  cent_mille_milliards: async (page) => {
    await hold(page, "scene-queneau", 5);
    if (await clickIfPresent(page, 'form[hx-post*="/deal"] button[type="submit"]')) {
      await film(page, "scene-queneau-deal", 12);
      await page.waitForTimeout(400);
    }
    if (await clickIfPresent(page, 'form[hx-post*="/flip"] button')) {
      await film(page, "scene-queneau-flip", 12);
    }
    await hold(page, "scene-queneau-flipped", 8);
  },

  // The rungs arrive one after another under a CSS animation keyed off `--i`,
  // so this is one of the scenes where filming matters most.
  word_ladder: async (page) => {
    await hold(page, "scene-word_ladder", 5);
    if (await clickIfPresent(page, 'form.actions button[type="submit"]')) {
      await film(page, "scene-word_ladder-climb", 16);
    }
    await hold(page, "scene-word_ladder-climbed", 8);
  },

  // Two blades and four quarters, all of it in the browser.
  cut_up: async (page) => {
    await hold(page, "scene-cut_up", 6);
    if (await clickIfPresent(page, "#cutup-cut")) {
      await film(page, "scene-cut_up-cut", 18);
    }
    await hold(page, "scene-cut_up-cut-done", 8);
  },

  llull_figure: async (page) => {
    await hold(page, "scene-llull", 5);
    if (await clickIfPresent(page, 'button[name="turn"]')) {
      await film(page, "scene-llull-turn", 14);
    }
    await hold(page, "scene-llull-turned", 8);
  },

  // 426 cells clattering. The longest animation on the stage and the one most
  // worth the frames, so it gets the tightest gap.
  poesie_automat: async (page) => {
    await hold(page, "scene-automat", 5);
    if (await clickIfPresent(page, "#automat-press")) {
      await film(page, "scene-automat-press", 26, 45);
    }
    await hold(page, "scene-automat-pressed", 10);
  },

  // The one scene with an input device of its own, so the recording uses it:
  // the number is *typed on the keypad*, a frame per key, before anything is
  // turned. Clearing first because the scene arrives carrying its example, and
  // a viewer who never sees an empty display cannot tell that the digits are
  // being entered rather than animated.
  //
  // The display turns over under a 700ms transform, so the default gap lands
  // roughly a dozen frames inside it.
  calculator_word: async (page) => {
    await hold(page, "scene-calculator", 5);
    if (await clickIfPresent(page, "#calc-clear")) {
      await hold(page, "scene-calculator-clear", 3);
      for (const digit of "7353") {
        await clickIfPresent(page, `.calc-key[data-digit="${digit}"]`);
        await hold(page, `scene-calculator-key-${digit}`, 4);
      }
    }
    if (await clickIfPresent(page, 'form.actions button[type="submit"]')) {
      await film(page, "scene-calculator-turn", 14);
    }
    await hold(page, "scene-calculator-turned", 10);
  },
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
  await scrollThrough(page, "board-scroll", 26);
  await page.evaluate(() => window.scrollTo(0, 0));
  await hold(page, "board-top", 5);

  // ── 2. every scene on the stage, driven ─────────────────────────────────
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
    await page.waitForTimeout(500);
    const drive = CHOREOGRAPHY[slug];
    const before = n;
    if (drive) {
      await drive(page);
    } else {
      // A new scene with no entry above still appears, still still. Named in
      // the log so it is obvious which one wants choreography.
      console.log(`  ${slug}: NO CHOREOGRAPHY — holding`);
      await hold(page, `scene-${slug}`, 12);
    }
    console.log(`  ${slug}: ${n - before} frames`);
  }

  // ── 3. the local model, through the MCP server ──────────────────────────
  await page.goto(`${BASE}/agent`, { waitUntil: "networkidle" });
  await hold(page, "agent", 8);

  for (const [index, label] of [
    ["0", "check"],
    ["1", "apply"],
  ]) {
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
    await hold(page, `agent-${label}-answered`, 24);
    await scrollThrough(page, `agent-${label}-scroll`, 12);
    await page.evaluate(() => window.scrollTo(0, 0));
  }

  await browser.close();
  console.log(`${n} frames in ${OUT}`);
};

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
