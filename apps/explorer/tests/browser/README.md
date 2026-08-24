# Browser reproductions — the volvelles' turning, the blades, and the flaps

Ten Playwright scripts. They are **not** run by `pytest`, or by anything else
automatically: each one drives a real browser against a running server, and
several of them deliberately take seconds per run. They live here because
they are the only real coverage of this interaction — `pytest` drives
Starlette's `TestClient`, which runs no JavaScript, so the races these
reproduce are out of its reach entirely, and the tests in `test_stage.py` that
name them can only guard the *source* of the fixes. A race has been found in
this code three times; the harness that reproduced it should outlive the task.

Six of them drive scene seven (`/stage/llull_figure`); `drag-turn.mjs` drives
either volvelle, because scene one (`/stage/denckring`) adopted the same
interaction in the drag round and its five windowed rings of differing sizes
are the case the shared module was written scene-agnostic for. `cut-blade.mjs`
drives scene six (`/stage/cut_up`), whose whole cut happens in the browser —
two blades, four quarters, and a verdict on text read back out of them.
`flap-board.mjs` drives scene eight (`/stage/poesie_automat`), which is a
letter board: 426 character cells turned in the browser by the machine, by
hand, and by a cartridge swap, with the verdict a check of the poem read
character by character out of them. `cut-methods.mjs` drives the same scene
six as `cut-blade.mjs` but across all four of its operations, three of which
are checked by a different procedure than the scene's own.

Its `wave` mode carries a load none of the others does. The board has to
resolve as a wave rather than in unison, and that cannot be pinned in Python:
the guard that used to try asserted `const STAGGER_MS = \d+`, and `\d+` matches
`0`, so a board resolving in unison passed its own test with every other guard
green.

What `wave` measures took two attempts. The obvious number is the **span**
between the first cell folding and the last — and it does not work: with
`STAGGER_MS` set to 0 the span still measured 2618-3038ms and the mode said
PASS, because on a board of 426 cells the main thread spreads the folds out
whether or not anything asked it to. So it measures *where* the folding cells
are instead: the **band** of columns folding at one moment (11-25 as shipped,
58-66 at zero, ceiling 35) and how far the **front** of that band advances
across the clatter (35.2-54.0 columns as shipped, 2.2-15.4 at zero, floor 20),
plus the dwell between two folds of one cell, which is what says a cell folds
more than once on its way. Set `STAGGER_MS` to 0 and the mode says FAIL — run
at zero to check that it does, not assumed.

Those figures are one run of `wave 12` and one control run at zero, from a
single session on one build, and the scene's own comments and the task report
quote the same run. The spread between sessions on this machine is wide enough
that quoting three separately-measured sets as if they were fixed would be
three different answers to one question.

## Running them

Playwright here is Node's (v1.62.1, pinned); the Python package is not
installed. An ES module resolves its imports from its own directory upwards,
so Playwright has to sit in a `node_modules` above these files —
`apps/explorer` carries the manifest and lockfile for exactly that, and the
tree itself is gitignored:

```console
npm ci --prefix apps/explorer     # installs the pinned playwright 1.62.1
npx playwright install chromium   # browsers cache in ~/.cache/ms-playwright

uv run --project apps/explorer explorer --port 8477
BASE=http://127.0.0.1:8477 node apps/explorer/tests/browser/hold-race.mjs stress 25
```

`BASE` defaults to `http://127.0.0.1:8477`. Confirm the port serves the build
you mean to measure — a stale `uvicorn` has silently served old code to this
project's screenshots before.

Race verification belongs under **normal** motion. Reduced motion makes every
step land synchronously, so the timing gap these exploit never exists, and a
clean run there proves nothing.

## What each one reproduces

| script | what it measures |
|---|---|
| `hold-race.mjs` | The drain race: a tap on one wheel, then a press on another inside the drain's own window. `scripted` runs the deterministic case, `stress N` randomises tap/gap/hold and which wheels. Counts a real verdict shown under a still-held button, and the strict subset where that verdict contradicts the chamber beside it. `REDUCED=1` runs it under `reducedMotion: 'reduce'`. |
| `hold-catch-up-verdict.mjs` | The catch-up replay's own instance of the same defect: press *inside* a delayed response and release before it lands, so the deferred steps replay after a real verdict is already on screen. Takes a delay in ms. Oracle reads the page's own `currentLetters()`, not the printed chamber. |
| `hold-slow-link.mjs` | Whether a hold spanning a slow round trip loses its steps: compares the ticks the held button produced with the letters the wheel actually moved. |
| `hold-blur-release.mjs` | The `blur` → `stop` release path for a *mouse* hold: steps before blurring the active element, and steps after. |
| `hold-two-finger.mjs` | Two simultaneous touch holds on two wheels (CDP touch events on a `hasTouch` context), with the `pointerdown`/`focus`/`blur` trace. Pins that focusing a button never ends another finger's hold. |
| `drag-turn.mjs` | Drag-to-turn on either scene: `sweep`/`back` turn one ring 90 degrees each way, sampling the dial's own transform and the panel beside it every 4 degrees *while the pointer is still down* — the requirement is that the ring moves under the finger, so a run that only checks where it landed proves nothing. `wrap` crosses the ring's own seam both ways; `contend` puts a second finger on that ring's step button mid-grab (the grab is meant to win); `two-finger` drags two rings at once with CDP touch; `regrab` grabs again while the previous release's read is still in flight (`DELAY`, default 600ms) and counts samples where the panel disagreed with the rings' own indices; and `release-inside` *lets go* inside that same window, which is the case `regrab` cannot see — with no hand down when the swap lands, nothing re-arms the panel, so the only thing that can save it is the read the drag owes. Takes `[scene] [mode] [ring]`; `REDUCED=1` runs under `reducedMotion: 'reduce'`, where the drag must still work and the snap lands at once. |
| `hold-announcements.mjs` | What the status line says and how often across a hold and the read that follows, against the panel's own mutation count. |
| `flap-board.mjs` | Scene eight's letter board, in twelve modes. `drag` samples a module's flaps *while the pointer is still down* — the requirement is that it turns under the hand — and reports whether the handle stayed over the cells its flap spells and whether a real verdict was ever on screen under the hand. `press` clocks the whole clatter inside the page and compares the poem the cells are showing with the `data-checked` the verdict came back carrying. `wave` is the measured floor described above — band, front advance and dwell. `reverse` turns a module and turns it back inside `FOLD_MS` — once, then three and four times in a row — by drag and by keyboard at dwells of 10/20/40ms, 18 runs in all, and builds its oracle from the glyphs the cells are actually rendering rather than from the page's own `cell.char`, because the defect it exists for is those two disagreeing and a board left spelling a character no flap carries. Reverting the `drawBoard` gate takes it to 7/18 FAIL — and *which* 7 is worth knowing: the single reversal fails 5 of 6, three reversals only 2 of 6, and four reversals none at all, because each extra turn gives the stranded cell another chance to be re-targeted and heal. Oscillation is the weaker probe, not the stronger one. `roll` checks that a cell travelling between two characters turns through every character in between, and reports how many journeys the cap shortened. `swap` drives the cartridge switcher: the flaps change, the 426 cells do not move, the alphabet becomes the incoming board's own, and the verdict's own history is read back to show the placeholder went up before any new verdict — sampled state cannot see that under reduced motion, where the whole swap takes about ten milliseconds. `stale` turns a module *during* the read's round trip (`DELAY`, default 600ms) and counts real verdicts standing over a board they were not about. `wedge` stubs the route with a 500, and separately with an aborted request; without the two-line handler both leave `inert` true and every control dead for the rest of the session. `read` clicks the plain "Read the board" button from first paint and reads back what went on the wire — it used to post an empty poem. `contend` begins a grab *during* an in-flight press and counts samples with the board clattering under a hand. `widths` is the measurement the layout turns on: 71 cells in the width the stage leaves, the cell and type sizes that come out of it, `data-fits`, and the scene's content extent against the 720px budget. `frames` writes first paint, a frame mid-clatter and the resolved board, for both cartridges, to `OUT`. `REDUCED=1` runs under `reducedMotion: 'reduce'`, where every cell must arrive at once and the drag must still work. |
| `cut-blade.mjs` | Scene six's blades and its cut. `drag` samples a blade's position *while the pointer is still down* — the requirement is that it moves under the hand, so a run that only checked where it landed would prove nothing. `clean` positions the vertical blade in a column the page itself says misses every word, cuts, and compares the text the quarters are showing with the `data-checked` the verdict came back carrying. `through` puts it inside words instead and reads the named fragments back. `stale` moves a blade *during* the check's round trip (`DELAY`, default 600ms) and counts real verdicts left standing over a page that has changed since — the invariant this codebase has had broken four times. `wedge` stubs the route with a 500, and separately with an aborted request, and reads back whether the scene can still be driven at all — htmx does not swap on a non-2xx, so the flag the submit gate reads has no other path back to false; that is a liveness failure and the placeholder machinery cannot see it. `frames` writes first paint, a frame mid-cut and the cut page to `OUT`, and reports the cut's clocked length and the scene's own content extent. `REDUCED=1` runs under `reducedMotion: 'reduce'`, where the quarters must land at once and the blades must still drag. |
| `cut-methods.mjs` | Scene six's four operations, each against its own checker. The picker turned one scene into four, and three of them are client-side arrangements checked by a *different* procedure — `fold_in`, nothing at all, `column_reading`. `run` performs all four in order and reads each verdict back; the word bag must come back with no verdict element of any class, because `dada_poem` is catalogued uncheckable. `reduced` is the same under `prefers-reduced-motion`, which kills every transition with `!important` and is where a choreography that waits on `transitionend` deadlocks. `switch` starts an operation and picks another mid-animation: no verdict may be left standing and the page must be whole again. |
