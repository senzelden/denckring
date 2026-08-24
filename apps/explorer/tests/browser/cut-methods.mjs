// Scene six (`/stage/cut_up`): the four operations, each against its own
// checker.
//
// The picker turned one scene into four, and the three it added are all
// client-side arrangements of the page checked by a *different* procedure —
// `fold_in`, nothing at all, `column_reading`. Nothing here is reachable from
// `pytest`: the test client runs no JavaScript, so a Python test can only post
// a fold it built itself and watch the route agree with it. It cannot see
// whether the fold the *page* produces is the same fold.
//
// That distinction is not academic. The first fold this scene performed came
// back "12 lines are not the fold" for a fold that was correct in every word:
// the two halves of each folded line come off two different pages, start at
// two different heights, and the one from page B only arrives at page A's line
// as a `transform` — so reading the result back by where a piece was standing
// gave twelve rows instead of six. The Python suite was green throughout.
//
//   run     perform all four operations in order and read each verdict back.
//           The word bag must come back with no verdict element of any class.
//   switch  start an operation and pick another one mid-animation. No verdict
//           may be left standing, and the page must be whole again.
//   reduced the same as `run` under `prefers-reduced-motion`, which kills
//           every transition with `!important` and is where a choreography
//           that waits on `transitionend` deadlocks.
//
//   BASE=http://127.0.0.1:8477 node tests/browser/cut-methods.mjs run
//   BASE=... node tests/browser/cut-methods.mjs reduced
//   BASE=... node tests/browser/cut-methods.mjs switch

import { chromium } from 'playwright';

const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const MODE = process.argv[2] || 'run';

// What each operation's verdict has to say about itself. Substrings, not whole
// lines: the counts inside them are rendered from the report and would pin
// this file to arithmetic that belongs in the Python suite.
const EXPECTED = {
  quarter: 'words across the join is the page',
  // No apostrophes: the template renders `&rsquo;`, so a straight quote here
  // matches nothing and reports a correct fold as a failure.
  fold: 'lines join page one',
  column: 'are the column, read down in line order',
};

async function operate(page, method) {
  await page.click(`.cutup-method[data-method="${method}"]`);
  await page.waitForTimeout(200);
  const started = Date.now();
  await page.click('#cutup-cut');
  // Both endings, and *settled* ones. Three things can be in this box: the
  // placeholder `.verdict.turning`, which is what "Fresh sheet" leaves behind
  // and what the scene wears while an operation runs; a real verdict; or the
  // bag's line. Waiting on a bare `.verdict` matches the placeholder that is
  // already there and returns instantly with the previous state — measured,
  // and it reported two correct operations as failures.
  await page
    .waitForSelector(
      '#cutup-result .verdict.yes, #cutup-result .verdict.no,' +
        ' #cutup-result .cutup-uncheckable-head',
      { timeout: 20000 }
    )
    .catch(() => {});
  return {
    ms: Date.now() - started,
    verdict: (await page.textContent('#cutup-result').catch(() => '')).replace(/\s+/g, ' ').trim(),
    classes: await page.evaluate(
      () => Array.from(document.querySelectorAll('#cutup-result .verdict')).map((el) => el.className)
    ),
    checked: await page.evaluate(() => {
      const el = document.querySelector('#cutup-result [data-checked]');
      return el ? el.dataset.checked : null;
    }),
  };
}

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1400, height: 900 },
  reducedMotion: MODE === 'reduced' ? 'reduce' : 'no-preference',
});
const page = await context.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
await page.goto(`${BASE}/stage/cut_up`, { waitUntil: 'networkidle' });
await page.waitForTimeout(700);

if (MODE === 'run' || MODE === 'reduced') {
  let bad = 0;
  for (const method of ['quarter', 'fold', 'bag', 'column']) {
    const result = await operate(page, method);
    if (method === 'bag') {
      // The whole claim: `dada_poem` is catalogued uncheckable, so this one
      // ends in no verdict of any class — including `turning`, which
      // everywhere else on this stage means a claim is on its way.
      const ok = result.classes.length === 0 && /Nothing to check/.test(result.verdict);
      if (!ok) bad++;
      console.log(`bag     ${String(result.ms).padStart(5)}ms  ${ok ? 'no verdict — correct' : `** ${result.classes.join()} **`}`);
    } else {
      const ok = result.classes.some((c) => c.includes('yes')) && result.verdict.includes(EXPECTED[method]);
      if (!ok) bad++;
      console.log(`${method.padEnd(7)} ${String(result.ms).padStart(5)}ms  ${ok ? 'green' : '** ' + result.verdict.slice(0, 70) + ' **'}`);
    }
    // Every operation is read off the screen, so every one carries the exact
    // text it was checked on. A missing `data-checked` means the fragment
    // stopped being holdable to what it showed.
    if (result.checked === null) {
      console.log(`   ** ${method}: no data-checked **`);
      bad++;
    }
    await page.click('#cutup-fresh');
    await page.waitForTimeout(200);
  }
  console.log(bad === 0 ? 'all four operations agree with their own checker' : `${bad} wrong`);
} else if (MODE === 'switch') {
  await page.click('.cutup-method[data-method="quarter"]');
  await page.waitForTimeout(200);
  await page.click('#cutup-cut');
  await page.waitForTimeout(300); // mid-animation, before the submit
  await page.click('.cutup-method[data-method="bag"]');
  await page.waitForTimeout(2500);
  const left = await page.evaluate(() => ({
    verdicts: document.querySelectorAll('#cutup-result .verdict.yes, #cutup-result .verdict.no').length,
    whole: !document.getElementById('cutup-page').hidden,
    said: (document.getElementById('cutup-result').textContent || '').replace(/\s+/g, ' ').trim(),
  }));
  console.log(`real verdicts left standing ${left.verdicts} (want 0), page whole ${left.whole} (want true)`);
  console.log(`  panel says: ${left.said.slice(0, 70)}`);
} else {
  console.log(`unknown mode ${MODE}`);
}

if (errors.length) console.log('PAGE ERRORS:', errors.slice(0, 3));
await browser.close();
