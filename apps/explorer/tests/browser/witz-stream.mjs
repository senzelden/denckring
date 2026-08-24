// The wait, on both pages that can ask for a reading.
//
// `static/witz_stream.js` is the only thing standing between a pressed button
// and half a minute of empty box, and none of it is reachable from `pytest`:
// the Python suite runs no JavaScript, so it can assert that the file is
// served and loaded and nothing at all about whether the indicator appears.
// That gap is the bug's own hiding place — the stage had a working reader
// inlined in its fragment and the bench, rendering the same form, had none,
// and every Python test passed throughout.
//
// This costs one real API call per page it drives. There is no way to check
// "the indicator is up while the model thinks" against a stub, because the
// thing being checked is the thinking.
//
//   stage   drive scene two's throw, then its reading.
//   bench   drive /p/ideenwuerfeln's apply, then its reading.
//   both    one after the other.
//
//   BASE=http://127.0.0.1:8477 node tests/browser/witz-stream.mjs both
//
// What it holds each page to:
//   - the indicator is showing within 2s of the press, and says a number;
//   - that number climbs, so a stalled stream cannot pass as a slow one;
//   - the indicator is gone once the paragraph has any text;
//   - the box is never left empty with no indicator over it — the exact
//     state the file exists to prevent, sampled throughout rather than
//     checked once at the end.

import { chromium } from 'playwright';

const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const MODE = process.argv[2] || 'both';

const PAGES = {
  stage: {
    url: `${BASE}/stage/ideenwuerfeln`,
    start: async (page) => {
      await page.click('.throw-form button[type=submit]');
      await page.waitForSelector('.witz-form', { timeout: 60000 });
    },
  },
  bench: {
    url: `${BASE}/p/ideenwuerfeln`,
    // Two presses before there is anything to read: the bench will not
    // generate from a corpus it has not loaded, and the witz form only exists
    // on the generated result.
    start: async (page) => {
      // Waited on the responses rather than on the buttons: both presses swap
      // the panel the next button lives in, so a selector can match the node
      // that is about to be replaced and click something already detached.
      await Promise.all([
        page.waitForResponse((r) => r.url().endsWith('/corpus'), { timeout: 60000 }),
        page.click('.corpus-picker button[type=submit]'),
      ]);
      await page.waitForTimeout(800);
      await Promise.all([
        page.waitForResponse((r) => r.url().endsWith('/apply'), { timeout: 60000 }),
        page.click('button:has-text("Generate from it")'),
      ]);
      await page.waitForSelector('.witz-form', { timeout: 60000 });
    },
  },
};

async function drive(browser, name) {
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(PAGES[name].url, { waitUntil: 'networkidle' });
  await PAGES[name].start(page);

  const pressed = Date.now();
  await page.click('.witz-form button');

  // Sampled rather than checked once: "it said something at the end" is true
  // of a box that was blank for twenty seconds first.
  const seen = { indicatorFirstAt: null, seconds: [], emptyWithNoIndicator: 0, samples: 0 };
  let text = '';
  for (;;) {
    const state = await page.evaluate(() => {
      const waiting = document.querySelector('.witz-waiting');
      const para = document.querySelector('.witz-reading');
      return {
        waiting: waiting ? waiting.textContent.trim() : null,
        text: para ? para.textContent : null,
      };
    });
    seen.samples++;
    if (state.waiting && seen.indicatorFirstAt === null) seen.indicatorFirstAt = Date.now() - pressed;
    if (state.waiting) {
      const n = Number((state.waiting.match(/(\d+)s/) || [])[1]);
      if (!Number.isNaN(n)) seen.seconds.push(n);
    }
    if (!state.waiting && !(state.text && state.text.length)) seen.emptyWithNoIndicator++;
    text = state.text || '';
    if (text.length > 40) break;
    if (Date.now() - pressed > 120000) break;
    await page.waitForTimeout(250);
  }
  await page.waitForTimeout(1500);
  const after = await page.evaluate(() => ({
    waiting: !!document.querySelector('.witz-waiting'),
    text: (document.querySelector('.witz-reading') || {}).textContent || '',
  }));

  const climbed = seen.seconds.length > 1 && seen.seconds[seen.seconds.length - 1] > seen.seconds[0];
  const checks = [
    ['indicator up within 2s', seen.indicatorFirstAt !== null && seen.indicatorFirstAt <= 2000],
    ['indicator counts a number', seen.seconds.length > 0],
    ['the count climbs', climbed],
    ['indicator gone once there is text', !after.waiting],
    ['paragraph arrived', after.text.trim().length > 40],
    ['never empty with no indicator', seen.emptyWithNoIndicator === 0],
  ];
  const bad = checks.filter(([, ok]) => !ok);
  console.log(
    `${name.padEnd(6)} first indicator ${String(seen.indicatorFirstAt).padStart(5)}ms  ` +
      `counted ${seen.seconds[0] ?? '-'}s..${seen.seconds[seen.seconds.length - 1] ?? '-'}s  ` +
      `${after.text.trim().length} chars`
  );
  for (const [label, ok] of checks) console.log(`   ${ok ? '  ok' : '**  '} ${label}`);
  if (errors.length) console.log('   PAGE ERRORS:', errors.slice(0, 3));
  await context.close();
  return bad.length === 0 && errors.length === 0;
}

const browser = await chromium.launch();
const names = MODE === 'both' ? ['stage', 'bench'] : [MODE];
let allGood = true;
for (const name of names) allGood = (await drive(browser, name)) && allGood;
console.log(allGood ? 'both waits say what they are doing' : 'FAILED');
await browser.close();
