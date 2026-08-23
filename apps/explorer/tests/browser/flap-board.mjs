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
//   read    the plain "Read the board" button, from first paint: what it puts
//           on the wire and whether the verdict that comes back is about the
//           board. It used to post an empty poem — the hidden field is filled
//           by `readBoard()` and a native submit never called it — and land a
//           red verdict over a board that was perfectly valid.
//   wave    the two constraints the clatter actually has to meet, measured in
//           the page rather than read off the source: the dwell between one
//           flap arriving on a drum and the next, and the span between the
//           first drum starting and the last one starting. Takes a run count
//           (default 20) and reports the range over all of them.
//   contend a grab begun *during* an in-flight press (`DELAY`, default 900ms),
//           which used to survive into the clatter — a hand and the machine
//           writing one strip. Counts samples with the board clattering under
//           a hand, and the POSTs the whole gesture costs.
//   widths  the measurement the whole layout turns on: every drum's rendered
//           width, each line's total against the width the stage leaves, and
//           what a literal board (columns aligned across all six lines) would
//           need instead. Also reports the board's own `data-fits`.
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
      fits: document.getElementById('flap-board').dataset.fits,
    };
  });
  log(`face ${m.face} at ${m.font}; the board says data-fits="${m.fits}"`);
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

// ── read ────────────────────────────────────────────────────────────────────
// The plain button, from first paint. Nothing has been dragged and nothing has
// been pressed, so the only thing that can have filled the hidden field is the
// button's own path.
async function runRead(page) {
  const posted = [];
  page.on('request', (r) => {
    if (r.method() === 'POST') posted.push(r.postData() || '');
  });
  const field = await page.evaluate(() => document.getElementById('automat-poem').value);
  log(`hidden field at first paint: ${JSON.stringify(field)}`);
  await page.click('#automat-read');
  const s = await waitVerdict(page);
  log(`posted ${posted.length} request(s); body starts: ${JSON.stringify(posted[0].slice(0, 60))}`);
  log(`verdict: ${s.verdict ? s.verdict.cls : '(none)'} — ${s.verdict ? s.verdict.text : ''}`);
  log(`checked text == what the drums show: ${s.verdict && s.verdict.checked === s.shown}`);
}

// ── wave ────────────────────────────────────────────────────────────────────
//
// `syncDrum` is called once per flap arrival, by the clatter and by nothing
// else during a press, so wrapping it is a flap-by-flap clock inside the page.
// A MutationObserver would not do: its callbacks are batched at microtask end,
// so several arrivals collapse onto one timestamp and the dwell measurement
// would be an artefact of the observer.
// Wrapped **once** per page, and the buffer emptied per run. Wrapping again on
// every run wraps the wrapper: measured, that reported 4272 flap steps for a
// press that took 166 of them, and a dwell of 0ms between the duplicates.
async function instrumentFlaps(page) {
  await page.evaluate(() => {
    window.__flaps = [];
    if (window.__flapsWrapped) return;
    window.__flapsWrapped = true;
    const original = window.syncDrum;
    window.syncDrum = function (slot) {
      window.__flaps.push({ slot: slot, t: performance.now() });
      return original.apply(this, arguments);
    };
    const originalClatter = window.clatterTo;
    window.clatterTo = function () {
      window.__clock = { start: performance.now(), end: null };
      return originalClatter.apply(this, arguments).then((v) => {
        window.__clock.end = performance.now();
        return v;
      });
    };
  });
}

function waveStats(flaps) {
  const firstBySlot = new Map();
  const lastBySlot = new Map();
  const dwells = [];
  flaps.forEach((f) => {
    if (!firstBySlot.has(f.slot)) firstBySlot.set(f.slot, f.t);
    else dwells.push(f.t - lastBySlot.get(f.slot));
    lastBySlot.set(f.slot, f.t);
  });
  const starts = [...firstBySlot.entries()].sort((a, b) => a[1] - b[1]);
  return {
    steps: flaps.length,
    drumsThatMoved: firstBySlot.size,
    // The wave: between the first drum to start and the last drum to start.
    startSpan: starts.length > 1 ? starts[starts.length - 1][1] - starts[0][1] : 0,
    dwellMin: dwells.length ? Math.min(...dwells) : 0,
    dwellMax: dwells.length ? Math.max(...dwells) : 0,
    dwellMedian: dwells.length ? dwells.slice().sort((a, b) => a - b)[dwells.length >> 1] : 0,
    total: flaps.length ? flaps[flaps.length - 1].t - flaps[0].t : 0,
  };
}

async function runWave(page) {
  const runs = Number(process.argv[3] || 20);
  // The floors this scene actually has to meet. The total duration is not one
  // of them: what a viewer needs is to see each flap arrive, which is dwell,
  // and to see the board resolve in a wave rather than in unison, which is the
  // start span. Both are budgets on the mechanism; the total is what falls out.
  const DWELL_FLOOR = 30; // ms a flap must stand before the next replaces it
  const SPAN_FLOOR = 500; // ms between the first drum starting and the last
  const all = [];
  for (let i = 0; i < runs; i++) {
    await instrumentFlaps(page);
    await page.click('#automat-press');
    await waitVerdict(page);
    const flaps = await page.evaluate(() => window.__flaps);
    const clock = await page.evaluate(() => window.__clock);
    const s = waveStats(flaps);
    s.clocked = clock.end - clock.start;
    all.push(s);
  }
  const col = (k) => all.map((s) => s[k]);
  const range = (k, unit = 'ms') =>
    `${Math.min(...col(k)).toFixed(1)}-${Math.max(...col(k)).toFixed(1)}${unit}`;
  log(`${runs} presses, reduced ${REDUCED}`);
  log(`flap steps per press : ${Math.min(...col('steps'))}-${Math.max(...col('steps'))}`);
  log(`drums that moved     : ${Math.min(...col('drumsThatMoved'))}-${Math.max(...col('drumsThatMoved'))} of 36`);
  log(`dwell, median        : ${range('dwellMedian')}`);
  log(`dwell, min over all  : ${Math.min(...col('dwellMin')).toFixed(1)}ms  (floor ${DWELL_FLOOR}ms)`);
  log(`start span, first->last drum : ${range('startSpan')}  (floor ${SPAN_FLOOR}ms)`);
  log(`clatter, clocked     : ${range('clocked')}`);
  if (REDUCED) {
    // Under reduced motion the floors are meant *not* to be met: there is no
    // dwell and no wave, because the board arrives at its flaps at once. The
    // requirement here is the opposite one, and it is checked as such rather
    // than reported as a failure of a budget that does not apply.
    const atOnce = Math.max(...col('startSpan')) < 50 && Math.max(...col('total')) < 100;
    log(`reduced motion: the whole board lands at once: ${atOnce}`);
    log(`VERDICT: ${atOnce ? 'pass' : 'FAIL'}`);
    return;
  }
  const dwellOk = Math.min(...col('dwellMin')) >= DWELL_FLOOR;
  const spanOk = Math.min(...col('startSpan')) >= SPAN_FLOOR;
  log(`dwell floor met on every run: ${dwellOk}`);
  log(`wave  floor met on every run: ${spanOk}  (a board resolving in unison scores 0)`);
  log(`VERDICT: ${dwellOk && spanOk ? 'pass' : 'FAIL'}`);
}

// ── contend ─────────────────────────────────────────────────────────────────
// A hand and the machine must never be writing one strip.
async function runContend(page) {
  await page.route('**/stage/poesie_automat/act', async (route) => {
    await new Promise((r) => setTimeout(r, DELAY));
    await route.continue();
  });
  let posts = 0;
  page.on('request', (r) => {
    if (r.method() === 'POST') posts++;
  });
  const slot = Number(process.argv[3] || 8);
  const box = await drumBox(page, slot);
  await page.click('#automat-press');
  await page.waitForTimeout(60); // inside the press's own flight
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  const samples = [];
  for (let i = 0; i < 40; i++) {
    await page.mouse.move(box.x, box.y + ((i % 8) + 1) * 6);
    samples.push(
      await page.evaluate(() => ({
        clattering: clattering,
        activeDrums: activeDrums,
        held: held.size,
        inert: inert,
        boardOwned: boardOwned,
      }))
    );
    await page.waitForTimeout(40);
  }
  await page.mouse.up();
  const s = await waitVerdict(page);
  const both = samples.filter((x) => x.clattering && x.activeDrums > 0);
  log(`delay ${DELAY}ms, drum ${slot}`);
  log(`grab accepted at all: ${samples.some((x) => x.activeDrums > 0)}`);
  log(`samples with the board clattering under a hand: ${both.length}/${samples.length}`);
  log(`POSTs for the whole gesture: ${posts}`);
  log(`final: ${s.verdict ? s.verdict.cls : '(none)'}; checked == shown: ${s.verdict && s.verdict.checked === s.shown}`);

  // The keyboard is deliberately *not* refused during a press's flight — a
  // keyboard step is instantaneous and cannot still be under way when the
  // clatter starts, and locking the keys out for the length of every round
  // trip is the mistake scene seven had to measure its way back out of. What
  // it does leave behind is a read owed for a board the clatter is about to
  // overwrite, and the press branch drops that debt rather than paying it.
  posts = 0;
  await page.click('#automat-press');
  // Focus *after* the click: clicking a button takes focus, so a drum focused
  // beforehand would not be the thing the key reaches.
  await page.focus(`#flap-${slot}`);
  await page.waitForTimeout(60);
  await page.keyboard.press('ArrowDown');
  const owed = await page.evaluate(() => ({ deferredRead: deferredRead, inert: inert }));
  await waitVerdict(page);
  const after = await state(page);
  log(`keyboard during the press flight: owed a read ${owed.deferredRead} (inert ${owed.inert})`);
  log(`POSTs for press + one arrow key: ${posts}   (PRESS, then the clatter's own READ)`);
  log(`final: ${after.verdict ? after.verdict.cls : '(none)'}; checked == shown: ${after.verdict && after.verdict.checked === after.shown}`);
}

const browser = await chromium.launch();
const page = await open(browser);
const modes = {
  drag: runDrag,
  press: runPress,
  read: runRead,
  wave: runWave,
  contend: runContend,
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
