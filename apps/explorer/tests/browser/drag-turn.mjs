// Drag-to-turn, on either volvelle: does the ring actually move *while the
// pointer is still down*, does the panel follow it, does the verdict stay a
// placeholder until it stops, and does it land on a detent?
//
//   BASE=... node drag-turn.mjs [scene] [mode] [ring]
//
//     scene  denckring | llull_figure          (default denckring)
//     mode   sweep | back | wrap | contend | two-finger | regrab  (default sweep)
//     ring   which ring to grab                (default: outermost)
//
// `sweep` drags one ring 90 degrees clockwise, sampling the dial's own
// transform and the panel beside it every few degrees while the pointer is
// down; `back` does the same anticlockwise, which is the direction scene one
// could not turn at all before this task; `wrap` crosses the ring's own seam
// in both directions from the position either side of it; `contend` holds a
// step button on the same ring mid-drag (the drag is meant to win); and
// `two-finger` drags two rings at once with CDP touch events, the capability
// the hold path had to be repaired to keep; and `regrab` grabs again while
// the previous release's read is still in flight (the POST is delayed by
// `DELAY`, default 600ms), which is the one way a *server* answer can land
// on the panel while a hand is turning a ring — it counts samples where the
// panel disagreed with the rings' own indices, and where a real verdict
// stood under the finger.
//
// The oracle is the page's own model, never the rendered text: scene one's
// `endbuchstabe` repeats two of its 120 parts, so a check by text can only
// ever find the first occurrence.
import { chromium } from 'playwright';

const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const SCENE = process.argv[2] || 'denckring';
const MODE = process.argv[3] || 'sweep';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const DENCKRING = SCENE === 'denckring';
const MODEL = DENCKRING ? 'rings' : 'wheels';
const ATTR = DENCKRING ? 'ring' : 'wheel';
const RING = Number(process.argv[4] !== undefined ? process.argv[4] : DENCKRING ? 3 : 2);
const PANEL = DENCKRING ? '#word' : '#llull-reading';

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  hasTouch: MODE === 'two-finger' || MODE === 'contend',
  reducedMotion: process.env.REDUCED ? 'reduce' : undefined,
});
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
await page.goto(`${BASE}/stage/${SCENE}`, { waitUntil: 'networkidle' });

// Where to put the pointer: the middle of the band, which is the only place
// the SVG's own hit test resolves to this ring and not its neighbour.
async function geometry(ring) {
  return page.evaluate(
    ([attr, r]) => {
      const svgEl = document.querySelector('svg[viewBox]');
      const box = svgEl.getBoundingClientRect();
      const scale = box.width / 600;
      const radiusOf = (i) =>
        i < 0 ? 0 : Number(document.querySelector(`[data-${attr}="${i}"] circle`).getAttribute('r'));
      return {
        cx: box.left + box.width / 2,
        cy: box.top + box.height / 2,
        radius: ((radiusOf(r) + radiusOf(r - 1)) / 2) * scale,
      };
    },
    [ATTR, ring]
  );
}

const sample = (ring) =>
  page.evaluate(
    ([model, r, panel]) => {
      const list = model === 'rings' ? rings : wheels;
      const verdicts = [...document.querySelectorAll(panel + ' .verdict')];
      const shown =
        model === 'rings'
          ? document.querySelector('#word .word').textContent.trim()
          : document.querySelector('.llull-chamber').textContent.trim();
      const truth =
        model === 'rings'
          ? rings.map((x) => (x.index < x.parts.length ? x.parts[x.index] : '')).join('')
          : wheels
              .slice(0, arity)
              .map((x) => x.letters[x.index])
              .join(' ');
      return {
        index: list[r].index,
        transform: list[r].dial.style.transform,
        transition: list[r].dial.style.transition,
        holds: activeHolds,
        placeholder: verdicts.length > 0 && verdicts.every((v) => v.classList.contains('turning')),
        realVerdict: verdicts.some((v) => !v.classList.contains('turning')),
        verdictText: verdicts.map((v) => v.textContent.replace(/\s+/g, ' ').trim()).join(' | '),
        shown: shown,
        truth: truth,
      };
    },
    [MODEL, ring, PANEL]
  );

const degOf = (t) => {
  const m = /rotate\(([-0-9.e]+)deg\)/.exec(t || '');
  return m ? Number(m[1]) : null;
};

async function drag(ring, totalDeg, stepDeg) {
  const geo = await geometry(ring);
  const at = (deg) => {
    const rad = (deg * Math.PI) / 180;
    return { x: geo.cx + geo.radius * Math.sin(rad), y: geo.cy - geo.radius * Math.cos(rad) };
  };
  const start = at(0);
  const first = await sample(ring);
  await page.mouse.move(start.x, start.y);
  await page.mouse.down();
  const samples = [];
  const sign = totalDeg >= 0 ? 1 : -1;
  const walk = Math.abs(stepDeg) * sign;
  // Instrument the snap from inside the page, off its own clock: the release
  // and the landing are both events this side can only poll for, and a poll
  // that goes through `evaluate` costs more than the settle it is timing.
  await page.evaluate(
    ([model, r]) => {
      const dial = (model === 'rings' ? rings : wheels)[r].dial;
      window.__up = null;
      window.__snap = null;
      window.addEventListener(
        'pointerup',
        () => {
          window.__up = performance.now();
        },
        { once: true, capture: true }
      );
      const landed = () =>
        dial.style.transition === 'none' && /rotate\(-?0(\.0+)?deg\)/.test(dial.style.transform);
      new MutationObserver(() => {
        if (window.__up !== null && window.__snap === null && landed()) {
          window.__snap = performance.now() - window.__up;
        }
      }).observe(dial, { attributes: true, attributeFilter: ['style'] });
    },
    [MODEL, ring]
  );
  for (let d = walk; Math.abs(d) <= Math.abs(totalDeg); d += walk) {
    const point = at(d);
    await page.mouse.move(point.x, point.y);
    const s = await sample(ring);
    s.pointerDeg = d;
    samples.push(s);
  }
  const held = await sample(ring);
  await page.mouse.up();
  await sleep(700);
  const snapMs = await page.evaluate(() => window.__snap);
  const rest = await sample(ring);
  return { first, samples, held, rest, snapMs, angleStep: null };
}

function report(name, run, expectedDetents) {
  const step = run.samples.length ? Math.abs(run.samples[0].pointerDeg) : 0;
  const moved = run.samples.filter((s, i) => i > 0 && s.index !== run.samples[i - 1].index).length;
  const underFinger = run.samples.filter((s) => degOf(s.transform) !== null).length;
  const residuals = run.samples.map((s) => degOf(s.transform));
  const worstResidual = Math.max(...residuals.map(Math.abs));
  const realUnderFinger = run.samples.filter((s) => s.realVerdict).length;
  const panelFollowed = run.samples.filter((s) => s.shown === s.truth).length;
  console.log(
    `${name}: ${run.samples.length} samples while the pointer was down; ` +
      `detents crossed ${moved} (asked ${expectedDetents}); ` +
      `index ${run.first.index} -> ${run.held.index} -> ${run.rest.index}; ` +
      `dial carried a live transform in ${underFinger}/${run.samples.length}, ` +
      `worst residual ${worstResidual.toFixed(2)}deg; ` +
      `panel matched the model in ${panelFollowed}/${run.samples.length}; ` +
      `real verdict under the finger ${realUnderFinger}/${run.samples.length}; ` +
      `snap landed ${run.snapMs === null ? '(no residual to settle)' : run.snapMs.toFixed(1) + 'ms'} ` +
      `after the release, by the page's own clock; ` +
      `at rest transform=${run.rest.transform || '(none)'} holds=${run.rest.holds} ` +
      `verdict=${JSON.stringify(run.rest.verdictText)} shown=${JSON.stringify(run.rest.shown)} ` +
      `model=${JSON.stringify(run.rest.truth)}`
  );
}

if (MODE === 'sweep' || MODE === 'back') {
  const detent = await page.evaluate(
    ([model, r]) => (model === 'rings' ? 360 / rings[r].window : 360 / 9),
    [MODEL, RING]
  );
  const total = MODE === 'sweep' ? 90 : -90;
  const run = await drag(RING, total, 4);
  report(`${SCENE} ring ${RING} ${MODE} ${total}deg (detent ${detent}deg)`, run, Math.round(90 / detent));
} else if (MODE === 'wrap') {
  // Park the ring one detent short of its own seam, then cross it, each way.
  for (const [label, park, total] of [
    ['forwards over the seam', 1, -90],
    ['backwards over the seam', 0, 90],
  ]) {
    await page.evaluate(
      ([model, r, p]) => {
        const list = model === 'rings' ? rings : wheels;
        list[r].index = p;
        renderDial(r);
        // The panel too, or this harness's own shortcut leaves it stale and
        // the mismatch it counts below is the harness's, not the page's.
        if (model === 'rings') renderLocalWord();
        else renderLocalReading(currentLetters());
      },
      [MODEL, RING, park]
    );
    const run = await drag(RING, total, 4);
    report(`${SCENE} ring ${RING} ${label} (from index ${park})`, run, null);
  }
} else if (MODE === 'contend') {
  // One finger on the disc, a second finger on that same ring's step button,
  // for 700ms. Two touch points, not a mouse: a mouse has one pointer, and
  // the grab captures it, so the button never even sees a press. The drag is
  // meant to win — `stepRing` declines a ring the grab owns — and the ring
  // must move by exactly what the *drag* asked for, which here is nothing.
  const geo = await geometry(RING);
  const box = await page.locator(`.hold-btn[data-hold-ring="${RING}"][data-hold-dir="1"]`).boundingBox();
  const finger = { x: geo.cx, y: geo.cy - geo.radius, id: 1 };
  const thumb = { x: box.x + box.width / 2, y: box.y + box.height / 2, id: 2 };
  const before = await sample(RING);
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [finger] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [finger, thumb] });
  await sleep(700);
  const during = await sample(RING);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [finger] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await sleep(900);
  const rest = await sample(RING);
  console.log(
    `${SCENE} ring ${RING} contend: index ${before.index} -> ${during.index} -> ${rest.index} ` +
      `after 700ms of a held step button on a ring a second finger was already grabbing ` +
      `(the grab never moved); activeHolds during ${during.holds}; ` +
      `at rest holds=${rest.holds} verdict=${JSON.stringify(rest.verdictText)} ` +
      `shown=${JSON.stringify(rest.shown)} model=${JSON.stringify(rest.truth)}`
  );
} else if (MODE === 'two-finger') {
  const ringA = DENCKRING ? 1 : 0;
  const ringB = DENCKRING ? 3 : 2;
  const gA = await geometry(ringA);
  const gB = await geometry(ringB);
  const cdp = await ctx.newCDPSession(page);
  const at = (g, deg, id) => {
    const rad = (deg * Math.PI) / 180;
    return { x: g.cx + g.radius * Math.sin(rad), y: g.cy - g.radius * Math.cos(rad), id };
  };
  const before = [await sample(ringA), await sample(ringB)];
  await cdp.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [at(gA, 0, 1), at(gB, 0, 2)],
  });
  let holdsSeen = 0;
  for (let d = 6; d <= 60; d += 6) {
    await cdp.send('Input.dispatchTouchEvent', {
      type: 'touchMove',
      touchPoints: [at(gA, d, 1), at(gB, -d, 2)],
    });
    const h = await page.evaluate(() => activeHolds);
    holdsSeen = Math.max(holdsSeen, h);
  }
  const mid = [await sample(ringA), await sample(ringB)];
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await sleep(900);
  const rest = [await sample(ringA), await sample(ringB)];
  console.log(
    `${SCENE} two fingers, rings ${ringA} and ${ringB}: activeHolds peaked at ${holdsSeen}; ` +
      `ring ${ringA} ${before[0].index} -> ${mid[0].index} -> ${rest[0].index} (dragged +60deg), ` +
      `ring ${ringB} ${before[1].index} -> ${mid[1].index} -> ${rest[1].index} (dragged -60deg); ` +
      `at rest holds=${rest[0].holds} verdict=${JSON.stringify(rest[0].verdictText)}`
  );
} else if (MODE === 'regrab') {
  const delay = Number(process.env.DELAY || 600);
  await page.route('**/act', async (route) => {
    await sleep(delay);
    await route.continue();
  });
  // First grab: turn it and let go, which submits a read that will not come
  // back for `delay` ms.
  const geo = await geometry(RING);
  const at = (deg) => {
    const rad = (deg * Math.PI) / 180;
    return { x: geo.cx + geo.radius * Math.sin(rad), y: geo.cy - geo.radius * Math.cos(rad) };
  };
  await page.mouse.move(at(0).x, at(0).y);
  await page.mouse.down();
  for (let d = 8; d <= 64; d += 8) await page.mouse.move(at(d).x, at(d).y);
  await page.mouse.up();
  // Long enough for the snap to settle and the read to actually go out --
  // grabbing again *inside* the snap keeps `activeHolds` above zero and no
  // request is ever sent, which is the gate working and not this scenario.
  await sleep(250);
  // Second grab, so the first read's swap lands in the middle of it.
  await page.mouse.move(at(0).x, at(0).y);
  await page.mouse.down();
  const samples = [];
  // Turn it for a moment, then hold it *still*. Standing still is the point:
  // a hand resting between two detents is a state only a drag can be in, and
  // it is exactly when nothing else will come along to redraw the panel over
  // whatever the arriving swap prints on it.
  const samplesWhileMoving = 8;
  for (let i = 0; i < 44; i++) {
    if (i < samplesWhileMoving) await page.mouse.move(at(-4 - i * 4).x, at(-4 - i * 4).y);
    samples.push(await sample(RING));
    await sleep(25);
  }
  await page.mouse.up();
  await sleep(delay + 900);
  const rest = await sample(RING);
  const stalePanel = samples.filter((x) => x.shown !== x.truth);
  const realVerdict = samples.filter((x) => x.realVerdict);
  console.log(
    `${SCENE} ring ${RING} regrab (POST delayed ${delay}ms): ${samples.length} samples during the ` +
      `second grab; panel disagreed with the rings in ${stalePanel.length}` +
      (stalePanel.length ? ` (e.g. shown ${JSON.stringify(stalePanel[0].shown)} vs model ` +
        `${JSON.stringify(stalePanel[0].truth)})` : '') +
      `; a real verdict stood under the finger in ${realVerdict.length}` +
      (realVerdict.length ? ` (e.g. ${JSON.stringify(realVerdict[0].verdictText)})` : '') +
      `; at rest holds=${rest.holds} shown=${JSON.stringify(rest.shown)} ` +
      `model=${JSON.stringify(rest.truth)} verdict=${JSON.stringify(rest.verdictText)}`
  );
} else {
  console.log(`unknown mode ${MODE}`);
}

if (errors.length) console.log('PAGE ERRORS:', errors.join(' / '));
await browser.close();
