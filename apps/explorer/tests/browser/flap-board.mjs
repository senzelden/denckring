// Scene eight (`/stage/poesie_automat`): the letter board, its clatter, its two
// cartridges, and the verdict on the poem the cells are showing.
//
// All of it against a real Chromium, because none of it is reachable from
// `pytest` — the test client runs no JavaScript, and every one of this board's
// 426 cells is turned in the browser.
//
//   drag    a module moves *under the pointer*, sampled while it is still down.
//           A run that only checked where it landed would prove nothing about
//           the gesture. Reports the flaps crossed, whether the row tracked the
//           hand, and whether a real verdict was ever on screen while the hand
//           was on the board.
//   press   press the button, clock the whole clatter inside the page, and
//           compare the poem the cells are showing — read character by
//           character out of the DOM — with the `data-checked` the verdict came
//           back carrying. Pins the honesty requirement: what `check` was given
//           is what is on the board, never the poem the seed produced.
//   wave    the two constraints the clatter actually has to meet, measured in
//           the page rather than read off the source: the **span** between the
//           first cell of a press starting to fold and the last one starting,
//           and the **dwell** between one fold landing on a cell and the next
//           starting on it. This is the guard the source-level one cannot be:
//           the previous Python test asserted `const STAGGER_MS = \d+` and
//           `\d+` matches `0`, so a board resolving in unison passed its own
//           test. Here the floor is measured. Takes a run count (default 12).
//   roll    that a cell travelling between two characters turns through every
//           character in between, and that the cap is the only thing that ever
//           shortens the journey. Reports each moved cell's fold count against
//           the alphabet distance it had to cover.
//   reverse a module turned one way and straight back **inside one fold**, by
//           the drag and by the keyboard, at dwells of 10/20/40ms. The oracle is
//           built from the glyphs the cells are actually rendering, not from the
//           page's own `cell.char`, because the defect this exists for is the
//           two disagreeing. `drawBoard` used to skip a cell whose *current*
//           character already equalled the new target while a roll was still in
//           flight on it, and nothing made that roll stale — so it landed the
//           cell on its own old target and the board came to rest spelling a
//           character no flap of any module contains.
//   swap    the cartridge switcher: the flaps change, the cells do not move,
//           the alphabet is the incoming board's own, and the verdict that was
//           true of the old cartridge does not survive into the new one. Also
//           checks the check: the reply is about the device the board is now
//           showing.
//   stale   turn a module *during* the read's round trip (`DELAY`, default
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
//   contend a grab begun *during* an in-flight press (`DELAY`, default 900ms),
//           which used to survive into the clatter — a hand and the machine
//           writing one row. Counts samples with the board clattering under a
//           hand, and the POSTs the whole gesture costs.
//   widths  the measurement the whole layout turns on: 71 cells in the width
//           the stage leaves, what that makes one cell, and what type size that
//           cell can carry. Also reports the board's own `data-fits` and the
//           scene's content extent against the 720px budget.
//   frames  first paint, a frame mid-clatter and the resolved board, for both
//           cartridges, written to `OUT` (default /tmp).
//
// `BASE` defaults to http://127.0.0.1:8477. `REDUCED=1` runs under the
// `reducedMotion: 'reduce'` **context option** (never the launch flag), where
// every cell must arrive at its character at once and the drag must still work.
import { chromium } from 'playwright';

const BASE = process.env.BASE || 'http://127.0.0.1:8477';
const OUT = process.env.OUT || '/tmp';
const REDUCED = process.env.REDUCED === '1';
const DELAY = Number(process.env.DELAY || 600);
const mode = process.argv[2] || 'drag';

function log(...args) {
  console.log(...args);
}

async function open(browser, query) {
  const context = await browser.newContext({
    viewport: { width: 1320, height: 860 },
    reducedMotion: REDUCED ? 'reduce' : 'no-preference',
  });
  const page = await context.newPage();
  page.on('pageerror', (e) => log('PAGEERROR', e.message));
  await page.goto(`${BASE}/stage/poesie_automat?chrome=off${query || ''}`);
  await page.waitForFunction(() => typeof cells !== 'undefined' && cells.length === 6);
  // The cell pitch is arithmetic but the *type* in it is the face's, so nothing
  // is measured before the face has actually arrived.
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => fitBoard());
  return page;
}

// Everything the page knows about itself, asked of the page rather than
// reconstructed here.
async function state(page) {
  return page.evaluate(() => ({
    inert: inert,
    clattering: clattering,
    activeModules: activeModules,
    boardToken: boardToken,
    submittedToken: submittedToken,
    deferredRead: deferredRead,
    device: document.getElementById('automat-device').value,
    alphabet: alphabet,
    // The attribution, which has to describe the flaps actually on the board.
    kicker: document.getElementById('automat-kicker').textContent.trim(),
    credit: document.getElementById('automat-credit').textContent.trim(),
    indices: positions.slice(),
    // The poem the cells are showing, by the page's own reader — the same call
    // the submit uses, so the harness cannot disagree with it.
    shown: readBoard(),
    pressDisabled: document.getElementById('automat-press').disabled,
    readDisabled: document.getElementById('automat-read').disabled,
    switchDisabled: Array.from(document.querySelectorAll('#cartridge-switch input')).every(
      (i) => i.disabled
    ),
    verdict: (() => {
      const v = document.querySelector('#automat-reading .verdict');
      return v
        ? { cls: v.className, text: v.textContent.trim(), checked: v.dataset.checked }
        : null;
    })(),
  }));
}

async function waitVerdict(page, ms = 30000) {
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

// The instrument every timing mode uses: stamps inside the page for when a cell
// starts a fold, when one lands, and when the whole board starts and stops
// running. Wrapped around the scene's own functions rather than reimplemented,
// so the harness cannot measure something the board is not doing.
//
// The board's own start and stop have to be stamped **in the page** rather than
// polled from here, and that is not a nicety: under reduced motion every cell
// lands at once, so `clattering` is true for less than one task and no
// `waitForFunction` can ever observe it. A harness that polled for it would
// report a timeout on the one configuration where the board is behaving
// perfectly.
async function instrument(page) {
  await page.evaluate(() => {
    window.__trace = { folds: [], lands: [] };
    window.__runs = [];
    const realFold = window.foldCell;
    window.foldCell = function (cell, next, settling) {
      window.__trace.folds.push({ t: performance.now(), cell: cell, to: next });
      return realFold(cell, next, settling);
    };
    const realLand = window.landCell;
    window.landCell = function (cell, character) {
      window.__trace.lands.push({ t: performance.now(), cell: cell });
      return realLand(cell, character);
    };
    ['clatterTo', 'loadCartridge'].forEach((name) => {
      const real = window[name];
      window[name] = function (argument) {
        const run = { what: name, start: performance.now(), end: null };
        window.__runs.push(run);
        return real(argument).then((value) => {
          run.end = performance.now();
          return value;
        });
      };
    });
  });
}

// One run of the board under its own power — a press or a cartridge swap —
// from the page's own clock. Returns its length in ms.
async function waitRun(page, ms = 60000) {
  await page.waitForFunction(
    () => window.__runs.length > 0 && window.__runs[window.__runs.length - 1].end !== null,
    { timeout: ms }
  );
  return page.evaluate(() => {
    const run = window.__runs[window.__runs.length - 1];
    return run.end - run.start;
  });
}

function summarise(values) {
  const sorted = values.slice().sort((a, b) => a - b);
  return {
    n: sorted.length,
    min: +sorted[0].toFixed(1),
    median: +sorted[Math.floor(sorted.length / 2)].toFixed(1),
    max: +sorted[sorted.length - 1].toFixed(1),
  };
}

// ── drag ───────────────────────────────────────────────────────────────────
async function runDrag(browser) {
  const page = await open(browser);
  const slot = Number(process.argv[3] || 2);
  const box = await page.evaluate((slot) => {
    const r = document.getElementById('module-' + slot).getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, h: r.height };
  }, slot);
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  const samples = [];
  for (let step = 1; step <= 6; step++) {
    await page.mouse.move(box.x, box.y - box.h * step);
    await page.waitForTimeout(160);
    samples.push(
      await page.evaluate((slot) => {
        const v = document.querySelector('#automat-reading .verdict');
        const line = Math.floor(slot / 6);
        const module = cart.modules[slot];
        const word = module.flaps[positions[slot]];
        const start = Number(document.getElementById('module-' + slot).style.getPropertyValue('--start'));
        const span = Number(document.getElementById('module-' + slot).style.getPropertyValue('--span'));
        const under = cells[line].slice(start, start + span).map((c) => c.char).join('');
        return {
          index: positions[slot],
          word: word,
          underHandle: under,
          handleAgrees: under === word,
          activeModules: activeModules,
          realVerdict: !!v && !v.classList.contains('turning'),
        };
      }, slot)
    );
  }
  await page.mouse.up();
  const after = await waitVerdict(page);
  const crossed = samples.map((s) => s.index);
  log('drag module', slot, REDUCED ? '(reduced motion)' : '');
  log('  flaps crossed        ', crossed.join(' -> '));
  log('  handle over its word ', samples.filter((s) => s.handleAgrees).length + '/' + samples.length);
  log('  real verdict in hand ', samples.filter((s) => s.realVerdict).length + '/' + samples.length);
  log('  activeModules peak   ', Math.max(...samples.map((s) => s.activeModules)));
  log('  after release        ', after.verdict.cls, '|', after.verdict.text.split('\n')[0].trim());
  log('  checked == on screen ', after.verdict.checked === after.shown);
}

// ── press ──────────────────────────────────────────────────────────────────
async function runPress(browser) {
  const page = await open(browser);
  await instrument(page);
  const before = await state(page);
  await page.click('#automat-press');
  const clatter = await waitRun(page);
  const after = await waitVerdict(page);
  const folds = await page.evaluate(() => window.__trace.folds.length);
  log('press', REDUCED ? '(reduced motion)' : '');
  log('  clatter              ', clatter.toFixed(0) + 'ms');
  log('  folds                ', folds, REDUCED ? '(reduced motion: every cell lands at once)' : '');
  log('  verdict              ', after.verdict.cls, '|', after.verdict.text.split('\n')[0].trim());
  log('  checked == on screen ', after.verdict.checked === after.shown);
  log('  board changed        ', before.shown !== after.shown);
  log('  shown\n' + after.shown.split('\n').map((l) => '    ' + l).join('\n'));
}

// ── wave ───────────────────────────────────────────────────────────────────
//
// The measured floor the source-level guard cannot be, and the shape of that
// measurement is itself a finding.
//
// The obvious number — the **span** between the first cell folding and the last
// — does not work, and I only know that because I set `STAGGER_MS` to 0 and ran
// it: the span was 2618-3038ms and the mode said PASS. On a board of 426 cells
// the main thread is the bottleneck, so a board told to start everything at
// once *still* spreads its folds over three seconds. A floor on the span
// measures congestion, not a wave.
//
// What actually separates the two is **where** the folding cells are, not when:
//
//   band   how many columns the folding set spans at one moment. A wave is a
//          narrow front; a board starting in unison is folding everywhere.
//          Measured: 13-18 columns staggered, 59-64 in unison.
//   front  the mean column of the folding set, early in the clatter against
//          late in it. A wave sweeps; unison sits still. Measured: 3.6 -> 57.2
//          staggered (an advance of ~50 columns), 34.2 -> 34.8 in unison.
//
// Sampled inside the page on `requestAnimationFrame`, because a poll from the
// harness round-trips and would miss most of it. `dwell` is kept from the
// original: it is what says a cell folds *more than once* on its way, which is
// the other half of the machine's identity.
async function runWave(browser) {
  const runs = Number(process.argv[3] || 12);
  const bands = [];
  const advances = [];
  const dwells = [];
  const concurrency = [];
  const clatters = [];
  for (let run = 0; run < runs; run++) {
    const page = await open(browser);
    await instrument(page);
    await page.evaluate(() => {
      window.__wave = [];
      window.__polling = true;
      const tick = () => {
        const columns = [];
        cells.forEach((row) =>
          row.forEach((cell, column) => {
            if (cell.el.classList.contains('folding')) columns.push(column);
          })
        );
        if (columns.length) {
          window.__wave.push({
            n: columns.length,
            band: Math.max(...columns) - Math.min(...columns),
            mean: columns.reduce((a, b) => a + b, 0) / columns.length,
          });
        }
        if (window.__polling) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    await page.click('#automat-press');
    const clatter = await waitRun(page);
    await page.evaluate(() => {
      window.__polling = false;
    });
    const measured = await page.evaluate(() => {
      const wave = window.__wave;
      const perCell = new Map();
      window.__trace.folds.forEach((f) => {
        const list = perCell.get(f.cell) || [];
        list.push(f.t);
        perCell.set(f.cell, list);
      });
      const dwells = [];
      perCell.forEach((list) => {
        for (let i = 1; i < list.length; i++) dwells.push(list[i] - list[i - 1]);
      });
      if (!wave.length) return { band: null, advance: null, peak: 0, dwells: dwells };
      const third = Math.max(1, Math.floor(wave.length / 3));
      const mean = (values) => values.reduce((a, b) => a + b, 0) / values.length;
      const bands = wave.map((w) => w.band).sort((a, b) => a - b);
      return {
        band: bands[Math.floor(bands.length / 2)],
        advance: mean(wave.slice(-third).map((w) => w.mean)) - mean(wave.slice(0, third).map((w) => w.mean)),
        peak: Math.max(...wave.map((w) => w.n)),
        dwells: dwells,
      };
    });
    if (measured.band !== null) {
      bands.push(measured.band);
      advances.push(measured.advance);
      concurrency.push(measured.peak);
    }
    dwells.push(...measured.dwells);
    clatters.push(clatter);
    await page.context().close();
  }
  log('wave over', runs, 'presses', REDUCED ? '(reduced motion)' : '');
  if (!dwells.length) {
    log('  no cell folded at all — under reduced motion every cell lands at once, which is right');
    log('  clatter', JSON.stringify(summarise(clatters)), 'ms');
    return;
  }
  const bandStats = summarise(bands);
  const advanceStats = summarise(advances);
  const dwellStats = summarise(dwells);
  log('  columns folding at once (band)', JSON.stringify(bandStats), 'of ' + 71);
  log('  front, early to late          ', JSON.stringify(advanceStats), 'columns');
  log('  dwell between folds of a cell ', JSON.stringify(dwellStats), 'ms');
  log('  cells folding at once         ', JSON.stringify(summarise(concurrency)));
  log('  clatter                       ', JSON.stringify(summarise(clatters)), 'ms');
  // The floors, and each one is between the two measured configurations rather
  // than beside one of them. A board starting in unison bands 59-64 and
  // advances 0-9; this board bands 13-18 and advances ~50.
  const BAND_CEILING = 35;
  const ADVANCE_FLOOR = 20;
  const DWELL_FLOOR_MS = 20;
  const bandOk = bandStats.max <= BAND_CEILING;
  const advanceOk = advanceStats.min >= ADVANCE_FLOOR;
  const dwellOk = dwellStats.min >= DWELL_FLOOR_MS;
  log('  band <= ' + BAND_CEILING + ' columns          ', bandOk ? 'PASS' : 'FAIL');
  log('  front advances >= ' + ADVANCE_FLOOR + ' columns', advanceOk ? 'PASS' : 'FAIL');
  log('  dwell >= ' + DWELL_FLOOR_MS + 'ms              ', dwellOk ? 'PASS' : 'FAIL');
  log('  ' + (bandOk && advanceOk && dwellOk ? 'PASS' : 'FAIL'));
}

// ── roll ───────────────────────────────────────────────────────────────────
async function runRoll(browser) {
  const page = await open(browser);
  await instrument(page);
  const before = await page.evaluate(() => cells.map((row) => row.map((c) => c.char)));
  await page.click('#automat-press');
  await waitRun(page);
  const result = await page.evaluate((before) => {
    const perCell = new Map();
    window.__trace.folds.forEach((f) => {
      const list = perCell.get(f.cell) || [];
      list.push(f.to);
      perCell.set(f.cell, list);
    });
    const rows = [];
    let contiguous = 0;
    let capped = 0;
    let exact = 0;
    perCell.forEach((letters, cell) => {
      const line = cells.findIndex((row) => row.indexOf(cell) >= 0);
      const column = cells[line].indexOf(cell);
      const from = before[line][column];
      const to = cell.char;
      const size = alphabet.length;
      const distance = ((alphabet.indexOf(to) - alphabet.indexOf(from)) % size + size) % size;
      // Every letter this cell showed, in order, has to be the next one in the
      // alphabet each time — that is what "turns through the characters in
      // between" means, and it is checked rather than assumed.
      let walked = true;
      let previous = letters.length === distance ? from : null;
      if (previous === null) {
        // A capped roll starts `MAX_ROLL` short of the target rather than where
        // the cell stood, so the first letter is where the seating put it.
        previous = alphabet[((alphabet.indexOf(to) - letters.length) % size + size) % size];
      }
      letters.forEach((letter) => {
        if (alphabet[(alphabet.indexOf(previous) + 1) % size] !== letter) walked = false;
        previous = letter;
      });
      if (walked) contiguous++;
      if (letters.length === distance) exact++;
      else capped++;
      rows.push({ from: from, to: to, distance: distance, folds: letters.length });
    });
    return {
      moved: perCell.size,
      contiguous: contiguous,
      exact: exact,
      capped: capped,
      cap: MAX_ROLL,
      alphabet: alphabet.length,
      sample: rows.slice(0, 8),
    };
  }, before);
  log('roll', REDUCED ? '(reduced motion)' : '');
  log('  alphabet             ', result.alphabet, 'characters, cap', result.cap, 'folds');
  log('  cells that moved     ', result.moved);
  log('  turned through every character in between:', result.contiguous + '/' + result.moved);
  log('  journeys inside cap  ', result.exact, '| journeys the cap shortened', result.capped);
  result.sample.forEach((r) =>
    log('    ' + JSON.stringify(r.from) + ' -> ' + JSON.stringify(r.to) + '  distance ' + r.distance + ', folds ' + r.folds)
  );
  log('  ' + (result.contiguous === result.moved ? 'PASS' : 'FAIL'));
}

// ── reverse ────────────────────────────────────────────────────────────────
//
// Turn a module and turn it back before the fold has landed — **once**, and
// then three and four times in a row, all inside `FOLD_MS`.
//
// The one-reversal case is the Critical this mode was written for. The
// oscillation is the *class* it belongs to: eleven earlier modes never reversed
// at all, which is how a single reversal got through, and a mode that only ever
// reverses once is the same narrowing one notch further along. Three and four
// changes of direction also cover both parities — an even number of moves puts
// the module back where it started, an odd number leaves it one flap along —
// so neither "it healed because it ended where it began" nor "it never had to
// come back" can hide a stranded cell.
//
// The oracle reads the **rendered** glyph out of each cell's static bottom half
// rather than the page's own `cell.char`, because what went wrong was those two
// disagreeing: the model said `DER NEBEL`, the accessible tree said
// `"Der Nebel"`, and the board spelled `DER NECEL` for the rest of the session.
// It also checks the module's own index against the displacement the gesture
// asked for, so a board that agreed with itself about the wrong flap is caught.
async function runReverse(browser) {
  const slot = Number(process.argv[3] || 6);
  const line = Math.floor(slot / 6);
  let bad = 0;
  let runs = 0;
  for (const route of ['drag', 'keyboard']) {
    for (const dwell of [10, 20, 40]) {
      for (const turns of [1, 3, 4]) {
        // `turns` changes of direction is `turns + 1` moves, alternating up,
        // down, up… so an even count of moves lands back on the starting flap
        // and an odd count lands one along.
        const moves = turns + 1;
        const expectedShift = moves % 2 === 0 ? 0 : 1;
        const page = await open(browser);
        await waitVerdict(page);
        const start = await page.evaluate(
          (arg) => ({
            row: Array.from(
              document.querySelectorAll('.board-line')[arg.line].querySelectorAll('.cell')
            )
              .map((cell) => cell.querySelector('.cell-bottom span').textContent)
              .join('')
              .trim(),
            index: positions[arg.slot],
            size: cart.modules[arg.slot].flaps.length,
          }),
          { line: line, slot: slot }
        );
        if (route === 'drag') {
          const box = await page.evaluate((slot) => {
            const r = document.getElementById('module-' + slot).getBoundingClientRect();
            return { x: r.left + r.width / 2, y: r.top + r.height / 2, h: r.height };
          }, slot);
          await page.mouse.move(box.x, box.y);
          await page.mouse.down();
          for (let move = 0; move < moves; move++) {
            // Up one flap on the even moves, back to the grab point on the odd
            // ones. Dragging up is what advances a module — the sign the
            // volvelles' own drag carries.
            await page.mouse.move(box.x, box.y - (move % 2 === 0 ? box.h : 0));
            if (move < moves - 1) await page.waitForTimeout(dwell);
          }
          await page.mouse.up();
        } else {
          await page.focus('#module-' + slot);
          for (let move = 0; move < moves; move++) {
            await page.keyboard.press(move % 2 === 0 ? 'ArrowUp' : 'ArrowDown');
            if (move < moves - 1) await page.waitForTimeout(dwell);
          }
        }
        const after = await waitVerdict(page);
        const found = await page.evaluate(
          (arg) => {
            const row = document.querySelectorAll('.board-line')[arg.line];
            return {
              // What the cells are painting, glyph by glyph.
              rendered: Array.from(row.querySelectorAll('.cell'))
                .map((cell) => cell.querySelector('.cell-bottom span').textContent)
                .join('')
                .trim(),
              // What the model says they should be painting.
              model: [0, 1, 2, 3, 4, 5]
                .map((k) => cart.modules[arg.line * 6 + k].flaps[positions[arg.line * 6 + k]])
                .join(' '),
              // And what the page itself thinks each cell shows.
              shown: readBoard().split('\n')[arg.line],
              index: positions[arg.slot],
              valuetext: document
                .getElementById('module-' + arg.slot)
                .getAttribute('aria-valuetext'),
              word: cart.modules[arg.slot].words[positions[arg.slot]],
              stillFolding: row.querySelectorAll('.cell.folding').length,
            };
          },
          { line: line, slot: slot }
        );
        runs++;
        const wantedIndex = (start.index + expectedShift) % start.size;
        const ok =
          found.rendered === found.model &&
          found.rendered === found.shown &&
          found.index === wantedIndex &&
          found.valuetext === found.word &&
          found.stillFolding === 0 &&
          (expectedShift === 0 ? found.rendered === start.row : true) &&
          after.verdict.cls.indexOf('no') < 0;
        if (!ok) bad++;
        log(
          '  ' + route.padEnd(8),
          String(turns) + ' turn' + (turns === 1 ? ' ' : 's'),
          'dwell ' + String(dwell).padStart(2) + 'ms ',
          'net ' + expectedShift,
          ok ? 'ok  ' : 'BAD ',
          JSON.stringify(found.rendered)
        );
        if (!ok) {
          log('      model     ', JSON.stringify(found.model));
          log('      readBoard ', JSON.stringify(found.shown));
          log('      started   ', JSON.stringify(start.row));
          log('      index     ', found.index, 'wanted', wantedIndex);
          log('      valuetext ', JSON.stringify(found.valuetext), 'module says', JSON.stringify(found.word));
          log('      verdict   ', after.verdict.cls, '|', after.verdict.text.split('\n')[0].trim());
          log('      folding   ', found.stillFolding);
        }
        await page.context().close();
      }
    }
  }
  log('reverse on module', slot, REDUCED ? '(reduced motion)' : '');
  log('  runs that ended with the board spelling something else', bad + '/' + runs);
  log('  ' + (bad === 0 ? 'PASS' : 'FAIL'));
}

// ── swap ───────────────────────────────────────────────────────────────────
async function runSwap(browser) {
  const page = await open(browser);
  const before = await waitVerdict(page);
  // A real verdict is standing, about the Landsberg cartridge. Now change the
  // flaps under it.
  await instrument(page);
  // The verdict's own history, not a sample of it. Under reduced motion the
  // whole swap takes about ten milliseconds and the read that follows lands
  // before this harness can ask a question — so a sampled `during` would find a
  // *new* real verdict and report the invariant broken when it is being kept.
  // What the invariant actually says is that no verdict ever stands over a board
  // the viewer has changed, and that is a claim about the sequence.
  await page.evaluate(() => {
    window.__verdicts = [];
    const target = document.getElementById('automat-reading');
    const record = () => {
      const v = target.querySelector('.verdict');
      const cls = v ? (v.classList.contains('turning') ? 'placeholder' : 'real') : 'none';
      const last = window.__verdicts[window.__verdicts.length - 1];
      if (!last || last.cls !== cls) window.__verdicts.push({ t: performance.now(), cls: cls });
    };
    record();
    new MutationObserver(record).observe(target, {
      subtree: true,
      childList: true,
      attributes: true,
      characterData: true,
    });
    window.__swapAt = null;
    const realSwap = window.swapCartridge;
    window.swapCartridge = function (id) {
      window.__swapAt = performance.now();
      return realSwap(id);
    };
  });
  await page.click('#cartridge-1');
  const swap = await waitRun(page);
  const after = await waitVerdict(page);
  // And what the server was asked, which is the honesty half: a verdict is only
  // true of the device it was checked against.
  const posted = [];
  page.on('request', (request) => {
    if (request.method() === 'POST') posted.push(request.postData());
  });
  await page.click('#automat-press');
  const pressed = await waitVerdict(page);
  log('swap', REDUCED ? '(reduced motion)' : '');
  log('  cells before/after   ', before.shown.split('\n')[0], '|', after.shown.split('\n')[0]);
  log('  cell count unchanged ', await page.evaluate(() => document.querySelectorAll('.cell').length));
  const history = await page.evaluate(() => ({
    swapAt: window.__swapAt,
    seq: window.__verdicts.map((v) => ({ cls: v.cls, at: +(v.t - window.__swapAt).toFixed(0) })),
  }));
  const afterClick = history.seq.filter((v) => v.at >= 0);
  const wentToPlaceholder = afterClick.length > 0 && afterClick[0].cls === 'placeholder';
  log('  verdict history      ', JSON.stringify(history.seq));
  log('  first thing after the swap was the placeholder', wentToPlaceholder ? 'yes' : 'NO (BUG)');
  log('  swap                 ', swap.toFixed(0) + 'ms');
  log('  device now           ', after.device);
  log('  alphabet before/after', JSON.stringify(before.alphabet), '->', JSON.stringify(after.alphabet));
  log('  eyebrow before       ', JSON.stringify(before.kicker));
  log('  eyebrow after        ', JSON.stringify(after.kicker));
  log('  eyebrow followed the cartridge', before.kicker !== after.kicker ? 'yes' : 'NO (BUG)');
  log('  footnote followed it ', before.credit !== after.credit ? 'yes' : 'NO (BUG)');
  log('  mechanism still credited both ways',
    before.kicker.indexOf('Enzensberger') >= 0 && after.kicker.indexOf('Enzensberger') >= 0
      ? 'yes' : 'NO (BUG)');
  log('  verdict after        ', after.verdict.cls, '|', after.verdict.text.split('\n')[0].trim());
  log('  checked == on screen ', after.verdict.checked === after.shown);
  log('  press on new cart    ', pressed.verdict.cls, '| checked == on screen', pressed.verdict.checked === pressed.shown);
  log('  posted device        ', posted.map((p) => (p || '').match(/device=[^&]*/)).join(' '));
  log('  shown\n' + pressed.shown.split('\n').map((l) => '    ' + l).join('\n'));
}

// ── stale ──────────────────────────────────────────────────────────────────
async function runStale(browser) {
  const page = await open(browser);
  await page.route('**/stage/poesie_automat/act', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, DELAY));
    await route.continue();
  });
  await waitVerdict(page);
  // Ask for a read, then move a module inside its round trip and let go.
  await page.click('#automat-read');
  await page.waitForFunction(() => inert === true, { timeout: 10000 });
  const slot = 8;
  const box = await page.evaluate((slot) => {
    const r = document.getElementById('module-' + slot).getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, h: r.height };
  }, slot);
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  await page.mouse.move(box.x, box.y - box.h * 3);
  await page.mouse.up();
  // Sample across the window the response lands in.
  const samples = [];
  for (let i = 0; i < 60; i++) {
    samples.push(
      await page.evaluate(() => {
        const v = document.querySelector('#automat-reading .verdict');
        if (!v || v.classList.contains('turning')) return null;
        return { checked: v.dataset.checked, shown: readBoard() };
      })
    );
    await page.waitForTimeout(30);
  }
  const real = samples.filter((s) => s !== null);
  const wrong = real.filter((s) => s.checked !== s.shown);
  const after = await waitVerdict(page);
  log('stale, response delayed', DELAY + 'ms', REDUCED ? '(reduced motion)' : '');
  log('  samples with a real verdict          ', real.length + '/60');
  log('  ...standing over a board it is not about', wrong.length + '/' + real.length);
  log('  the owed read was paid                ', after.verdict.checked === after.shown);
  log('  ' + (wrong.length === 0 && after.verdict.checked === after.shown ? 'PASS' : 'FAIL'));
}

// ── wedge ──────────────────────────────────────────────────────────────────
async function runWedge(browser) {
  const kind = process.argv[3] || '500';
  const page = await open(browser);
  await waitVerdict(page);
  await page.route('**/stage/poesie_automat/act', async (route) => {
    if (kind === 'abort') await route.abort('failed');
    else await route.fulfill({ status: 500, body: 'no' });
  });
  await page.click('#automat-read');
  await page.waitForTimeout(700);
  const broken = await state(page);
  await page.unroute('**/stage/poesie_automat/act');
  // And now: can the scene still be driven at all?
  await page.click('#automat-press');
  const recovered = await waitVerdict(page);
  log('wedge (' + kind + ')', REDUCED ? '(reduced motion)' : '');
  log('  after the failure: inert', broken.inert, '| press disabled', broken.pressDisabled, '| verdict', broken.verdict.cls);
  log('  the press after it: verdict', recovered.verdict.cls, '| checked == on screen', recovered.verdict.checked === recovered.shown);
  log('  ' + (broken.inert === false && recovered.verdict.cls.indexOf('turning') < 0 ? 'PASS' : 'FAIL'));
}

// ── read ───────────────────────────────────────────────────────────────────
async function runRead(browser) {
  const page = await open(browser);
  const posted = [];
  page.on('request', (request) => {
    if (request.method() === 'POST') posted.push(request.postData());
  });
  const first = await state(page);
  await page.click('#automat-read');
  const after = await waitVerdict(page);
  log('read', REDUCED ? '(reduced motion)' : '');
  log('  on the wire          ', posted.join(' | ').slice(0, 200));
  log('  poem was not empty   ', posted.every((p) => (p || '').indexOf('poem=&') < 0 && (p || '').indexOf('poem=') >= 0));
  log('  verdict              ', after.verdict.cls, '|', after.verdict.text.split('\n')[0].trim());
  log('  checked == on screen ', after.verdict.checked === after.shown);
  log('  board did not move   ', first.shown === after.shown);
}

// ── contend ────────────────────────────────────────────────────────────────
async function runContend(browser) {
  const page = await open(browser);
  const posts = [];
  page.on('request', (request) => {
    if (request.method() === 'POST') posts.push(request.url());
  });
  await page.route('**/stage/poesie_automat/act', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, Number(process.env.DELAY || 900)));
    await route.continue();
  });
  await instrument(page);
  await page.click('#automat-press');
  await page.waitForFunction(() => inert === true, { timeout: 10000 });
  const box = await page.evaluate(() => {
    const r = document.getElementById('module-2').getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, h: r.height };
  });
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  const samples = [];
  for (let i = 0; i < 40; i++) {
    await page.mouse.move(box.x, box.y - box.h * ((i % 6) + 1));
    samples.push(await page.evaluate(() => ({ clattering: clattering, active: activeModules })));
    await page.waitForTimeout(40);
  }
  await page.mouse.up();
  const after = await waitVerdict(page);
  const contended = samples.filter((s) => s.clattering && s.active > 0);
  log('contend', REDUCED ? '(reduced motion)' : '');
  log('  samples clattering under a hand', contended.length + '/' + samples.length);
  log('  POSTs the gesture cost         ', posts.length);
  log('  verdict                        ', after.verdict.cls, '| checked == on screen', after.verdict.checked === after.shown);
  log('  ' + (contended.length === 0 ? 'PASS' : 'FAIL'));
}

// ── widths ─────────────────────────────────────────────────────────────────
async function runWidths(browser) {
  for (const device of ['poesieautomat_2000', 'poesieautomat_pokemon']) {
    const page = await open(browser, '&device=' + device);
    const measured = await page.evaluate(() => {
      const board = document.getElementById('flap-board');
      const stage = document.getElementById('stage');
      const line = document.querySelector('.board-line');
      const cell = document.querySelector('.cell');
      const rows = Array.from(document.querySelectorAll('.board-line')).map(
        (el) => el.querySelectorAll('.cell').length
      );
      let deepest = 0;
      let who = '';
      stage.querySelectorAll('*').forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return;
        if (r.bottom > deepest) {
          deepest = r.bottom;
          who = el.className || el.tagName;
        }
      });
      return {
        device: document.getElementById('automat-device').value,
        room: board.clientWidth,
        columns: Number(board.dataset.columns),
        cellWidth: Number(board.dataset.cellWidth),
        cellFont: Number(board.dataset.cellFont),
        cellBox: [cell.getBoundingClientRect().width, cell.getBoundingClientRect().height],
        lineWidth: line.getBoundingClientRect().width,
        cellsPerRow: rows,
        totalCells: document.querySelectorAll('.cell').length,
        fits: board.dataset.fits,
        boardHeight: board.getBoundingClientRect().height,
        extent: deepest - stage.getBoundingClientRect().top,
        deepest: who,
        longestRow: Math.max(...cells.map((row) => row.map((c) => c.char).join('').trim().length)),
      };
    });
    log('widths ' + measured.device);
    log('  room / columns       ', measured.room.toFixed(2) + 'px / ' + measured.columns);
    log('  one cell             ', measured.cellWidth + 'px wide, ' + measured.cellBox[1].toFixed(2) + 'px tall');
    log('  type in it           ', measured.cellFont + 'px  (data-fits=' + measured.fits + ')');
    log('  a row                ', measured.lineWidth.toFixed(2) + 'px, cells per row ' + JSON.stringify(measured.cellsPerRow) + ', total ' + measured.totalCells);
    log('  widest line spelled  ', measured.longestRow + ' columns');
    log('  board height         ', measured.boardHeight.toFixed(2) + 'px');
    log('  content extent       ', measured.extent.toFixed(2) + 'px against 720 (' + (720 - measured.extent).toFixed(2) + 'px blank), deepest: ' + measured.deepest);
    // The extent is cartridge-dependent — the two credits wrap to different
    // line counts — and it is deterministic to the hundredth of a pixel across
    // sessions and machines, unlike the clatter. It has already drifted once,
    // caught only by eye at 684.72px. 40px of blank is the house floor: the
    // tightest other scene, `cent_mille_milliards`, runs 679.28px / 40.72px.
    const blank = 720 - measured.extent;
    log('  blank >= 40px        ', blank.toFixed(2) + 'px', blank >= 40 ? 'PASS' : 'FAIL');
    await page.context().close();
  }
}

// ── frames ─────────────────────────────────────────────────────────────────
async function runFrames(browser) {
  for (const device of ['poesieautomat_2000', 'poesieautomat_pokemon']) {
    const short = device.split('_')[1];
    const page = await open(browser, '&device=' + device);
    await page.screenshot({ path: `${OUT}/automat-${short}-first-paint.png` });
    await instrument(page);
    await page.click('#automat-press');
    await page.waitForTimeout(400);
    // Where the wave front actually is at the moment of capture, so the frame
    // can be described from a reading rather than from the direction the code
    // implies. Playwright stalls the page for about a second while it
    // captures, so the image is a little later than this reading — but which
    // side is ahead does not change.
    const folding = await page.evaluate(() => {
      const row = document.querySelectorAll('.board-line')[0];
      const cs = Array.from(row.querySelectorAll('.cell'));
      const band = cs.map((c, i) => (c.classList.contains('folding') ? i : -1)).filter((i) => i >= 0);
      return {
        cells: document.querySelectorAll('.cell.folding').length,
        band: band.length ? [Math.min(...band), Math.max(...band)] : null,
      };
    });
    await page.screenshot({ path: `${OUT}/automat-${short}-mid-clatter.png`, animations: 'allow' });
    await waitRun(page);
    const after = await waitVerdict(page);
    await page.screenshot({ path: `${OUT}/automat-${short}-resolved.png` });
    log(
      short, 'frames written to', OUT,
      '| cells folding at capture:', folding.cells,
      '| row 1 folding band, columns:', JSON.stringify(folding.band)
    );
    log('  ' + after.verdict.text.split('\n')[0].trim());
    log(after.shown.split('\n').map((l) => '    ' + l).join('\n'));
    await page.context().close();
  }
}

const MODES = {
  drag: runDrag,
  press: runPress,
  wave: runWave,
  roll: runRoll,
  reverse: runReverse,
  swap: runSwap,
  stale: runStale,
  wedge: runWedge,
  read: runRead,
  contend: runContend,
  widths: runWidths,
  frames: runFrames,
};

const browser = await chromium.launch();
try {
  const run = MODES[mode];
  if (!run) {
    log('unknown mode', mode, '- one of', Object.keys(MODES).join(', '));
  } else {
    await run(browser);
  }
} finally {
  await browser.close();
}
