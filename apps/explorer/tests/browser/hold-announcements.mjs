// What the status line actually says, and how often, across a hold and the
// read that follows it.
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
await page.goto(`${BASE}/stage/llull_figure`, { waitUntil: 'networkidle' });
await page.evaluate(() => {
  window.__says = [];
  window.__panel = 0;
  new MutationObserver(() =>
    window.__says.push(document.getElementById('llull-status').textContent)
  ).observe(document.getElementById('llull-status'), { characterData: true, childList: true, subtree: true });
  new MutationObserver(() => window.__panel++).observe(document.getElementById('llull-reading'), {
    characterData: true, childList: true, subtree: true,
  });
});
const b = await page.locator('.hold-group[data-wheel-index="0"] .hold-btn[data-hold-dir="1"]').boundingBox();
await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
await page.mouse.down();
await sleep(1600);
await page.mouse.up();
await sleep(900);
const out = await page.evaluate(() => ({
  says: window.__says,
  panelMutations: window.__panel,
  live: [...document.querySelectorAll('[aria-live]')].map(
    (e) => `${e.id || e.className}: ${e.getAttribute('aria-live')} atomic=${e.getAttribute('aria-atomic')}`
  ),
}));
console.log('live regions:', JSON.stringify(out.live));
console.log(`panel mutations during a 1.6s hold: ${out.panelMutations}`);
console.log('status line said:', JSON.stringify(out.says));
await browser.close();
