// Does a hold that spans a slow round trip lose its steps? Delays the POST
// so `inert` is true for most of a second, presses and holds a *second*
// wheel inside that window, and compares the ticks the hold produced with
// the letters the wheel actually moved.
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const DELAY = Number(process.argv[2] || 800);
const RUNS = Number(process.argv[3] || 5);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ALPHA = 'BCDEFGHIK';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.route('**/stage/llull_figure/act', async (route) => {
  await sleep(DELAY);
  await route.continue();
});
let lost = 0;
for (let i = 0; i < RUNS; i++) {
  await page.goto(`${BASE}/stage/llull_figure`, { waitUntil: 'networkidle' });
  await page.evaluate(() => {
    // Count only what the held button itself asked for: the replay of
    // deferred steps calls the same function, and counting that too would
    // count the same movement twice.
    window.__ticks = 0;
    window.__flushing = false;
    const origStep = window.stepWheel;
    window.stepWheel = function (w, d) {
      if (w === 1 && !window.__flushing) window.__ticks += d;
      return origStep.apply(null, arguments);
    };
    const origFlush = window.flushDeferredSteps;
    if (origFlush) {
      window.flushDeferredSteps = function () {
        window.__flushing = true;
        try {
          return origFlush.apply(null, arguments);
        } finally {
          window.__flushing = false;
        }
      };
    }
  });
  const a = await page.locator('.hold-group[data-wheel-index="0"] .hold-btn[data-hold-dir="1"]').boundingBox();
  const b = await page.locator('.hold-group[data-wheel-index="1"] .hold-btn[data-hold-dir="1"]').boundingBox();
  const before = await page.evaluate(() => document.querySelector('.llull-chamber').textContent.trim());
  await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
  await page.mouse.down();
  await sleep(30);
  await page.mouse.up();          // -> read submits, response held for DELAY ms
  await sleep(200);               // land inside the round trip
  const inertNow = await page.evaluate(() => ({
    inert,
    wheelsOwned: typeof wheelsOwned === 'undefined' ? null : wheelsOwned,
  }));
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
  await page.mouse.down();
  await sleep(620);
  const mid = await page.evaluate(() => ({
    ticks: window.__ticks,
    deferred: typeof deferredAdvance === 'undefined' ? null : [...deferredAdvance.entries()],
    verdict: document.querySelector('.verdict').textContent.trim(),
  }));
  await page.mouse.up();
  await page.waitForTimeout(DELAY + 1500);
  const after = await page.evaluate(() => ({
    chamber: document.querySelector('.llull-chamber').textContent.trim(),
    verdict: document.querySelector('.verdict').textContent.trim(),
    ticks: window.__ticks,
  }));
  const startLetter = before.split(' ')[1];
  const endLetter = after.chamber.split(' ')[1];
  const moved = (ALPHA.indexOf(endLetter) - ALPHA.indexOf(startLetter) + 9) % 9;
  const asked = ((after.ticks % 9) + 9) % 9;
  if (moved !== asked) lost++;
  console.log(
    `run ${i + 1}: inertDuringPress=${inertNow.inert} wheelsOwned=${inertNow.wheelsOwned}` +
      ` deferredMidHold=${JSON.stringify(mid.deferred)} midVerdict="${mid.verdict}"` +
      ` ticks=${after.ticks} wheelMoved=${moved} ${before} -> ${after.chamber} "${after.verdict}"`
  );
}
console.log(`\n${lost}/${RUNS} runs lost steps under a finger still down (delay ${DELAY}ms)`);
await browser.close();
