// The blur -> stop release path, which `preventDefault` on pointerdown used
// to leave dead for pointer holds (no focus was ever taken, so no blur was
// ever delivered).
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
await page.goto(`${BASE}/stage/llull_figure`, { waitUntil: 'networkidle' });
const b = await page.locator('.hold-group[data-wheel-index="0"] .hold-btn[data-hold-dir="1"]').boundingBox();
await page.evaluate(() => {
  window.__n = 0;
  new MutationObserver(() => window.__n++).observe(document.querySelector('.llull-chamber'), {
    characterData: true, childList: true, subtree: true,
  });
});
await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
await page.mouse.down();
await sleep(800);
const beforeBlur = await page.evaluate(() => window.__n);
await page.evaluate(() => document.activeElement.blur());
await sleep(900);
const afterBlur = await page.evaluate(() => ({
  n: window.__n,
  holds: activeHolds,
  verdict: document.querySelector('.verdict').textContent.trim(),
}));
await page.mouse.up();
await sleep(400);
console.log(
  `steps before blur=${beforeBlur}, 900ms after blur=${afterBlur.n} (${afterBlur.n - beforeBlur} more,` +
    ` one of which is the release's own read swap), activeHolds=${afterBlur.holds},` +
    ` verdict="${afterBlur.verdict}"`
);
await browser.close();
