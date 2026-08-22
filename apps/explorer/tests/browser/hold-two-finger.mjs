// Two fingers, two wheels: does a second touch hold kill the first?
// CDP touch events on a hasTouch context, so `pointerType` is 'touch'.
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const ALPHA = 'BCDEFGHIK';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, hasTouch: true });
const page = await ctx.newPage();
await page.goto(`${BASE}/stage/llull_figure`, { waitUntil: 'networkidle' });
const cdp = await ctx.newCDPSession(page);
const log = [];
await page.exposeFunction('__log', (s) => log.push(s));
await page.evaluate(() => {
  document.querySelectorAll('.hold-btn').forEach((b) => {
    const name = b.getAttribute('aria-label');
    ['pointerdown', 'focus', 'blur', 'pointerup'].forEach((type) =>
      b.addEventListener(type, () => window.__log(`${type} ${name} @${Math.round(performance.now())}`))
    );
  });
});
const box = async (w) =>
  page.locator(`.hold-group[data-wheel-index="${w}"] .hold-btn[data-hold-dir="1"]`).boundingBox();
const b0 = await box(0);
const b2 = await box(2);
const p0 = { x: b0.x + b0.width / 2, y: b0.y + b0.height / 2, id: 1 };
const p2 = { x: b2.x + b2.width / 2, y: b2.y + b2.height / 2, id: 2 };
const before = await page.evaluate(() => wheels.map((w) => w.letters[w.index]));

await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [p0] });
await sleep(150);
await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [p0, p2] });
await sleep(1000);
const mid = await page.evaluate(() => ({ holds: activeHolds, letters: wheels.map((w) => w.letters[w.index]) }));
await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [p0] });
await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
await sleep(600);
const moved = (i) => (ALPHA.indexOf(mid.letters[i]) - ALPHA.indexOf(before[i]) + 9) % 9;
console.log(
  `activeHolds while both held = ${mid.holds}; wheel I moved ${moved(0)} letters,` +
    ` wheel III moved ${moved(2)} (${before.join('')} -> ${mid.letters.join('')})`
);
console.log(log.join('\n'));
await browser.close();
