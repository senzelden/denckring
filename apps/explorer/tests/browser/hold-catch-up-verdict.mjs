// The catch-up replay's own instance of Finding 1: `flushDeferredSteps`
// moves a wheel after the swap has already put a real verdict on screen,
// then submits — leaving the *previous* chamber's verdict over the new
// letters for a whole round trip. Oracle reads the page's own
// `currentLetters()`, not the printed chamber text.
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const DELAY = Number(process.argv[2] || 800);
const RUNS = Number(process.argv[3] || 3);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function contradicts(letters, verdict) {
  const parts = letters.split(/\s+/).filter(Boolean);
  const dup = parts.length !== new Set(parts).size;
  const m = verdict.match(/repeated principle: (\w+)/);
  if (m) return !dup || parts.filter((l) => l === m[1]).length < 2;
  if (verdict.includes('genuine chamber of')) return dup;
  return false; // the placeholder claims nothing, so it can contradict nothing
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.route('**/stage/llull_figure/act', async (route) => {
  await sleep(DELAY);
  await route.continue();
});
let bad = 0;
for (let i = 0; i < RUNS; i++) {
  await page.goto(`${BASE}/stage/llull_figure`, { waitUntil: 'networkidle' });
  const a = await page.locator('.hold-group[data-wheel-index="0"] .hold-btn[data-hold-dir="1"]').boundingBox();
  const b = await page.locator('.hold-group[data-wheel-index="1"] .hold-btn[data-hold-dir="1"]').boundingBox();
  // tap wheel I -> submits a read of C C D, response held for DELAY
  await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
  await page.mouse.down();
  await sleep(30);
  await page.mouse.up();
  await sleep(250);                       // land inside the round trip
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
  await page.mouse.down();
  await sleep(320);                       // two ticks, all deferred
  await page.mouse.up();                  // released before the response lands
  const t0 = Date.now();
  const samples = [];
  while (Date.now() - t0 < DELAY + 2200) {
    samples.push(
      await page.evaluate(() => ({
        t: Math.round(performance.now()),
        wheels: currentLetters().join(' '),
        chamber: document.querySelector('.llull-chamber').textContent.trim(),
        verdict: document.querySelector('.verdict').textContent.trim(),
        inert,
        holds: activeHolds,
      }))
    );
    await sleep(30);
  }
  const wrong = samples.filter((s) => contradicts(s.wheels, s.verdict));
  const window = wrong.length ? wrong[wrong.length - 1].t - wrong[0].t : 0;
  if (wrong.length) bad++;
  console.log(
    `run ${i + 1}/${RUNS}: ${wrong.length} contradicting samples, window ~${window}ms` +
      `  final wheels=${samples[samples.length - 1].wheels} "${samples[samples.length - 1].verdict}"`
  );
  if (wrong.length && i === 0) {
    const first = samples.findIndex((s) => contradicts(s.wheels, s.verdict));
    for (const s of samples.slice(Math.max(0, first - 2), first + 3)) {
      console.log(
        `    ${s.t}  wheels=${s.wheels.replace(/ /g, '')} chamber=${s.chamber.replace(/ /g, '')}` +
          ` inert=${s.inert} holds=${s.holds}  "${s.verdict}"`
      );
    }
  }
}
console.log(`\n${bad}/${RUNS} runs showed a verdict contradicting the wheels' own letters (delay ${DELAY}ms)`);
await browser.close();
