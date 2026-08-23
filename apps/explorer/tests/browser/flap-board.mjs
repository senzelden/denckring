// Scene eight (`/stage/poesie_automat`): the flap-board, its clatter, and the
// verdict on the poem the drums are showing.
//
// Six modes, all against a real Chromium, because none of them is reachable
// from `pytest` — the test client runs no JavaScript, and every flap on this
// board is turned in the browser.
//
//   drag    a drum moves *under the pointer*, sampled while it is still down.
//           A run that only checked where it landed would prove nothing about
//           the gesture. Reports the flap indices crossed, whether the drum
//           tracked the hand, and whether a real verdict was ever on screen
//           while the hand was on the board.
//   press   press the button, clock the whole clatter inside the page, and
//           compare the poem the drums are showing — read cell by cell out of
//           the DOM — with the `data-checked` the verdict came back carrying.
//           Pins the honesty requirement: what `check` was given is what is on
//           the board, never the poem the seed produced.
//   stale   turn a drum *during* the read's round trip (`DELAY`, default
//           600ms) and count real verdicts left standing over a board that has
//           changed since. The invariant this codebase has had broken five
//           times. Also reports whether the read the drag owes was ever paid.
//   wedge   stub the route with a 500, and separately with an aborted request,
//           and read back whether the scene can still be driven. htmx does not
//           swap on a non-2xx, so the flag the submit gate reads has no other
//           path back to false — a liveness failure, not a staleness one, and
//           the placeholder machinery cannot see it. Takes `500` (default) or
//           `abort`.
//   widths  the measurement the whole layout turns on: every drum's rendered
//           width, each line's total against the width the stage leaves, and
//           what a literal board (columns aligned across all six lines) would
//           need instead.
//   frames  first paint, a frame mid-clatter, and the resolved board, written
//           to `OUT` (default /tmp). Also reports the clocked length of the
//           clatter and the scene's own content extent.
//
// `BASE` defaults to http://127.0.0.1:8477. `REDUCED=1` runs under the
// `reducedMotion: 'reduce'` **context option** (never the launch flag), where
// every drum must arrive at its flap at once and the drag must still work.
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
  await page.goto(`${BASE}/stage/poesie_automat?chrome=off`);
  await page.waitForFunction(() => typeof drums !== 'undefined' && drums.length === 36);
  // The board is measured in whole cells and the cell height is a rem, but the
  // *drum widths* are the face's — so nothing is read before the face has
  // actually arrived.
  await page.evaluate(() => document.fonts.ready);
  return page;
}

// Everything the page knows about itself, asked of the page rather than
// reconstructed here.
async function state(page) {
  return page.evaluate(() => ({
    inert: inert,
    clattering: clattering,
    activeDrums: activeDrums,
    boardToken: boardToken,
    submittedToken: submittedToken,
    deferredRead: deferredRead,
    indices: drums.map((d, i) => flapIndex(i)),
    // The poem the drums are showing, by the page's own reader — the same call
    // the submit uses, so the harness cannot disagree with it.
    shown: readBoard(),
    pressDisabled: document.getElementById('automat-press').disabled,
    readDisabled: document.getElementById('automat-read').disabled,
    verdict: (() => {
      const v = document.querySelector('#automat-reading .verdict');
      return v
        ? { cls: v.className, text: v.textContent.trim(), checked: v.dataset.checked }
        : null;
    })(),
  }));
}

async function waitVerdict(page, ms = 12000) {
  try {
    await page.waitForFunction(
      () => {
        const v = document.querySelector('#automat-reading .verdict');
        return v && !v.classList.contains('turning') && !inert && !clattering;
      },
      { timeout: ms }
    );
  } catch (e) {
    /* the caller reports what it found */
  }
  return state(page);
}

async function drumBox(page, slot) {
  return page.evaluate((s) => {
    const r = drums[s].el.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, h: r.height };
  }, slot);
}

// ── drag ────────────────────────────────────────────────────────────────────
async function runDrag(page) {
  const slot = Number(process.argv[3] || 8);
  const box = await drumBox(page, slot);
  const before = await state(page);
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  const samples = [];
  // Three whole flaps' worth of travel, sampled every few pixels.
  const span = Math.round(box.h * 3);
  for (let step = 4; step <= span; step += 4) {
    await page.mouse.move(box.x, box.y + step);
    const s = await page.evaluate(
      (i) => ({
        index: flapIndex(i),
        transform: drums[i].strip.style.transform,
        transition: drums[i].strip.style.transition,
        held: activeDrums,
        text: drums[i].el.getAttribute('aria-valuetext'),
        shownCell: drums[i].cells[flapIndex(i)].textContent.trim(),
        verdict: (() => {
          const v = document.querySelector('#automat-reading .verdict');
          return v ? v.className : null;
        })(),
      }),
      slot
    );
    samples.push({ asked: step, ...s });
  }
  await page.mouse.up();
  await page.waitForTimeout(400);
  const after = await state(page);
  const distinct = samples.filter((s, i) => i === 0 || s.index !== samples[i - 1].index).length;
  // Every flap the drag passed through, in order — a drag that jumped from
  // its start straight to its end would show two, not four.
  const walked = [];
  samples.forEach((s) => {
    if (walked[walked.length - 1] !== s.index) walked.push(s.index);
  });
  log(`drum ${slot}: cell height ${box.h.toFixed(2)}px, dragged ${span}px down`);
  log(`  ${samples.length} samples, ${distinct} distinct flap positions, walked ${JSON.stringify(walked)}`);
  log(`  live under the pointer: transition off on every sample ${samples.every((s) => s.transition === 'none')}`);
  log(`  held throughout: ${samples.every((s) => s.held === 1)}`);
  log(`  aria-valuetext always the cell in the window: ${samples.every((s) => s.text === s.shownCell)}`);
  log(`  real verdict under the pointer: ${samples.some((s) => s.verdict && !/turning/.test(s.verdict))}`);
  log(`  index ${before.indices[slot]} -> ${after.indices[slot]}, activeDrums after release ${after.activeDrums}`);
  const settled = await waitVerdict(page);
  log(`  after release the board read itself: ${settled.verdict ? settled.verdict.cls : '(none)'} — ${settled.verdict ? settled.verdict.text : ''}`);
  log(`  checked text == what the drums show: ${settled.verdict && settled.verdict.checked === settled.shown}`);
}

// ── press ───────────────────────────────────────────────────────────────────
async function runPress(page) {
  // Clocked inside the page: from the click to the frame the last drum has
  // stopped on, off `performance.now()`.
  await page.evaluate(() => {
    window.__clock = { start: null, end: null };
    const original = window.clatterTo;
    window.clatterTo = function (targets) {
      window.__clock.start = performance.now();
      return original.apply(this, arguments).then((v) => {
        window.__clock.end = performance.now();
        return v;
      });
    };
  });
  const before = await state(page);
  await page.click('#automat-press');
  const s = await waitVerdict(page);
  const clock = await page.evaluate(() => window.__clock);
  log(`reduced ${REDUCED}`);
  log(`clatter clocked at ${(clock.end - clock.start).toFixed(1)}ms (first drum released to last drum stopped)`);
  log(`indices ${JSON.stringify(before.indices)}`);
  log(`     -> ${JSON.stringify(s.indices)}`);
  log(`verdict: ${s.verdict ? s.verdict.cls : '(none)'} — ${s.verdict ? s.verdict.text : ''}`);
  log('--- the board is showing:');
  log(s.shown);
  log(`--- checked text == shown text: ${s.verdict && s.verdict.checked === s.shown}`);
}

// ── stale ───────────────────────────────────────────────────────────────────
async function runStale(page) {
  await page.route('**/stage/poesie_automat/act', async (route) => {
    await new Promise((r) => setTimeout(r, DELAY));
    await route.continue();
  });
  const slot = Number(process.argv[3] || 8);
  // Get a real verdict on screen first, so there is something to go stale.
  await page.click('#automat-read');
  await waitVerdict(page);
  const box = await drumBox(page, slot);
  // Ask for a read, then turn a drum while that read is still in flight, and
  // let go before it lands — the case no hand is left down to re-arm.
  await page.click('#automat-read');
  await page.waitForTimeout(60);
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  await page.mouse.move(box.x, box.y + box.h * 2, { steps: 6 });
  await page.mouse.up();
  const during = await state(page);
  const seen = [];
  for (let i = 0; i < 60; i++) {
    seen.push(await state(page));
    await page.waitForTimeout(50);
  }
  const wrong = seen.filter(
    (s) => s.verdict && !/turning/.test(s.verdict.cls) && s.verdict.checked !== s.shown
  );
  const final = seen[seen.length - 1];
  log(`delay ${DELAY}ms, reduced ${REDUCED}, drum ${slot}`);
  log(`token at the move ${during.boardToken}, submitted under ${during.submittedToken}`);
  log(`real verdicts standing over a board they were not about: ${wrong.length}/${seen.length}`);
  log(`final: ${final.verdict ? final.verdict.cls : '(none)'} "${final.verdict ? final.verdict.text : ''}"`);
  log(`final checked text == what the drums show: ${final.verdict && final.verdict.checked === final.shown}`);
}

// ── wedge ───────────────────────────────────────────────────────────────────
async function runWedge(page) {
  const kind = process.argv[3] === 'abort' ? 'abort' : '500';
  await page.route('**/stage/poesie_automat/act', async (route) => {
    if (kind === 'abort') await route.abort('failed');
    else await route.fulfill({ status: 500, body: 'nope' });
  });
  const controls = () =>
    page.evaluate(() => ({
      inert: inert,
      clattering: clattering,
      deferredRead: deferredRead,
      pressDisabled: document.getElementById('automat-press').disabled,
      readDisabled: document.getElementById('automat-read').disabled,
      says: (() => {
        const v = document.querySelector('#automat-reading .verdict');
        return v ? v.textContent.trim() : null;
      })(),
    }));
  await page.click('#automat-press');
  await page.waitForTimeout(2500);
  log(`${kind}: ${JSON.stringify(await controls())}`);
  // Can a hand get the scene back? Turn a drum, the way a viewer would.
  const box = await drumBox(page, 8);
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  await page.mouse.move(box.x, box.y + box.h * 2, { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(1200);
  log(`  after turning a drum: ${JSON.stringify(await controls())}`);
}

// ── widths ──────────────────────────────────────────────────────────────────
async function runWidths(page) {
  const m = await page.evaluate(() => {
    const stage = document.getElementById('stage');
    const cs = getComputedStyle(stage);
    const available = stage.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const lines = Array.from(document.querySelectorAll('.flap-line')).map((l) => {
      const cells = Array.from(l.querySelectorAll('.flap'));
      const gap = parseFloat(getComputedStyle(l).gap);
      const widths = cells.map((d) => +d.getBoundingClientRect().width.toFixed(2));
      const chars = cells.map((d) =>
        Math.max(
          ...Array.from(d.querySelectorAll('.flap-cell')).map((c) => c.textContent.trim().length)
        )
      );
      return {
        widths: widths,
        chars: chars,
        gap: gap,
        total: +(widths.reduce((a, b) => a + b, 0) + gap * (widths.length - 1)).toFixed(2),
        charTotal: chars.reduce((a, b) => a + b, 0) + chars.length - 1,
      };
    });
    // What a literal board would need: each column as wide as the widest
    // module standing in it anywhere on the board.
    const columns = lines[0].widths.map((_, j) => Math.max(...lines.map((l) => l.widths[j])));
    const columnChars = lines[0].chars.map((_, j) => Math.max(...lines.map((l) => l.chars[j])));
    return {
      available: available,
      lines: lines,
      perLine: +Math.max(...lines.map((l) => l.total)).toFixed(2),
      perLineChars: Math.max(...lines.map((l) => l.charTotal)),
      aligned: +(columns.reduce((a, b) => a + b, 0) + lines[0].gap * 5).toFixed(2),
      alignedChars: columnChars.reduce((a, b) => a + b, 0) + 5,
      font: getComputedStyle(document.querySelector('.flap-cell')).fontSize,
      face: getComputedStyle(document.querySelector('.flap-cell')).fontFamily,
      loaded: document.fonts.check('14px "IBM Plex Mono"'),
    };
  });
  log(`face ${m.face} at ${m.font}; IBM Plex Mono loaded: ${m.loaded}`);
  log(`the stage leaves ${m.available}px between its margins`);
  m.lines.forEach((l, i) => {
    log(
      `line ${i + 1}: ${l.widths.map((w) => w.toFixed(1)).join(' + ')} + ${l.gap}px x5` +
        ` = ${l.total}px  (${l.charTotal} chars)`
    );
  });
  log(`A — drums sized per line:      ${m.perLine}px (${m.perLineChars} chars), fits: ${m.perLine <= m.available} (${(m.available - m.perLine).toFixed(2)}px spare)`);
  log(`B — columns aligned across all: ${m.aligned}px (${m.alignedChars} chars), fits: ${m.aligned <= m.available} (${(m.available - m.aligned).toFixed(2)}px spare)`);
}

// ── frames ──────────────────────────────────────────────────────────────────
//
// The scene's own content extent. A drum is a window one cell tall on a strip
// of twenty, so the strip's own box runs far past the board — clipped, and
// clipping is not overflow. Every element's bottom is intersected with its
// clipping ancestors up to `#stage`, whose own `overflow: hidden` is the clip
// this measurement is about and therefore not one of them.
async function extent(page) {
  return page.evaluate(() => {
    const stage = document.getElementById('stage');
    const top = stage.getBoundingClientRect().top;
    let deepest = 0;
    let who = null;
    stage.querySelectorAll('*').forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.width <= 0 && r.height <= 0) return;
      let bottom = r.bottom;
      let p = el.parentElement;
      while (p && p !== stage) {
        const cs = getComputedStyle(p);
        if (cs.overflow !== 'visible' || cs.overflowY !== 'visible') {
          bottom = Math.min(bottom, p.getBoundingClientRect().bottom);
        }
        p = p.parentElement;
      }
      if (bottom - top > deepest) {
        deepest = bottom - top;
        who = el.className || el.tagName;
      }
    });
    return { deepest: +deepest.toFixed(1), blank: +(720 - deepest).toFixed(1), by: String(who) };
  });
}

async function runFrames(page) {
  await page.screenshot({ path: `${OUT}/automat-first-paint.png` });
  log(`first paint: ${JSON.stringify(await extent(page))}`);
  await page.evaluate(() => {
    window.__clock = { start: null, end: null };
    const original = window.clatterTo;
    window.clatterTo = function () {
      window.__clock.start = performance.now();
      return original.apply(this, arguments).then((v) => {
        window.__clock.end = performance.now();
        return v;
      });
    };
  });
  const clicked = page.click('#automat-press');
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${OUT}/automat-mid-clatter.png` });
  log(`mid-clatter: ${JSON.stringify(await page.evaluate(() => ({ clattering: clattering, moving: drums.filter((d) => d.strip.style.transition !== 'none').length })))}`);
  await clicked;
  const s = await waitVerdict(page);
  await page.screenshot({ path: `${OUT}/automat-resolved.png` });
  const clock = await page.evaluate(() => window.__clock);
  log(`clatter clocked at ${(clock.end - clock.start).toFixed(1)}ms`);
  log(`resolved: ${JSON.stringify(await extent(page))}`);
  log(`verdict: ${s.verdict ? s.verdict.text : '(none)'}`);
  log(`checked text == shown text: ${s.verdict && s.verdict.checked === s.shown}`);
}

const browser = await chromium.launch();
const page = await open(browser);
const modes = {
  drag: runDrag,
  press: runPress,
  stale: runStale,
  wedge: runWedge,
  widths: runWidths,
  frames: runFrames,
};
if (!modes[mode]) {
  log(`unknown mode ${mode}; one of ${Object.keys(modes).join(', ')}`);
} else {
  await modes[mode](page);
}
await browser.close();
