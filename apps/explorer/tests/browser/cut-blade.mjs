// Scene six (`/stage/cut_up`): the blades, the cut, and the verdict.
//
// Five modes, all against a real Chromium, because none of them is reachable
// from `pytest` — the test client runs no JavaScript, and the whole of this
// scene's cut happens in the browser.
//
//   drag    the blade moves *under the pointer*, sampled while it is still
//           down. A run that only checked where it landed would prove
//           nothing about the gesture.
//   clean   position both blades in gaps, cut, and compare the text the
//           quarters are showing with the `data-checked` the verdict came
//           back carrying. Pins the honesty requirement: what `check` was
//           given is what is on screen.
//   through put the vertical blade inside a word, cut, and read the verdict
//           back — it must name the fragments the blade just made.
//   stale   move a blade *during* the check's round trip (`DELAY`, default
//           600ms) and count real verdicts left standing over a page that is
//           no longer showing what was checked. The invariant this codebase
//           has had broken four times.
//   wedge   stub the route with a 500, and separately with an aborted
//           request, and read back whether the scene can still be driven.
//           htmx does not swap on a non-2xx, so the flag the submit gate
//           reads has no other path back to false — a liveness failure, not
//           a staleness one. Takes `500` (default) or `abort`.
//   frames  first paint, a frame mid-cut, and the cut page with its verdict,
//           written to `OUT` (default /tmp). Also reports the clocked length
//           of the whole cut and the scene's own content extent.
//
// `BASE` defaults to http://127.0.0.1:8477. `REDUCED=1` runs under the
// `reducedMotion: 'reduce'` **context option** (never the launch flag), where
// the quarters must arrive at their rearranged positions at once and the
// blades must still drag.
import { chromium } from 'playwright';

const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const OUT = process.env.OUT || '/tmp';
const REDUCED = process.env.REDUCED === '1';
const DELAY = Number(process.env.DELAY || 600);
const mode = process.argv[2] || 'drag';

function log(...args) {
  console.log(...args);
}

async function open(browser) {
  const context = await browser.newContext({
    viewport: { width: 1320, height: 860 },
    reducedMotion: REDUCED ? 'reduce' : 'no-preference',
  });
  const page = await context.newPage();
  page.on('pageerror', (e) => log('PAGEERROR', e.message));
  await page.goto(`${BASE}/stage/cut_up?chrome=off`);
  await page.waitForFunction(() => typeof geom !== 'undefined' && geom !== null);
  return page;
}

// Where the blades are, in client coordinates, so the pointer can be put on
// them without the harness duplicating the page's own arithmetic.
async function bladeBox(page, which) {
  // Deliberately off the middle of the blade: the two blades cross, and at
  // the crossing the one painted last is the one a pointer hits. A harness
  // that pressed at the centre of the vertical blade would grab the
  // horizontal one and measure nothing.
  return page.evaluate((w) => {
    const el = document.getElementById(w === 'h' ? 'cutup-blade-h' : 'cutup-blade-v');
    const r = el.getBoundingClientRect();
    return {
      x: w === 'h' ? r.left + r.width * 0.2 : r.left + r.width / 2,
      y: w === 'h' ? r.top + r.height / 2 : r.top + r.height * 0.15,
      left: r.left,
      top: r.top,
    };
  }, which);
}

async function state(page) {
  return page.evaluate(() => ({
    bladeX: bladeX,
    gapIndex: gapIndex,
    cutState: cutState,
    activeBlades: activeBlades,
    cutToken: cutToken,
    through: geom.lines.filter((l) => wordAt(l, splitIndex(l, bladeX)) !== null).length,
    verdict: (() => {
      const v = document.querySelector('#cutup-result .verdict');
      return v ? { cls: v.className, text: v.textContent.trim(), checked: v.dataset.checked } : null;
    })(),
    shown: (() => {
      const rowsOf = (key) =>
        Array.from(
          document.querySelectorAll(`[data-piece="${key}"] .cutup-piece-line`)
        ).map((el) => el.textContent.trim());
      const out = [];
      [['d', 'a'], ['b', 'c']].forEach(([l, r]) => {
        const left = rowsOf(l);
        const right = rowsOf(r);
        for (let i = 0; i < Math.max(left.length, right.length); i++) {
          const row = [left[i] || '', right[i] || ''].filter((s) => s !== '').join(' ');
          if (row !== '') out.push(row);
        }
      });
      return out.join('\n');
    })(),
  }));
}

// Wait for a real (checked) verdict, or give up.
async function waitVerdict(page, ms = 5000) {
  try {
    await page.waitForFunction(
      () => {
        const v = document.querySelector('#cutup-result .verdict');
        return v && !v.classList.contains('turning');
      },
      { timeout: ms }
    );
  } catch (e) {
    /* the caller reports what it found */
  }
  return state(page);
}

async function cut(page) {
  await page.click('#cutup-cut');
  return waitVerdict(page);
}

// ── drag ────────────────────────────────────────────────────────────────────
// The blade has to move while the pointer is down, not on release.
async function runDrag(page) {
  for (const which of ['v', 'h']) {
    const box = await bladeBox(page, which);
    const before = await state(page);
    await page.mouse.move(box.x, box.y);
    await page.mouse.down();
    const samples = [];
    const span = 160;
    for (let step = 8; step <= span; step += 8) {
      if (which === 'v') await page.mouse.move(box.x - step, box.y);
      else await page.mouse.move(box.x, box.y + step);
      const s = await state(page);
      samples.push({
        asked: step,
        got: which === 'v' ? s.bladeX : s.gapIndex,
        held: s.activeBlades,
        verdict: s.verdict ? s.verdict.cls : null,
      });
    }
    await page.mouse.up();
    const after = await state(page);
    const moved = samples.filter((s, i) =>
      i === 0 ? true : s.got !== samples[i - 1].got
    ).length;
    const live = samples.filter((s) =>
      which === 'v' ? Math.abs(before.bladeX - s.got - s.asked) < 1.5 : true
    ).length;
    const heldThroughout = samples.every((s) => s.held === 1);
    const noRealVerdict = samples.every((s) => s.verdict === null || /turning/.test(s.verdict));
    log(
      `${which}: ${samples.length} samples, ${moved} distinct positions,` +
        ` live-under-pointer ${which === 'v' ? live : 'n/a'}/${samples.length},` +
        ` held throughout ${heldThroughout}, real verdict under the pointer ${!noRealVerdict}`
    );
    log(
      `   before ${which === 'v' ? before.bladeX.toFixed(2) : before.gapIndex}` +
        ` -> after ${which === 'v' ? after.bladeX.toFixed(2) : after.gapIndex},` +
        ` activeBlades after release ${after.activeBlades}`
    );
  }
}

// ── clean / through ─────────────────────────────────────────────────────────
// Put the vertical blade at a chosen x and cut.
async function placeBlade(page, x) {
  const box = await bladeBox(page, 'v');
  const originX = await page.evaluate(
    () => document.getElementById('cutup-blades').getBoundingClientRect().left
  );
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  await page.mouse.move(originX + x, box.y, { steps: 6 });
  await page.mouse.up();
  return state(page);
}

// An x the page itself says misses every word, and one it says goes through
// the most. Asked of the page rather than computed here — the whole point is
// that the page's own arithmetic is the authority.
async function columns(page) {
  return page.evaluate(() => {
    const scores = [];
    for (let x = 0; x <= geom.width; x += 1) {
      let n = 0;
      geom.lines.forEach((l) => {
        if (wordAt(l, splitIndex(l, x)) !== null) n++;
      });
      scores.push({ x: x, through: n });
    }
    const clean = scores.filter((s) => s.through === 0);
    const middling = scores.filter((s) => s.x > geom.width * 0.3 && s.x < geom.width * 0.7);
    return {
      cleanCount: clean.length,
      cleanAt: clean.length ? clean[Math.floor(clean.length / 2)].x : null,
      worst: middling.reduce((a, b) => (b.through > a.through ? b : a)),
    };
  });
}

async function runClean(page) {
  const cols = await columns(page);
  log(`columns that miss every word: ${cols.cleanCount}; using x=${cols.cleanAt}`);
  const placed = await placeBlade(page, cols.cleanAt);
  log(`blade at ${placed.bladeX.toFixed(2)}, through ${placed.through} words, gap ${placed.gapIndex}`);
  const s = await cut(page);
  log(`verdict: ${s.verdict ? s.verdict.cls : '(none)'} — ${s.verdict ? s.verdict.text : ''}`);
  log('--- the page is showing:');
  log(s.shown);
  log(`--- checked text == shown text: ${s.verdict && s.verdict.checked === s.shown}`);
}

async function runThrough(page) {
  const cols = await columns(page);
  log(`worst column: x=${cols.worst.x}, through ${cols.worst.through} words`);
  const placed = await placeBlade(page, cols.worst.x);
  log(`blade at ${placed.bladeX.toFixed(2)}, through ${placed.through} words`);
  const marked = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.cutup-cut-through')).map((e) => e.textContent)
  );
  log(`marked live on the uncut page: ${JSON.stringify(marked)}`);
  const s = await cut(page);
  log(`verdict: ${s.verdict ? s.verdict.cls : '(none)'} — ${s.verdict ? s.verdict.text : ''}`);
  const named = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.cutup-violations li')).map((e) =>
      e.textContent.replace(/\s+/g, ' ').trim()
    )
  );
  named.forEach((n) => log(`  ${n}`));
  const fragments = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.cutup-fragment')).map((e) => e.textContent)
  );
  log(`fragments on the page: ${JSON.stringify(fragments)}`);
  log('--- the page is showing:');
  log(s.shown);
  log(`--- checked text == shown text: ${s.verdict && s.verdict.checked === s.shown}`);
}

// ── stale ───────────────────────────────────────────────────────────────────
// A real verdict must never stand over a page the viewer has changed since.
async function runStale(page) {
  await page.route('**/stage/cut_up/act', async (route) => {
    await new Promise((r) => setTimeout(r, DELAY));
    await route.continue();
  });
  const cols = await columns(page);
  await placeBlade(page, cols.cleanAt);
  // Cut, then move a blade while the check is still in flight, and let go.
  await page.click('#cutup-cut');
  await page.waitForFunction(() => cutState === 'cut', { timeout: 8000 });
  const box = await bladeBox(page, 'v');
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  await page.mouse.move(box.x - 40, box.y, { steps: 4 });
  await page.mouse.up();
  const duringToken = await page.evaluate(() => cutToken);
  // Watch until well past the response.
  const seen = [];
  for (let i = 0; i < 40; i++) {
    seen.push(await state(page));
    await page.waitForTimeout(50);
  }
  const standing = seen.filter(
    (s) => s.verdict && !/turning/.test(s.verdict.cls)
  );
  const final = seen[seen.length - 1];
  log(`delay ${DELAY}ms, reduced ${REDUCED}`);
  log(`real verdicts standing after the blade moved: ${standing.length}/${seen.length}`);
  log(`final: cutState=${final.cutState} verdict=${final.verdict ? final.verdict.cls : '(none)'}` +
    ` "${final.verdict ? final.verdict.text : ''}"`);
  log(`token at the move ${duringToken}, now ${final.cutToken}; page in pieces: ${final.shown !== ''}`);
}

// ── frames ──────────────────────────────────────────────────────────────────
async function extent(page) {
  return page.evaluate(() => {
    const stage = document.getElementById('stage');
    const top = stage.getBoundingClientRect().top;
    let deepest = 0;
    stage.querySelectorAll('*').forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.width > 0 || r.height > 0) deepest = Math.max(deepest, r.bottom - top);
    });
    return { deepest: deepest, blank: 720 - deepest };
  });
}

async function runFrames(page) {
  await page.screenshot({ path: `${OUT}/cutup-before.png` });
  log(`uncut: ${JSON.stringify(await extent(page))}`);
  const cols = await columns(page);
  await placeBlade(page, cols.worst.x);
  // Clock the whole cut, inside the page, from the click to the moment the
  // quarters have landed and the text has been read out of them.
  await page.evaluate(() => {
    window.__cutClock = { start: performance.now(), end: null };
    const original = window.readAssembledText;
    window.readAssembledText = function () {
      window.__cutClock.end = performance.now();
      return original.apply(this, arguments);
    };
  });
  const clicked = page.click('#cutup-cut');
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${OUT}/cutup-mid.png` });
  await clicked;
  await waitVerdict(page);
  await page.screenshot({ path: `${OUT}/cutup-after.png` });
  const clock = await page.evaluate(() => window.__cutClock);
  log(`cut clocked at ${(clock.end - clock.start).toFixed(1)}ms (click to quarters landed)`);
  log(`cut: ${JSON.stringify(await extent(page))}`);
  // The worst case for height: the horizontal blade in the topmost gap.
  await page.evaluate(() => {
    invalidate();
    gapIndex = 1;
    drawBlades();
  });
  await page.click('#cutup-cut');
  await waitVerdict(page);
  log(`cut with the horizontal blade in gap 1: ${JSON.stringify(await extent(page))}`);
  await page.screenshot({ path: `${OUT}/cutup-gap1.png` });
  // And the passing case, which is the finding this scene is built on.
  await page.evaluate(() => {
    invalidate();
    gapIndex = 3;
    drawBlades();
  });
  await placeBlade(page, cols.cleanAt);
  const clean = await cut(page);
  log(`clean cut: ${clean.verdict ? clean.verdict.text : '(none)'}`);
  log(`clean cut extent: ${JSON.stringify(await extent(page))}`);
  await page.screenshot({ path: `${OUT}/cutup-clean.png` });
}

// ── wedge ───────────────────────────────────────────────────────────────────
// A request that never gets a swap must not take the scene with it.
async function runWedge(page) {
  const kind = process.argv[3] === 'abort' ? 'abort' : '500';
  await page.route('**/stage/cut_up/act', async (route) => {
    if (kind === 'abort') await route.abort('failed');
    else await route.fulfill({ status: 500, body: 'nope' });
  });
  const controls = () =>
    page.evaluate(() => ({
      inert: inert,
      cutState: cutState,
      cutDisabled: document.getElementById('cutup-cut').disabled,
      freshDisabled: document.getElementById('cutup-fresh').disabled,
      says: (() => {
        const v = document.querySelector('#cutup-result .verdict');
        return v ? v.textContent.trim() : null;
      })(),
    }));
  await page.click('#cutup-cut');
  await page.waitForTimeout(2500);
  log(`${kind}: ${JSON.stringify(await controls())}`);
  // Can a hand get the scene back? Move a blade, the way a viewer would.
  const box = await bladeBox(page, 'v');
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  await page.mouse.move(box.x - 60, box.y, { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(300);
  log(`  after moving a blade: ${JSON.stringify(await controls())}`);
}

const browser = await chromium.launch();
const page = await open(browser);
const modes = {
  drag: runDrag,
  clean: runClean,
  through: runThrough,
  stale: runStale,
  wedge: runWedge,
  frames: runFrames,
};
if (!modes[mode]) {
  log(`unknown mode ${mode}; one of ${Object.keys(modes).join(', ')}`);
} else {
  await modes[mode](page);
}
await browser.close();
