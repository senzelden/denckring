# The Stage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the explorer a board that shows every procedure's golden cases at a glance, and five recordable scenes that show what five of the procedures actually are.

**Architecture:** New routes in the existing FastAPI explorer, under `/board` and `/stage/*`. A second base template (`stage.html`) gives scenes a full-bleed, chrome-free frame at a fixed recording size; each scene is its own template and its own route with its own CSS block. Every scene calls the library live through htmx, exactly as the bench already does. No scene abstraction is invented up front — extract one only if a later scene proves it needs what an earlier one built.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, htmx (vendored), CSS, SVG. No JavaScript framework and no build step.

**Spec:** `docs/superpowers/specs/2026-08-19-showcase-design.md`

## Global Constraints

- Everything lives in `apps/explorer`, which is `Private :: Do Not Upload`. Nothing here may be imported by `src/denckring` or by either data package.
- **No new library capability.** Scenes drive `check`, `apply` and existing pack methods through the public API. If a scene seems to need core to change, stop and report it — that is a scene claiming something the library cannot do.
- **No build step, no npm, no JS framework.** htmx is already vendored at `src/explorer/static/htmx.min.js`.
- **Live calls only.** No scene renders a stored result. A recorded mockup is a lie about the software.
- Line length 100, `ruff format` clean, `mypy --strict` clean. Run from the app: `uv run --project apps/explorer ruff check`, `uv run --project apps/explorer mypy --strict src tests`, `uv run --project apps/explorer pytest -q`.
- Templates extend `base.html` (bench pages) or `stage.html` (board and scenes). Render through the existing `page(request, name, **context)` helper in `app.py`.
- Corpora are never committed and never copied (ADR 0020). They are read from `DENCKRING_CORPORA` through `explorer.corpora`.
- The repository suite must stay green too: `uv run pytest -q` at the root, unchanged at 3395 passed.

---

## File Structure

**Created:**
- `apps/explorer/src/explorer/board.py` — turns `harness.run()` into tiles. No rendering.
- `apps/explorer/src/explorer/stage.py` — per-scene data preparation. One function per scene, each returning a frozen dataclass the template renders. No rendering, no HTTP.
- `apps/explorer/src/explorer/templates/stage.html` — the second base template.
- `apps/explorer/src/explorer/templates/board.html`, `stage_index.html`, and one `stage_<scene>.html` per scene, plus the fragments each scene posts back.
- `apps/explorer/src/explorer/static/stage.css` — stage-only styling, on the tokens `explorer.css` already defines.
- `apps/explorer/tests/test_board.py`, `apps/explorer/tests/test_stage.py`.

**Modified:**
- `apps/explorer/src/explorer/app.py` — routes only.
- `apps/explorer/src/explorer/templates/base.html` — one nav link to the board.
- `.github/workflows/ci.yml` — an explorer job (Task 8).

---

### Task 1: The board

**Files:**
- Create: `apps/explorer/src/explorer/board.py`
- Create: `apps/explorer/src/explorer/templates/board.html`
- Modify: `apps/explorer/src/explorer/app.py`
- Modify: `apps/explorer/src/explorer/templates/base.html`
- Test: `apps/explorer/tests/test_board.py`

**Interfaces:**
- Consumes: `denckring.eval.harness.run() -> Scoreboard` with `.results: list[CaseResult]` (fields `case`, `procedure`, `lang`, `passed`, `detail`) and `.coverage: Coverage`; `harness.status() -> Coverage` whose `__str__` is the scoreboard line; `denckring.core.catalogue.ids()`; `denckring.core.registry.all_procedures()`.
- Produces: `board.tiles() -> list[Tile]` and the `Tile` dataclass, used by nothing else in this plan but by the board template.

- [ ] **Step 1: Write the failing test**

Create `apps/explorer/tests/test_board.py`:

```python
"""The board is `denckring eval` with a body. These guard what it claims."""

from __future__ import annotations

from explorer import board
from explorer.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_every_catalogued_procedure_gets_a_tile() -> None:
    from denckring.core import catalogue

    assert {tile.id for tile in board.tiles()} == set(catalogue.ids())


def test_an_implemented_procedure_with_passing_cases_is_green() -> None:
    tiles = {tile.id: tile for tile in board.tiles()}
    assert tiles["lipogram"].state == "green"
    assert tiles["lipogram"].cases > 0
    assert tiles["lipogram"].detail == ""


def test_a_catalogued_but_unimplemented_procedure_is_grey() -> None:
    """`homosyntaxism` is blocked on a `pos` capability no pack provides. It is not a
    failure, and a board that showed it red would cry wolf 35 times."""
    tiles = {tile.id: tile for tile in board.tiles()}
    assert tiles["homosyntaxism"].state == "grey"
    assert tiles["homosyntaxism"].cases == 0


def test_the_board_renders_with_the_scoreboard_line() -> None:
    response = client.get("/board")
    assert response.status_code == 200
    assert "152 catalogued" in response.text
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run --project apps/explorer pytest tests/test_board.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'explorer.board'`.

- [ ] **Step 3: Write the module**

Create `apps/explorer/src/explorer/board.py`:

```python
"""Every procedure as one tile, coloured by its own golden cases.

`denckring eval` prints 344 lines and a scoreboard, which is the right shape for CI
and the wrong shape for a person looking for the one row that is unhappy. Same data,
laid out so it can be scanned.
"""

from __future__ import annotations

from dataclasses import dataclass

from denckring.core import catalogue
from denckring.core.registry import all_procedures
from denckring.eval import harness


@dataclass(frozen=True)
class Tile:
    """One procedure on the board."""

    id: str
    name: str
    family: str
    #: `green` — every golden case passes. `red` — at least one does not.
    #: `grey` — catalogued but not implemented, which is a gap and not a failure.
    state: str
    cases: int
    #: The first failing case, named, or empty when there is nothing to say.
    detail: str


def tiles() -> list[Tile]:
    """Every catalogued procedure, with its golden cases run."""
    scoreboard = harness.run()
    implemented = set(all_procedures())
    by_procedure: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    for result in scoreboard.results:
        counts[result.procedure] = counts.get(result.procedure, 0) + 1
        if not result.passed:
            by_procedure.setdefault(result.procedure, []).append(
                f"{result.case}: {result.detail or 'did not match'}"
            )

    out: list[Tile] = []
    for procedure_id in catalogue.ids():
        meta = catalogue.get(procedure_id)
        failures = by_procedure.get(procedure_id, [])
        if procedure_id not in implemented:
            state = "grey"
        else:
            state = "red" if failures else "green"
        out.append(
            Tile(
                id=procedure_id,
                name=meta.names.get("en", procedure_id),
                family=meta.family,
                state=state,
                cases=counts.get(procedure_id, 0),
                detail=failures[0] if failures else "",
            )
        )
    return out


def scoreboard_line() -> str:
    """The line `denckring status` prints, for the board to carry unchanged."""
    return str(harness.status())
```

- [ ] **Step 4: Add the route and the template**

In `apps/explorer/src/explorer/app.py`, add `board` to the `from explorer import ...` line and append this route after `missing`:

```python
@app.get("/board", response_class=HTMLResponse)
def the_board(request: Request) -> HTMLResponse:
    """Every procedure's golden cases, run now and laid out to be scanned."""
    return page(
        request,
        "board.html",
        page_id="board",
        tiles=board.tiles(),
        scoreboard=board.scoreboard_line(),
    )
```

Create `apps/explorer/src/explorer/templates/board.html`:

```html
{% extends "stage.html" %}
{% block title %}The board — denckring{% endblock %}
{% block main %}
<h1>The board</h1>
<p class="scoreboard">{{ scoreboard }}</p>
<ul class="board">
  {% for tile in tiles %}
  <li class="tile {{ tile.state }}">
    <a href="/p/{{ tile.id }}">
      <span class="tile-id">{{ tile.id }}</span>
      <span class="tile-cases">{{ tile.cases }}</span>
    </a>
    {% if tile.detail %}<p class="tile-detail">{{ tile.detail }}</p>{% endif %}
  </li>
  {% endfor %}
</ul>
{% endblock %}
```

**Note:** `board.html` extends `stage.html`, which Task 2 creates. Do Task 2 first if you are executing out of order; otherwise the template will fail to render and the last test in Step 1 will stay red until Task 2 lands. If you prefer a self-contained Task 1, extend `base.html` here and switch it in Task 2.

In `base.html`, add to the `<nav>`:

```html
    <a href="/board" {% if page_id == 'board' %}aria-current="page"{% endif %}>The board</a>
```

- [ ] **Step 5: Run the tests**

```bash
uv run --project apps/explorer pytest tests/test_board.py -q
```

Expected: PASS, all four.

- [ ] **Step 6: Commit**

```bash
git add apps/explorer/src/explorer/board.py apps/explorer/src/explorer/templates/board.html \
        apps/explorer/src/explorer/app.py apps/explorer/src/explorer/templates/base.html \
        apps/explorer/tests/test_board.py
git commit -m "feat(explorer): the board, every procedure's golden cases at a glance"
```

---

### Task 2: The stage shell

**Files:**
- Create: `apps/explorer/src/explorer/templates/stage.html`
- Create: `apps/explorer/src/explorer/templates/stage_index.html`
- Create: `apps/explorer/src/explorer/static/stage.css`
- Create: `apps/explorer/src/explorer/stage.py`
- Modify: `apps/explorer/src/explorer/app.py`
- Test: `apps/explorer/tests/test_stage.py`

**Interfaces:**
- Produces: `stage.SCENES: list[Scene]` and the `Scene` dataclass (`slug`, `title`, `procedure_id`, `caption`), consumed by the index route and by every later task's route registration.

- [ ] **Step 1: Write the failing test**

Create `apps/explorer/tests/test_stage.py`:

```python
"""The stage. Appearance is not tested; the claims underneath it are."""

from __future__ import annotations

from explorer import stage
from explorer.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_the_index_lists_every_scene() -> None:
    response = client.get("/stage")
    assert response.status_code == 200
    for scene in stage.SCENES:
        assert scene.title in response.text


def test_every_scene_names_a_real_procedure() -> None:
    """A scene dramatising a procedure that is not registered would be a scene making
    a claim the library cannot back."""
    from denckring.core.registry import all_procedures

    registered = set(all_procedures())
    assert {scene.procedure_id for scene in stage.SCENES} <= registered


def test_chrome_off_removes_the_caption() -> None:
    """Recording wants the stage and nothing else."""
    with_chrome = client.get("/stage")
    without = client.get("/stage?chrome=off")
    assert "stage-caption" in with_chrome.text
    assert "stage-caption" not in without.text
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run --project apps/explorer pytest tests/test_stage.py -q
```

Expected: FAIL — no module `explorer.stage`.

- [ ] **Step 3: Write the scene registry**

Create `apps/explorer/src/explorer/stage.py`:

```python
"""The stage: what each scene is, and the data it needs.

Preparation only. Nothing here renders, and nothing here touches HTTP — a scene's
route reads from this module and hands the result to a template, so the thing a
scene claims can be tested without a browser.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scene:
    """One recordable scene."""

    slug: str
    title: str
    procedure_id: str
    #: One line, shown under the stage and hidden by `?chrome=off`.
    caption: str


SCENES: list[Scene] = [
    Scene(
        slug="denckring",
        title="Der Denckring",
        procedure_id="denckring",
        caption="Harsdörffer, Nürnberg 1651. Turn the rings; read inward to outward.",
    ),
    Scene(
        slug="ideenwuerfeln",
        title="Ideenwürfeln",
        procedure_id="ideenwuerfeln",
        caption="Jean Paul's excerpt books: distant material forced together under one word.",
    ),
    Scene(
        slug="arca",
        title="Arca musarithmica",
        procedure_id="arca_musarithmica",
        caption="Kircher, 1650. The phrase is measured; the tablet for that length answers.",
    ),
    Scene(
        slug="n_plus_7",
        title="N+7",
        procedure_id="n_plus_7",
        caption="Lescure, 1961. Every noun, seven entries further down the dictionary.",
    ),
    Scene(
        slug="ghazal",
        title="Ghazal",
        procedure_id="ghazal",
        caption="Persian and Urdu: every couplet closes on the same word, rhyming before it.",
    ),
]


def scene(slug: str) -> Scene:
    """One scene by slug, or `KeyError`."""
    for candidate in SCENES:
        if candidate.slug == slug:
            return candidate
    raise KeyError(slug)
```

- [ ] **Step 4: Write the shell template**

Create `apps/explorer/src/explorer/templates/stage.html`:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}denckring{% endblock %}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=Instrument+Sans:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/explorer.css">
<link rel="stylesheet" href="/static/stage.css">
<script src="/static/htmx.min.js" defer></script>
</head>
<body class="stage-body{% if chrome_off %} bare{% endif %}">
<main class="stage" id="stage">
{% block main %}{% endblock %}
</main>
{% if not chrome_off %}
<p class="stage-caption">{% block caption %}{% endblock %}</p>
{% endif %}
</body>
</html>
```

Create `apps/explorer/src/explorer/templates/stage_index.html`:

```html
{% extends "stage.html" %}
{% block title %}The stage — denckring{% endblock %}
{% block main %}
<h1>The stage</h1>
<ol class="scene-list">
  {% for scene in scenes %}
  <li><a href="/stage/{{ scene.slug }}">{{ scene.title }}</a> <span>{{ scene.caption }}</span></li>
  {% endfor %}
</ol>
{% endblock %}
{% block caption %}Five procedures, driven by hand.{% endblock %}
```

- [ ] **Step 5: Write the stylesheet**

Create `apps/explorer/src/explorer/static/stage.css`. It uses the tokens `explorer.css` already defines (`--case`, `--paper`, `--ink`, `--rubric`, `--lead`), and fixes the stage at recording size:

```css
/* The stage: scenes recorded as short loops.
 *
 * One fixed size, because every recording should crop identically. The bench's
 * type-case palette carries over; a scene is a proof pulled on the same press.
 */

.stage-body {
  margin: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--case-deep);
}

.stage {
  width: 1280px;
  height: 720px;
  background: var(--paper);
  color: var(--ink);
  padding: 3rem;
  box-sizing: border-box;
  overflow: hidden;
  position: relative;
}

.stage-caption {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.8rem;
  color: var(--lead);
  margin: 1rem 0 0;
  max-width: 1280px;
}

.stage-body.bare .stage { box-shadow: none; }

.board { display: grid; grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr)); gap: 0.4rem; list-style: none; padding: 0; }
.tile { border-left: 3px solid var(--lead); padding: 0.3rem 0.5rem; background: var(--paper-shade); }
.tile.green { border-left-color: #3f7d3f; }
.tile.red { border-left-color: var(--rubric); }
.tile.grey { opacity: 0.55; }
.tile-detail { font-size: 0.7rem; color: var(--rubric); margin: 0.2rem 0 0; }
```

**Note:** the board is taller than 720px. Give `board.html` a `stage-tall` class on the main element, and in `stage.css` add `.stage.stage-tall { height: auto; min-height: 720px; }`. The fixed height is for scenes, which are recorded; the board is not.

- [ ] **Step 6: Add the routes**

In `app.py`, import `stage` and add:

```python
@app.get("/stage", response_class=HTMLResponse)
def the_stage(request: Request, chrome: str = "on") -> HTMLResponse:
    return page(request, "stage_index.html", scenes=stage.SCENES, chrome_off=chrome == "off")
```

- [ ] **Step 7: Run the tests and commit**

```bash
uv run --project apps/explorer pytest tests/test_stage.py tests/test_board.py -q
uv run --project apps/explorer ruff check && uv run --project apps/explorer mypy --strict src tests
git add apps/explorer/src/explorer/stage.py apps/explorer/src/explorer/static/stage.css \
        apps/explorer/src/explorer/templates/stage.html \
        apps/explorer/src/explorer/templates/stage_index.html apps/explorer/src/explorer/app.py \
        apps/explorer/tests/test_stage.py
git commit -m "feat(explorer): the stage shell, at recording size"
```

---

### Task 3: Scene 1 — Der Denckring

**Files:**
- Modify: `apps/explorer/src/explorer/stage.py`
- Create: `apps/explorer/src/explorer/templates/stage_denckring.html`
- Create: `apps/explorer/src/explorer/templates/_stage_word.html`
- Modify: `apps/explorer/src/explorer/app.py`, `apps/explorer/src/explorer/static/stage.css`
- Test: `apps/explorer/tests/test_stage.py`

**Interfaces:**
- Consumes: `denckring.core.device.load(device_id) -> Device` with `.slots: list[Slot]` (`name`, `alternatives`, `optional`) and `.combinations: int`; `denckring.check("denckring", word)`; `get("denckring").apply("", lang="en")`.
- Produces: `stage.rings() -> Rings` — `Rings(slots: list[RingSlot], combinations: int, claimed: int)` where `RingSlot(name: str, alternatives: list[str])`.

- [ ] **Step 1: Write the failing test**

Append to `apps/explorer/tests/test_stage.py`:

```python
def test_the_rings_carry_the_transcribed_counts() -> None:
    """Cramer's transcription has 49/60/12/120/23, where Harsdörffer's own text
    announces 48/50/12/120/24. The scene shows what the data has, not what the book
    claims — the catalogue row records both and adjusts neither."""
    rings = stage.rings()
    assert [len(slot.alternatives) for slot in rings.slots] == [49, 60, 12, 120, 23]


def test_the_scene_shows_the_true_count_beside_the_famous_one() -> None:
    rings = stage.rings()
    assert rings.claimed == 97_209_600
    assert rings.combinations != rings.claimed


def test_a_word_turned_from_the_rings_satisfies_the_procedure() -> None:
    """The scene's claim: what comes off these rings is a denckring word."""
    from denckring import check
    from denckring.core.registry import get

    word = get("denckring").apply("", lang="en")
    assert check("denckring", word).satisfied is True


def test_the_denckring_scene_renders() -> None:
    response = client.get("/stage/denckring")
    assert response.status_code == 200
    assert "ring-0" in response.text
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run --project apps/explorer pytest tests/test_stage.py -q
```

Expected: FAIL — `AttributeError: module 'explorer.stage' has no attribute 'rings'`.

- [ ] **Step 3: Implement the scene data**

Append to `apps/explorer/src/explorer/stage.py`:

```python
from denckring.core import device

#: The figure the literature repeats for the Denckring. It is not a product of rings of
#: 12 and 120 at all — the catalogue row carries the arithmetic. The scene puts it next
#: to the real number rather than arguing in prose.
CLAIMED_COMBINATIONS = 97_209_600


@dataclass(frozen=True)
class RingSlot:
    """One disc, with everything written on it."""

    name: str
    alternatives: list[str]
    optional: bool


@dataclass(frozen=True)
class Rings:
    """The five discs, and the two counts."""

    slots: list[RingSlot]
    combinations: int
    claimed: int


def rings() -> Rings:
    """Harsdörffer's device as the shipped transcription has it."""
    loaded = device.load("harsdoerffer_1651")
    return Rings(
        slots=[
            RingSlot(name=slot.name, alternatives=list(slot.alternatives), optional=slot.optional)
            for slot in loaded.slots
        ],
        combinations=loaded.combinations,
        claimed=CLAIMED_COMBINATIONS,
    )
```

- [ ] **Step 4: Add the route and the fragment endpoint**

In `app.py`:

```python
@app.get("/stage/denckring", response_class=HTMLResponse)
def stage_denckring(request: Request, chrome: str = "on") -> HTMLResponse:
    return page(
        request,
        "stage_denckring.html",
        scene=stage.scene("denckring"),
        rings=stage.rings(),
        chrome_off=chrome == "off",
    )


@app.post("/stage/denckring/act", response_class=HTMLResponse)
async def stage_denckring_act(request: Request) -> HTMLResponse:
    """Check the word the rings currently spell, or turn them to a new one."""
    form = dict(await request.form())
    word = str(form.get("word", ""))
    if form.get("turn"):
        word = get("denckring").apply("", lang="en")
    report = check("denckring", word) if word else None
    return page(request, "_stage_word.html", word=word, report=report)
```

Add to `app.py`'s imports:

```python
from denckring import __version__, check
from denckring.core.registry import all_procedures, get
```

- [ ] **Step 5: Write the templates**

Create `apps/explorer/src/explorer/templates/stage_denckring.html`. Each ring is an SVG group of text elements on a circle; a click on a ring rotates it by one step through a CSS custom property set by the inline handler, and the assembled word posts to `/stage/denckring/act`:

```html
{% extends "stage.html" %}
{% block title %}Der Denckring{% endblock %}
{% block main %}
<h1>{{ scene.title }}</h1>
<div class="rings">
  {% for slot in rings.slots %}
  <div class="ring" id="ring-{{ loop.index0 }}" data-parts="{{ slot.alternatives | join('|') }}">
    <span class="ring-name">{{ slot.name }}</span>
    <button class="ring-turn" type="button"
            onclick="turn({{ loop.index0 }}, 1)">{{ slot.alternatives[0] }}</button>
  </div>
  {% endfor %}
</div>
<form hx-post="/stage/denckring/act" hx-target="#word" hx-trigger="submit">
  <input type="hidden" name="word" id="word-field">
  <button type="submit">Read it</button>
  <button type="submit" name="turn" value="1">Turn them for me</button>
</form>
<div id="word"></div>
<p class="counts">
  {{ "{:,}".format(rings.combinations) }} readings on these discs —
  <s>{{ "{:,}".format(rings.claimed) }}</s> is the figure the literature repeats.
</p>
{% endblock %}
{% block caption %}{{ scene.caption }}{% endblock %}
<script>
const at = {};
function turn(ring, step) {
  const el = document.getElementById('ring-' + ring);
  const parts = el.dataset.parts.split('|');
  at[ring] = ((at[ring] || 0) + step + parts.length) % parts.length;
  el.querySelector('.ring-turn').textContent = parts[at[ring]];
  document.getElementById('word-field').value =
    [0, 1, 2, 3, 4].map(i => {
      const e = document.getElementById('ring-' + i);
      return e ? e.querySelector('.ring-turn').textContent : '';
    }).join('');
}
</script>
```

Create `apps/explorer/src/explorer/templates/_stage_word.html`:

```html
<p class="word">{{ word }}</p>
{% if report %}
<p class="verdict {{ 'yes' if report.satisfied else 'no' }}">
  {{ "off the rings" if report.satisfied else "not a reading of these rings" }}
</p>
{% endif %}
```

- [ ] **Step 6: Run the tests**

```bash
uv run --project apps/explorer pytest tests/test_stage.py -q
```

Expected: PASS, all seven.

- [ ] **Step 7: Commit**

```bash
git add apps/explorer/src/explorer/stage.py apps/explorer/src/explorer/app.py \
        apps/explorer/src/explorer/templates/stage_denckring.html \
        apps/explorer/src/explorer/templates/_stage_word.html \
        apps/explorer/src/explorer/static/stage.css apps/explorer/tests/test_stage.py
git commit -m "feat(explorer): scene one, the rings turning"
```

---

### Task 4: Scene 2 — Ideenwürfeln, in two registers

**Files:**
- Modify: `apps/explorer/src/explorer/stage.py`, `app.py`, `static/stage.css`
- Create: `apps/explorer/src/explorer/templates/stage_ideenwuerfeln.html`, `_stage_throw.html`
- Test: `apps/explorer/tests/test_stage.py`

**Interfaces:**
- Consumes: `explorer.corpora.available() -> list[Corpus]` (`path`, `name`, `entries`, `style`), `corpora.load(path) -> tuple[str, str]`, `corpora.headwords_of(text) -> list[str]`; `explorer.witz.available() -> bool` and `witz.read(...) -> Reading`; `explorer.bench.generate(procedure_id, text, lang, params) -> tuple[str, str]`.
- Produces: `stage.corpus_choices() -> list[CorpusChoice]` where `CorpusChoice(path, name, entries, style, register)` and `register` is `"baroque"` for `style == "jean_paul"` and `"modern"` otherwise.

- [ ] **Step 1: Write the failing test**

Append to `apps/explorer/tests/test_stage.py`:

```python
def test_the_scene_renders_without_any_corpus() -> None:
    """Every machine except the author's has an empty DENCKRING_CORPORA. A scene that
    exploded there would be worse than one that explains itself (ADR 0020: corpora are
    never shipped)."""
    import os

    from explorer import corpora

    original = os.environ.get("DENCKRING_CORPORA")
    os.environ["DENCKRING_CORPORA"] = "/nonexistent-for-this-test"
    corpora.available.cache_clear() if hasattr(corpora.available, "cache_clear") else None
    try:
        response = client.get("/stage/ideenwuerfeln")
        assert response.status_code == 200
        assert "no corpus" in response.text.lower()
    finally:
        if original is None:
            os.environ.pop("DENCKRING_CORPORA", None)
        else:
            os.environ["DENCKRING_CORPORA"] = original


def test_each_corpus_maps_to_a_register() -> None:
    """The corpora already carry the marker that switches the scene's look:
    `style: jean_paul` and `style: modern`."""
    assert stage.register_for("jean_paul") == "baroque"
    assert stage.register_for("modern") == "modern"
    assert stage.register_for("anything-else") == "modern"
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run --project apps/explorer pytest tests/test_stage.py -q
```

Expected: FAIL — no `register_for`, no route.

- [ ] **Step 3: Implement**

Append to `stage.py`:

```python
from explorer import corpora

#: A corpus's own `style` marker decides how the scene looks. Jean Paul's excerpts are
#: paper and copperplate; anything else is a modern card.
REGISTERS = {"jean_paul": "baroque"}


def register_for(style: str) -> str:
    """The visual register a corpus's `style` marker asks for."""
    return REGISTERS.get(style, "modern")


@dataclass(frozen=True)
class CorpusChoice:
    """One corpus, offered to the scene."""

    path: str
    name: str
    entries: int
    style: str
    register: str


def corpus_choices() -> list[CorpusChoice]:
    """Whatever is in `DENCKRING_CORPORA`, with its register resolved."""
    return [
        CorpusChoice(
            path=item.path,
            name=item.name,
            entries=item.entries,
            style=item.style,
            register=register_for(item.style),
        )
        for item in corpora.available()
    ]
```

In `app.py`:

```python
@app.get("/stage/ideenwuerfeln", response_class=HTMLResponse)
def stage_ideenwuerfeln(request: Request, chrome: str = "on") -> HTMLResponse:
    return page(
        request,
        "stage_ideenwuerfeln.html",
        scene=stage.scene("ideenwuerfeln"),
        choices=stage.corpus_choices(),
        can_read=witz.available(),
        chrome_off=chrome == "off",
    )


@app.post("/stage/ideenwuerfeln/act", response_class=HTMLResponse)
async def stage_ideenwuerfeln_act(request: Request) -> HTMLResponse:
    """Throw the dice: draw slips from the chosen corpus under one headword."""
    form = dict(await request.form())
    path = str(form.get("corpus_path", ""))
    headword = str(form.get("headword", ""))
    text, problem = corpora.load(path) if path else ("", "no corpus chosen")
    if problem:
        return page(request, "_stage_throw.html", throw="", problem=problem, headword=headword)
    produced, trouble = bench.generate(
        "ideenwuerfeln", text, "en", {"headword": headword} if headword else {}
    )
    return page(
        request,
        "_stage_throw.html",
        throw=produced,
        problem=trouble,
        headword=headword,
        can_read=witz.available(),
    )
```

- [ ] **Step 4: Write the templates**

`stage_ideenwuerfeln.html` shows the corpus picker, a headword box, a throw button, and — when `choices` is empty — the placeholder:

```html
{% extends "stage.html" %}
{% block title %}Ideenwürfeln{% endblock %}
{% block main %}
<h1>{{ scene.title }}</h1>
{% if not choices %}
<p class="placeholder">
  There is no corpus to throw. Point <code>DENCKRING_CORPORA</code> at a directory of
  excerpt files; nothing is bundled, because a corpus belongs to whoever assembled it.
</p>
{% else %}
<form hx-post="/stage/ideenwuerfeln/act" hx-target="#throw">
  <select name="corpus_path">
    {% for choice in choices %}
    <option value="{{ choice.path }}" data-register="{{ choice.register }}">
      {{ choice.name }} — {{ "{:,}".format(choice.entries) }} entries
    </option>
    {% endfor %}
  </select>
  <input name="headword" placeholder="a headword to collide under">
  <button type="submit">Throw</button>
</form>
{% endif %}
<div id="throw"></div>
{% endblock %}
{% block caption %}{{ scene.caption }}{% endblock %}
```

`_stage_throw.html` renders the slips and the Witz control:

```html
{% if problem %}<p class="problem">{{ problem }}</p>{% endif %}
{% if throw %}
<div class="slips">
  {% for slip in throw.split("\n") if slip.strip() %}
  <p class="slip">{{ slip }}</p>
  {% endfor %}
</div>
{% if can_read %}
<form hx-post="/p/ideenwuerfeln/witz" hx-target="#witz">
  <input type="hidden" name="throw" value="{{ throw }}">
  <input type="hidden" name="headword" value="{{ headword }}">
  <button type="submit">Find the Witz</button>
</form>
<div id="witz"></div>
<p class="disclaimer">
  A reading, not a verdict. No <code>Report</code> is produced and no checker consults
  it — the Witz is the step no program performs.
</p>
{% endif %}
{% endif %}
```

- [ ] **Step 5: Run the tests and commit**

```bash
uv run --project apps/explorer pytest tests/test_stage.py -q
git add apps/explorer/src/explorer apps/explorer/tests/test_stage.py
git commit -m "feat(explorer): scene two, the collision in two registers"
```

---

### Task 5: Scene 3 — Arca musarithmica

**Files:**
- Modify: `stage.py`, `app.py`, `static/stage.css`
- Create: `templates/stage_arca.html`, `templates/_stage_column.html`
- Test: `apps/explorer/tests/test_stage.py`

**Interfaces:**
- Consumes: `denckring.core.arca.parse(text) -> Pinakes` with `.patterns(syllables, syntagma)` and `.lengths(syntagma)`; `denckring.check("arca_musarithmica", text, source=..., pinakes=...)`.
- Produces: `stage.TABLET` — the synthetic tablet JSON string, and `stage.tablet() -> Pinakes`.

- [ ] **Step 1: Write the failing test**

```python
def test_the_arca_scene_uses_a_tablet_that_is_not_kirchers() -> None:
    """Kircher's own pitch numbers are not shipped, and the golden fixture's tablet is
    synthetic and says so. The scene must not imply otherwise."""
    assert "4" in str(sorted(stage.tablet().lengths()))
    response = client.get("/stage/arca")
    assert response.status_code == 200
    assert "not his" in response.text


def test_the_pattern_the_scene_offers_really_sets_the_phrase() -> None:
    from denckring import check

    source = "the cat sat down"
    pattern = stage.tablet().patterns(4)[0]
    report = check("arca_musarithmica", pattern, source=source, pinakes=stage.TABLET)
    assert report.satisfied is True
```

- [ ] **Step 2: Run it and watch it fail**

Expected: FAIL — no `stage.tablet`.

- [ ] **Step 3: Implement**

Append to `stage.py`:

```python
from denckring.core import arca

#: The tablet the golden fixture uses. The mechanism is Kircher's Musurgia Universalis
#: (1650) book VIII; the patterns are not his, and the scene says so on screen. ADR 0021
#: is why: this project implements the indexing and leaves the columns opaque.
TABLET = (
    '{"tones": ["I", "II", "III"], "syntagmata": {"1": '
    '{"4": ["5 3 1 3", "1 3 5 3"], "6": ["5 5 3 1 3 5", "1 1 3 5 3 1"]}}}'
)


def tablet() -> arca.Pinakes:
    """The scene's pattern table, parsed."""
    return arca.parse(TABLET)
```

The syllable count is what indexes the tablet, and the arca procedure itself gets it from
`line_syllables`, which returns `(offset, syllables, estimated)` per line. The scene uses
the same function rather than a second way of counting:

```python
from denckring.procedures.syllable_count import line_syllables


@app.get("/stage/arca", response_class=HTMLResponse)
def stage_arca(request: Request, chrome: str = "on") -> HTMLResponse:
    return page(
        request,
        "stage_arca.html",
        scene=stage.scene("arca"),
        tablet=stage.tablet(),
        lengths=stage.tablet().lengths(),
        chrome_off=chrome == "off",
    )


@app.post("/stage/arca/act", response_class=HTMLResponse)
async def stage_arca_act(request: Request) -> HTMLResponse:
    """Measure the phrase, light the tablet for that length, check the chosen column."""
    form = dict(await request.form())
    phrase = str(form.get("phrase", ""))
    pattern = str(form.get("pattern", ""))
    measured = line_syllables(phrase, bench.pack_for("en"))
    syllables = measured[0][1] if measured else 0
    offered = stage.tablet().patterns(syllables)
    report = (
        check("arca_musarithmica", pattern, source=phrase, pinakes=stage.TABLET)
        if pattern
        else None
    )
    return page(
        request,
        "_stage_column.html",
        phrase=phrase,
        syllables=syllables,
        offered=offered,
        report=report,
    )
```

- [ ] **Step 4: Templates**

`stage_arca.html`: a phrase box, the tablet drawn as columns of patterns grouped by syllable count with the matching group highlighted, and a note reading "the mechanism is Kircher's; the patterns are not his". `_stage_column.html`: the chosen column, and the verdict.

- [ ] **Step 5: Run the tests and commit**

```bash
uv run --project apps/explorer pytest tests/test_stage.py -q
git add apps/explorer/src/explorer apps/explorer/tests/test_stage.py
git commit -m "feat(explorer): scene three, the tablet answers for the length"
```

---

### Task 6: Scene 4 — N+7

**Files:**
- Modify: `stage.py`, `app.py`, `static/stage.css`
- Create: `templates/stage_n_plus_7.html`, `templates/_stage_displaced.html`
- Test: `apps/explorer/tests/test_stage.py`

**Interfaces:**
- Consumes: `denckring.procedures.n_plus_7.displace(text, pack, offset) -> str`; `pack.nouns() -> Sequence[str]`; `pack.noun_index(word) -> int | None`; `denckring.check("n_plus_7", produced, source=source)`.
- Produces: `stage.displacement(source, offset) -> list[Step]` where `Step(word: str, replacement: str, neighbours: list[str])` and `neighbours` is the window of the noun list the word travels through.

- [ ] **Step 1: Write the failing test**

```python
def test_the_displacement_the_scene_animates_is_the_one_the_checker_accepts() -> None:
    from denckring import check
    from denckring.procedures.n_plus_7 import displace

    source = "the cat sat on the table"
    produced = displace(source, stage.pack(), 7)
    assert check("n_plus_7", produced, source=source).satisfied is True


def test_the_scene_shows_the_words_a_noun_travels_past() -> None:
    steps = stage.displacement("the cat sat on the table", 7)
    cat = next(step for step in steps if step.word == "cat")
    assert cat.replacement == "catacomb"
    assert len(cat.neighbours) == 8
    assert cat.neighbours[0] == "cat" and cat.neighbours[-1] == "catacomb"
```

- [ ] **Step 2: Run it and watch it fail**

Expected: FAIL — no `stage.displacement`.

- [ ] **Step 3: Implement**

```python
from denckring.core.protocol import LanguagePack
from denckring.lang import get_pack


@dataclass(frozen=True)
class Step:
    """One noun's journey down the list."""

    word: str
    replacement: str
    neighbours: list[str]


def pack() -> LanguagePack:
    """The English pack, with the noun list the scene walks."""
    return get_pack("en")


def displacement(source: str, offset: int = 7) -> list[Step]:
    """Each noun of `source`, with the entries it passes on the way to its replacement."""
    english = pack()
    nouns = english.nouns()
    steps: list[Step] = []
    for token in english.tokenize(source):
        index = english.noun_index(token.lower())
        if index is None:
            continue
        landing = index + offset
        if landing >= len(nouns):
            continue
        steps.append(
            Step(
                word=token,
                replacement=nouns[landing],
                neighbours=[nouns[i] for i in range(index, landing + 1)],
            )
        )
    return steps
```

**Note:** the test above asserts `cat → catacomb` against Open English WordNet 2024. If that assertion fails, the noun list has changed and the *test* is the thing to update — but check `CHANGELOG.md` first, because a silent change to the noun list is exactly the event the N+7 fixtures exist to catch.

- [ ] **Step 4: Route and templates**

GET `/stage/n_plus_7` renders the source, and each noun as a column of `neighbours` that scrolls to its last entry on click. POST `/stage/n_plus_7/act` runs `displace` then `check` and renders `_stage_displaced.html` with both the produced text and the verdict.

- [ ] **Step 5: Run the tests and commit**

```bash
uv run --project apps/explorer pytest tests/test_stage.py -q
git add apps/explorer/src/explorer apps/explorer/tests/test_stage.py
git commit -m "feat(explorer): scene four, seven entries down the dictionary"
```

---

### Task 7: Scene 5 — Ghazal

**Files:**
- Modify: `stage.py`, `app.py`, `static/stage.css`
- Create: `templates/stage_ghazal.html`, `templates/_stage_couplets.html`
- Test: `apps/explorer/tests/test_stage.py`

**Interfaces:**
- Consumes: `denckring.check("ghazal", text)`; `explorer.bench.mark_up(text, report) -> str` for the inline violation marking the bench already does.
- Produces: `stage.GHAZAL_GOOD` and `stage.GHAZAL_BROKEN`, two example texts.

- [ ] **Step 1: Write the failing test**

```python
def test_the_ghazal_examples_are_what_the_scene_claims() -> None:
    """One passes, one fails on the couplet the scene points at. A scene whose
    counterexample quietly passed would be teaching the wrong thing."""
    from denckring import check

    assert check("ghazal", stage.GHAZAL_GOOD).satisfied is True
    broken = check("ghazal", stage.GHAZAL_BROKEN)
    assert broken.satisfied is False
    assert broken.violations
```

- [ ] **Step 2: Run it and watch it fail**

Expected: FAIL — no `GHAZAL_GOOD`.

- [ ] **Step 3: Implement**

Write the two examples by running them against the checker first — do not invent couplets and hope. Start from the golden fixture:

```bash
uv run python -c "
import yaml, pathlib
print(pathlib.Path('src/denckring/eval/fixtures/golden/ghazal.yaml').read_text())
"
```

Take the satisfying case verbatim as `GHAZAL_GOOD`, and derive `GHAZAL_BROKEN` from it by changing the rhyme in one couplet, then confirm both with `check` before committing them.

- [ ] **Step 4: Route and templates**

GET `/stage/ghazal` renders the good example in an editable area. POST `/stage/ghazal/act` checks it and renders `_stage_couplets.html`, using `bench.mark_up(text, report)` for the inline marking and highlighting the radif and qafia in each couplet's closing words.

- [ ] **Step 5: Run the tests and commit**

```bash
uv run --project apps/explorer pytest tests/test_stage.py -q
git add apps/explorer/src/explorer apps/explorer/tests/test_stage.py
git commit -m "feat(explorer): scene five, the refrain and the rhyme before it"
```

---

### Task 8: The explorer enters CI

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `apps/explorer/README.md`

- [ ] **Step 1: Add the job**

The explorer has 957 lines and a test file CI has never run, and this plan roughly doubles it. Add to `.github/workflows/ci.yml`, matching the style of the jobs already there:

```yaml
  explorer:
    # A development tool, but a tested one: 957 lines that no other job touches,
    # and the stage doubles it.
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --project apps/explorer
      - run: uv run --project apps/explorer ruff check
      - run: uv run --project apps/explorer mypy --strict src tests
      - run: uv run --project apps/explorer pytest -q
```

- [ ] **Step 2: Run everything locally as CI will**

```bash
uv run --project apps/explorer ruff check
uv run --project apps/explorer ruff format --check
uv run --project apps/explorer mypy --strict src tests
uv run --project apps/explorer pytest -q
uv run pytest -q            # the repository suite, still 3395 passed
```

- [ ] **Step 3: Note the stage in the explorer's README**

Add a short section naming `/board` and `/stage`, and stating that the scenes need no corpora except Ideenwürfeln, which explains itself when `DENCKRING_CORPORA` is empty.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml apps/explorer/README.md
git commit -m "ci: run the explorer's tests, which nothing has ever run"
```

---

## Self-Review

**Spec coverage.** The board is Task 1; the shell, the fixed recording size and `?chrome=off` are Task 2; the five scenes are Tasks 3–7 in the spec's order; the CI job the spec asks for is Task 8. The spec's "corpus-absent path" test is Task 4 Step 1. The spec's "one claim test per scene" is Step 1 of Tasks 3, 5, 6 and 7 — the rings' word satisfying `denckring`, the arca pattern setting its phrase, the N+7 output satisfying `n_plus_7`, and the ghazal counterexample failing.

**Known softness, stated rather than hidden.** Tasks 5, 6 and 7 give full failing tests and exact interfaces but describe their templates in prose rather than writing every line of HTML. That is deliberate: the visual language is settled by Task 3's review with a human, and HTML written before that review would be rewritten after it. The Python in every task is complete, and the tests are complete for all five scenes — which is where the claims live.

**Every datum in the tests was run, not assumed.** `noun_index("cat")` is 8402 and `nouns[8409]` is `catacomb`, so Task 6's window of eight entries is what the scene will actually show; `denckring.apply()` really does turn out words the checker accepts; the arca's syllable count comes from `line_syllables`, which is the function the procedure itself uses, rather than a second way of counting invented for the scene.

**Type consistency.** `Scene`, `RingSlot`, `Rings`, `CorpusChoice`, `Step` and `Tile` are each defined once, in the task that introduces them, and referenced by those names afterwards. `stage.scene(slug)` is defined in Task 2 and used by every scene route. `page(request, name, **context)` is the existing helper throughout. `chrome_off` is the context key in every scene route and the only thing `stage.html` tests.
