# Browser reproductions — the volvelles' turning, the blades, and the flaps

Nine Playwright scripts. They are **not** run by `pytest`, or by anything else
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
`flap-board.mjs` drives scene eight (`/stage/poesie_automat`), whose 36 drums
are turned in the browser both by the machine and by hand, and whose verdict is
a check of the poem read cell by cell out of them.

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
| `flap-board.mjs` | Scene eight's flap-board. `drag` samples a drum's position *while the pointer is still down* — the requirement is that it turns under the hand, so a run that only checked where it landed would prove nothing — and reports the flaps it walked through, whether the drum ever showed a flap other than the one in its window, and whether a real verdict was on screen under the hand. `press` clocks the whole clatter inside the page and compares the poem the drums are showing with the `data-checked` the verdict came back carrying. `stale` turns a drum *during* the read's round trip (`DELAY`, default 600ms) and counts real verdicts standing over a board they were not about — with the token comparison removed this reports 11/60 and with it 0/60, and with the owed read dropped the scene never recovers a verdict at all. `wedge` stubs the route with a 500, and separately with an aborted request; without the two-line handler both leave `inert` true and both buttons dead for the rest of the session. `widths` is the measurement the whole layout turns on: every drum's rendered width, each line's total, and what a literal board would need instead. `frames` writes first paint, a frame mid-clatter and the resolved board to `OUT`, and reports the clocked clatter and the scene's own content extent. `REDUCED=1` runs under `reducedMotion: 'reduce'`, where every drum must arrive at once and the drag must still work. |
| `cut-blade.mjs` | Scene six's blades and its cut. `drag` samples a blade's position *while the pointer is still down* — the requirement is that it moves under the hand, so a run that only checked where it landed would prove nothing. `clean` positions the vertical blade in a column the page itself says misses every word, cuts, and compares the text the quarters are showing with the `data-checked` the verdict came back carrying. `through` puts it inside words instead and reads the named fragments back. `stale` moves a blade *during* the check's round trip (`DELAY`, default 600ms) and counts real verdicts left standing over a page that has changed since — the invariant this codebase has had broken four times. `wedge` stubs the route with a 500, and separately with an aborted request, and reads back whether the scene can still be driven at all — htmx does not swap on a non-2xx, so the flag the submit gate reads has no other path back to false; that is a liveness failure and the placeholder machinery cannot see it. `frames` writes first paint, a frame mid-cut and the cut page to `OUT`, and reports the cut's clocked length and the scene's own content extent. `REDUCED=1` runs under `reducedMotion: 'reduce'`, where the quarters must land at once and the blades must still drag. |
