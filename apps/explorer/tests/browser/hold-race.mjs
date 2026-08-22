// Reproduction for the llull_figure hold/drain race: a short tap on one
// wheel followed, within the drain's own window, by a press-and-hold on
// another. If the drain submits mid-hold, the server's checked verdict
// swaps in over the "turning…" placeholder and is never restored, so the
// panel shows a real verdict under wheels that keep turning.
import { chromium } from 'playwright';

const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const MODE = process.argv[2] || 'scripted';
const RUNS = Number(process.argv[3] || (MODE === 'scripted' ? 3 : 25));

function box(page, wheel, dir) {
  return page
    .locator(`.hold-group[data-wheel-index="${wheel}"] .hold-btn[data-hold-dir="${dir}"]`)
    .boundingBox();
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function run(page, { tapMs, gapMs, holdMs, tapWheel, holdWheel }) {
  await page.goto(`${BASE}/stage/llull_figure`, { waitUntil: 'networkidle' });
  const a = await box(page, tapWheel, 1);
  const b = await box(page, holdWheel, 1);

  // tap wheel A
  await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
  await page.mouse.down();
  await sleep(tapMs);
  await page.mouse.up();

  await sleep(gapMs);

  // press and hold wheel B
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
  await page.mouse.down();

  const samples = [];
  const t0 = Date.now();
  while (Date.now() - t0 < holdMs) {
    samples.push(
      await page.evaluate(() => ({
        t: Math.round(performance.now()),
        chamber: document.querySelector('#llull-reading .llull-chamber').textContent.trim(),
        verdict: document.querySelector('#llull-reading .verdict').textContent.trim(),
      }))
    );
    await sleep(50);
  }
  await page.mouse.up();

  // a stale verdict = a non-placeholder verdict seen while the button was
  // still down, at least 300ms in (past the settling of the tap's own read)
  const stale = samples.filter((s, i) => i >= 6 && !s.verdict.includes('turning'));
  const chambersUnderStale = new Set(stale.map((s) => s.chamber));
  // A stricter, self-evident reading of the same samples: a verdict that
  // contradicts the very chamber displayed beside it.
  const contradicts = (s) => {
    const letters = s.chamber.split(/\s+/).filter(Boolean);
    const dup = letters.length !== new Set(letters).size;
    const m = s.verdict.match(/repeated principle: (\w+)/);
    if (m) return !dup || letters.filter((l) => l === m[1]).length < 2;
    if (s.verdict.includes('genuine chamber of')) return dup;
    return false;
  };
  const contradictions = stale.filter(contradicts);
  // Motion under a real verdict: the panel changed chamber from one sample
  // to the next while a checked verdict, not the placeholder, was on screen.
  const staleMotion = samples.filter(
    (s, i) => i > 0 && i >= 6 && !s.verdict.includes('turning') && s.chamber !== samples[i - 1].chamber
  );
  const held = new Set(samples.map((s) => s.chamber)).size;

  await page.waitForTimeout(1200); // let the release's own read land
  const rest = await page.evaluate(() => ({
    chamber: document.querySelector('#llull-reading .llull-chamber').textContent.trim(),
    verdict: document.querySelector('#llull-reading .verdict').textContent.trim(),
    letters: window.currentLetters ? window.currentLetters().join(' ') : null,
  }));
  rest.contradicts = contradicts(rest);
  return { samples, stale, staleMotion, held, contradictions, chambersUnderStale: [...chambersUnderStale], rest };
}

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1280, height: 800 },
  ...(process.env.REDUCED ? { reducedMotion: 'reduce' } : {}),
});

let bugRuns = 0;
let motionRuns = 0;
let contraRuns = 0;
let restBad = 0;
for (let i = 0; i < RUNS; i++) {
  const params =
    MODE === 'scripted'
      ? { tapMs: 30, gapMs: 40, holdMs: 1600, tapWheel: 0, holdWheel: 1 }
      : {
          tapMs: 20 + Math.floor(Math.random() * 60),
          gapMs: Math.floor(Math.random() * 120),
          holdMs: 1200 + Math.floor(Math.random() * 900),
          tapWheel: Math.floor(Math.random() * 3),
          holdWheel: Math.floor(Math.random() * 3),
        };
  const r = await run(page, params);
  const bug = r.stale.length > 0;
  if (bug) bugRuns++;
  if (r.staleMotion.length) motionRuns++;
  if (r.contradictions.length) contraRuns++;
  const restOk = !r.rest.verdict.includes('turning') && !r.rest.contradicts;
  if (!restOk) restBad++;
  console.log(
    `run ${i + 1}/${RUNS} ${JSON.stringify(params)} stale=${r.stale.length}` +
      ` staleMotion=${r.staleMotion.length} chambersSeenDuringHold=${r.held}` +
      ` contradictions=${r.contradictions.length}` +
      ` chambersUnderStaleVerdict=${JSON.stringify(r.chambersUnderStale)}` +
      ` rest="${r.rest.chamber}" / "${r.rest.verdict}"${r.rest.contradicts ? ' CONTRADICTS' : ''}`
  );
  if (bug && i === 0) {
    for (const s of r.stale.slice(0, 6)) console.log(`    ${s.chamber}  "${s.verdict}"`);
  }
}
console.log(`\n${MODE}: ${bugRuns}/${RUNS} runs showed a real verdict under a still-held button,` +
  ` ${motionRuns}/${RUNS} showed the chamber still changing under one,` +
  ` ${contraRuns}/${RUNS} showed a verdict contradicting the chamber beside it,` +
  ` ${restBad}/${RUNS} ended at rest wrong (placeholder left up, or a verdict contradicting the chamber)`);
await browser.close();
