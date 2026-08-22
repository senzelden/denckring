# Browser reproductions — scene seven's hold-to-turn

Six Playwright scripts. They are **not** run by `pytest`, or by anything else
automatically: each one drives a real browser against a running server, and
several of them deliberately take seconds per run. They live here because
they are the only real coverage of this interaction — `pytest` drives
Starlette's `TestClient`, which runs no JavaScript, so the races these
reproduce are out of its reach entirely, and the tests in `test_stage.py` that
name them can only guard the *source* of the fixes. A race has been found in
this code three times; the harness that reproduced it should outlive the task.

## Running them

Playwright here is Node's (v1.62.1 when these were written); the Python
package is not installed, and this repo has no `package.json`. An ES module
resolves its imports from its own directory upwards, so Playwright has to sit
in a `node_modules` above these files — `apps/explorer/node_modules` is the
nearest place that is not the repo root:

```console
npm install --prefix apps/explorer playwright   # untracked, and NOT gitignored — delete it after
npx playwright install chromium                 # browsers cache in ~/.cache/ms-playwright

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
| `hold-announcements.mjs` | What the status line says and how often across a hold and the read that follows, against the panel's own mutation count. |
