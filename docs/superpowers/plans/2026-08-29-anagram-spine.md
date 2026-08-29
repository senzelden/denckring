# Anagram Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `apply anagram "dormitory"` return `room dirty`, ranked above the junk covers, by shipping a commonness-graded word list and a surface that can carry the ranking.

**Architecture:** Four workstreams in dependency order. W0 closes two recorded test blind spots first, so the new search lands on a net that works. W1 changes the single `_produce` primitive from `list[str]` to `list[Candidate]` so a generator can attach scores. W2 vendors SCOWL into `denckring-en-data` behind a new `lexicon.graded_words` capability. W3 replaces the greedy noun walk with a ranked, budgeted multi-cover search.

**Tech Stack:** Python 3.11+, pydantic v2, Hypothesis, pytest, mypy --strict, ruff, uv workspace, hatchling.

**Spec:** `docs/superpowers/specs/2026-08-29-anagram-spine-design.md`

## Global Constraints

- The gate is four commands, all four, every task: `uv run pytest -q`, `uv run mypy --strict src tests`, `uv run ruff check .`, `uv run ruff format --check .`. A green `ruff check` alone is not a green gate.
- For any task touching a procedure, also: `uv run denckring eval --all` (expect `119 procedures · 353 passed · 0 failed`) and `uv run denckring status` (expect `154 · 128 · 119 · 119 · 26`). Neither number should change in this plan; if one does, stop and say so.
- Comments explain **why**, not what, and cite ADRs by number. A comment that has become false is a defect, not a nit.
- Stage files **by name**. Never `git add -A` — `undefined/queneau-seams.png` is untracked and must stay that way.
- `docs/index.md` is generated and gitignored. Edit `README.md`; never commit `docs/index.md`.
- `procedure_id` is a reserved test-argument name (auto-parametrised by `tests/conftest.py`). In any new test, name the argument `pid`.
- `PARAMETER_GATED` in `tests/test_round_trip.py` is not a knob. If `test_the_named_coverage_gap_is_the_whole_coverage_gap` fails, a row became unreachable — find the cause.
- Catalogue provenance: `author-stated` must cite a source with a year. Do not invent citations.
- Neither installation nor use may touch the network (ADR 0013). Build scripts are run by hand; their output is vendored.

---

### Task 1: Widen the round trip to draw the seed

**Files:**
- Modify: `tests/test_round_trip.py:118` (the `derandomize` already present on `collect`), `:171-280` (the five properties)
- Modify: whichever generator(s) the widening exposes — unknown until run, see Step 3

**Interfaces:**
- Consumes: nothing
- Produces: `_apply_args(procedure_id: str, seed: int) -> dict[str, int]` unchanged in signature; callers now pass a drawn seed rather than the literal `0`

**Why this is first:** the spec's W0. Widening `TEXT`'s alphabet surfaced two latent generator/checker disagreements, one per chapter-2 task. Widening the seed is the same kind of widening on a different axis. Do it before the new drawing search exists, not after.

**This task has unknown size.** Steps 3–4 are a loop whose length is what the widening finds. That is the deliverable, not a risk to be managed away.

- [ ] **Step 1: Add a seed strategy and thread it through the four `TEXT` properties**

At the top of the file, beside `TEXT`:

```python
#: Ten of the 27 constructive rows draw at random. Every property below used to
#: pass `_apply_args(procedure_id, 0)` — the same seed on every example, in every
#: property, on every run — so those ten were exercised at exactly one draw per
#: input text and never the rest of the seed space. A generator producing text
#: its own `check` rejects on seed 1 but not on seed 0 passed here in silence.
#: Bounded rather than unbounded because a seed is fed to `random.Random` and a
#: bignum buys no additional coverage, only slower shrinking.
SEED = st.integers(min_value=0, max_value=2**16 - 1)
```

Change each of `test_apply_output_satisfies_check`, `test_every_produced_text_satisfies_check`, `test_every_produced_text_differs_from_the_input` and `test_apply_does_not_return_its_input` from:

```python
@settings(max_examples=50, deadline=None)
@given(TEXT)
def test_apply_output_satisfies_check(text: str) -> None:
```

to:

```python
@settings(max_examples=50, deadline=None, derandomize=True)
@given(TEXT, SEED)
def test_apply_output_satisfies_check(text: str, seed: int) -> None:
```

and replace every `_apply_args(procedure_id, 0)` inside them with `_apply_args(procedure_id, seed)`.

`derandomize=True` is added to all four, not only to `test_apply_output_satisfies_check`. The chapter-2 spec named that one property, but the same argument applies to its three companions and there is no reason to leave them intermittent.

**Do not touch** `test_apply_is_deterministic_under_a_fixed_seed`. It passes `7` twice on purpose: its subject is that two identical calls agree, so drawing a seed there would test nothing new and drawing two would test the opposite of what it means.

**Do not touch** `test_the_named_coverage_gap_is_the_whole_coverage_gap`. It asks which rows are reachable at all, not what they produce; `seed=0` is a fine witness for reachability and a drawn seed would make the coverage set itself vary between runs.

- [ ] **Step 2: Update the module docstring to say what changed and why**

The docstring at the top of `tests/test_round_trip.py` currently describes `TEXT`'s alphabet at length and says nothing about the seed. Add a paragraph in the same register, immediately after the `_apply_args` paragraph:

```
The seed is drawn, not pinned. Every property here used to pass `0`, so the ten
rows that draw were exercised at one draw per input and the rest of the seed space
never at all. That was the larger of the two blind spots the chapter-2 spec
recorded, and on a different axis from the missing `derandomize=True` beside it:
that one is about which inputs Hypothesis tries, this one about which draw each
generator makes from them, so closing either left the other standing. Both are
closed here. `test_apply_is_deterministic_under_a_fixed_seed` still pins its seed,
and must: its subject is that two identical calls agree.
```

- [ ] **Step 3: Run the suite and record everything it finds**

Run: `uv run pytest -q tests/test_round_trip.py`

Expected: **failures are the likely outcome and the point of the task.** For each failure, record the procedure id, the drawn seed, and the falsifying text before fixing anything.

If the suite is green on the first run, do not accept that at face value. Verify the widening actually varies the draw by temporarily asserting a contradiction inside one property (e.g. `assert seed == 0`) and confirming it fails. Remove the temporary assertion afterwards. A seed-widening that goes green without ever having varied anything has closed no blind spot.

- [ ] **Step 4: Fix each disagreement, one commit per procedure**

For each failure from Step 3, the fix is in the generator or its checker, never in the property and never by adding the row to a skip set. Both chapter-2 precedents (`cent_mille_milliards`, `recombination`) were real defects in the generator, and this is the third of the same kind.

Add a row-level regression test pinning the specific seed that exposed it, so the fix stays fixed even if the property's draw sequence shifts:

```python
def test_apply_output_satisfies_check_at_the_seed_that_exposed_it() -> None:
    """Regression: <procedure> produced text its own check rejected at seed <N>.

    Pinned at row level because the round-trip property draws its seed, so the
    example that found this is not guaranteed to be drawn again.
    """
    procedure = all_procedures()["<procedure_id>"]
    produced = procedure.apply("<falsifying text>", lang="en", seed=<N>)
    assert procedure.check(produced, lang="en", source="<falsifying text>").satisfied
```

Commit each fix separately:

```bash
git add tests/test_<procedure>.py src/denckring/procedures/<procedure>.py
git commit -m "fix: <procedure> produced text its own check rejects on some seeds"
```

- [ ] **Step 5: Run the full gate**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
```

Expected: all green; `119 procedures · 353 passed · 0 failed` and `154 · 128 · 119 · 119 · 26`.

- [ ] **Step 6: Commit the widening**

```bash
git add tests/test_round_trip.py
git commit -m "test: the round trip draws its seed instead of pinning zero"
```

---

### Task 2: `Candidate`, and `Production` built from it

**Files:**
- Modify: `src/denckring/core/protocol.py:74-100`
- Modify: `src/denckring/core/base.py:289-327` (`produce`)
- Test: `tests/test_production.py`

**Interfaces:**
- Consumes: nothing from Task 1
- Produces: `Candidate(text: str, metrics: dict[str, float])`; `Production.candidates: list[Candidate]` (min_length=1); `Production.texts -> list[str]` as a serialising computed field. `_produce` still returns `list[str]` after this task — Task 3 changes it.

This task delivers the surface without touching a single generator, so it can be reviewed on its own.

- [ ] **Step 1: Write the failing test**

Create `tests/test_production.py` (or append, if it exists):

```python
def test_production_exposes_texts_derived_from_candidates() -> None:
    production = Production(
        procedure="anagram",
        candidates=[Candidate(text="room dirty", metrics={"max_band": 50.0})],
    )
    assert production.texts == ["room dirty"]


def test_texts_survives_serialisation_so_the_json_surface_is_unchanged() -> None:
    """`apply --json` and the MCP surface both read `texts`. A plain @property
    would vanish from model_dump() and break them silently."""
    production = Production(procedure="anagram", candidates=[Candidate(text="tinsel")])
    assert production.model_dump()["texts"] == ["tinsel"]


def test_a_production_with_no_candidates_is_a_validation_error() -> None:
    """`min_length` moved from `texts` to `candidates` with the data. Without it
    `apply`'s `texts[0]` is a bare IndexError rather than a named field error."""
    with pytest.raises(ValidationError):
        Production(procedure="anagram", candidates=[])
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_production.py`
Expected: FAIL — `Candidate` is not defined.

- [ ] **Step 3: Implement**

In `src/denckring/core/protocol.py`, above `Production`:

```python
class Candidate(BaseModel):
    """One result, with whatever the generator knows about it.

    `Production.texts` was a list of strings, and for twenty-six of the
    twenty-seven generators that is still the whole truth. `anagram` is the
    exception ADR 0026 anticipated in writing: it ranks its covers by the SCOWL
    band of their least common word, and a bare string cannot carry the number
    the ranking was computed from. A caller shown `room dirty` ahead of
    `morty dior` deserves to see why, rather than trusting the order.

    `metrics` is open rather than a fixed set of fields because what a generator
    knows is generator-specific, and a schema listing every score any procedure
    might ever have would be a schema nobody could satisfy.
    """

    text: str
    metrics: dict[str, float] = Field(default_factory=dict)
```

Replace `Production.texts` with:

```python
    #: Best first — `apply` returns `texts[0]`, so the order is the contract.
    #: Never empty: a generator with nothing to return raises, and an empty list
    #: would be a fourth way of saying a failure that has three honest names.
    #: `min_length=1` makes that a validation error naming the field rather than
    #: a bare `IndexError` from `apply`'s `texts[0]`.
    candidates: list[Candidate] = Field(min_length=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def texts(self) -> list[str]:
        """The candidates' texts, in the same order.

        A `computed_field` and not a plain `@property`: `apply --json` and the
        MCP surface both read `texts` out of `model_dump()`, and a plain property
        is absent from it. Kept rather than removed because it is the shape every
        existing consumer already reads, and ADR 0026 made `texts[0]` the
        definition of `apply`.
        """
        return [candidate.text for candidate in self.candidates]
```

Add `computed_field` to the `pydantic` import.

Leave the `truncated` comment block exactly where it is — it is still true.

In `src/denckring/core/base.py`, in `produce`, change the return to:

```python
        return Production(
            procedure=self.id,
            candidates=[Candidate(text=text) for text in found[:limit]],
            truncated=len(found) > limit,
            metrics={"found": float(len(found))},
        )
```

and add `Candidate` to the `denckring.core.protocol` import.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -q tests/test_production.py && uv run pytest -q`
Expected: PASS.

- [ ] **Step 5: Run the gate and commit**

```bash
uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
git add src/denckring/core/protocol.py src/denckring/core/base.py tests/test_production.py
git commit -m "feat: Production is built from candidates, texts derived from them"
```

---

### Task 3: `_produce` returns candidates

**Files:**
- Modify: `src/denckring/core/base.py` (`_produce` signature, `_guard_degenerate`, `produce`)
- Modify: all 27 files under `src/denckring/procedures/` that define `_produce`
- Test: `tests/test_production.py`

**Interfaces:**
- Consumes: `Candidate` from Task 2
- Produces: `Produced(candidates: list[Candidate], truncated: bool)`; `_produce(self, text: str, pack: LanguagePack, params: A) -> Produced` as the single primitive; `plain(texts: Iterable[str]) -> Produced` helper exported from `denckring.core.base`

**Why not an overlay:** ADR 0026 made `_produce -> list[str]` the single primitive and rejected two primitives in writing — "two would make every consumer ask which a given procedure implements". Adding a `_produce_scored` that only `anagram` implements would reintroduce exactly that, one day after it was decided.

**Why a structure and not a bare list:** Task 6 needs the generator to report truncation the spine cannot see. The spine derives `truncated` from `len(found) > limit`, and node-budget exhaustion means the search found *fewer* results, not more — so that derivation can never express it. A list would force a second channel for the flag (an instance attribute, a re-entrant hook, a sentinel metrics key), and each of those is the two-primitive condition in a different hat.

- [ ] **Step 1: Write the failing test**

```python
def test_produce_is_the_only_primitive() -> None:
    """ADR 0026 rejected two primitives; ADR 0027 changes this one's type rather
    than adding a second. A generator defining a scored variant alongside
    `_produce` is the shape that regression would take."""
    for procedure in all_procedures().values():
        if not isinstance(procedure, ConstructiveProcedure):
            continue
        assert not hasattr(procedure, "_produce_scored"), (
            f"{procedure.id}: a second production primitive defeats ADR 0026"
        )


def test_every_generator_returns_produced(pid: str) -> None:
    """`pid`, not `procedure_id`: that name is auto-parametrised by conftest and
    writing it here would be a duplicate-parametrization error."""
    procedure = all_procedures()[pid]
    if not isinstance(procedure, ConstructiveProcedure):
        pytest.skip("not constructive")
    hints = get_type_hints(type(procedure)._produce)
    assert hints["return"] is Produced, f"{pid}: _produce must return Produced"


def test_a_generator_can_report_truncation_the_spine_cannot_derive() -> None:
    """The spine reads `truncated` as `len(found) > limit`, which is false when a
    budget made the search stop early and so found *fewer*. Task 6's node budget
    is exactly that case, and this is the channel that carries it.

    Driven through a stub rather than by constructing a `Production` directly:
    `Production.truncated` already existed and already accepted `True`, so
    asserting on a hand-built one would pass without the channel existing at all.
    """

    class _Stub(ConstructiveProcedure[BaseModel, ApplyParams]):
        id = "stub"
        meta = Meta(id="stub", requires=[], apply_requires=[], languages=["en"])

        @classmethod
        def params_model(cls) -> type[BaseModel]:
            return BaseModel

        @classmethod
        def apply_params_model(cls) -> type[ApplyParams]:
            return ApplyParams

        def _check(self, text: str, pack: LanguagePack, params: BaseModel) -> Report:
            raise NotImplementedError

        def _produce(self, text: str, pack: LanguagePack, params: ApplyParams) -> Produced:
            # Two candidates against a limit of ten: `len(found) > limit` is
            # false, so a true `truncated` can only have come from here.
            return Produced(
                candidates=[Candidate(text="a"), Candidate(text="b")], truncated=True
            )

    production = _Stub().produce("input", lang="en")
    assert production.truncated
    assert not production.metrics["found"] > 10  # the spine's own test did not fire
```

Constructing `_Stub` may need `meta` supplied differently than shown — `BaseProcedure.__init__` reads `catalogue.get(self.id)` and there is no `stub` row. Set the attribute after construction, or build the stub however the existing test suite already fakes a procedure; check `tests/` for an established pattern before inventing one.

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_production.py -k candidates`
Expected: FAIL — generators still annotate `list[str]`.

- [ ] **Step 3: Add the helper and change the abstract signature**

In `src/denckring/core/protocol.py`, beside `Candidate`:

```python
class Produced(BaseModel):
    """What `_produce` hands the spine: its candidates, and whether it gave up.

    `truncated` here is the generator's own, and is not the same statement as
    `Production.truncated`. The spine can see that `max_results` capped a result
    set; it cannot see that a search abandoned its own budget, because that makes
    the set *smaller* rather than larger. `anagram`'s node budget is the case ADR
    0026's spec named in advance as needing this.
    """

    candidates: list[Candidate]
    truncated: bool = False
```

In `src/denckring/core/base.py`:

```python
def plain(texts: Iterable[str]) -> Produced:
    """Candidates with nothing known about them beyond their text.

    Twenty-six of the twenty-seven generators are in this case and say so in one
    call, rather than each spelling out a `Candidate(text=...)` comprehension.
    ADR 0027 changed the primitive's type; it did not claim every procedure
    suddenly has a score, or that any of them ran out of budget.
    """
    return Produced(candidates=[Candidate(text=text) for text in texts])
```

Change the abstract method:

```python
    @abstractmethod
    def _produce(self, text: str, pack: LanguagePack, params: A) -> Produced:
        """Procedure-specific generation, best first. Language and parameters are already valid.

        Ordered even where there is one answer: `apply` returns `texts[0]`, so the
        order is the contract, and a generator that ranks its candidates puts its
        winner at the front. One primitive rather than a `str` one beside a
        `list` one, because two would make every consumer ask which a given
        procedure implements.

        `Produced` and not `list[str]` since ADR 0027, for two reasons that arrived
        together: a generator that ranks needs somewhere to put the number it
        ranked by, and a generator that abandons its own budget needs somewhere to
        say so — the spine cannot derive the second, because giving up makes the
        result set smaller and its own test is whether the set was too large.
        Generators with neither wrap their strings with `plain()`.
        """
```

Update `_guard_degenerate`'s signature to take and return `list[Candidate]`, comparing `candidate.text` where it currently compares the string.

Update `produce`'s tail:

```python
        produced = self._produce(text, pack, parsed)
        if not produced.candidates:
            raise DegenerateOutput(self.id, DegenerateOutput.NOTHING)
        found = self._guard_degenerate(text, produced.candidates, parsed)
        limit = getattr(parsed, "max_results", 1)
        return Production(
            procedure=self.id,
            candidates=found[:limit],
            # Either event means the same thing to a reader — what you were shown
            # is not everything — but only one of them is visible from here.
            truncated=produced.truncated or len(found) > limit,
            metrics={"found": float(len(found))},
        )
```

Leave the long comment above the `DegenerateOutput(NOTHING)` raise exactly as it is; every word of it is still true of `produced.candidates`.

- [ ] **Step 4: Migrate all 27 generators**

Mechanical. In each file under `src/denckring/procedures/` defining `_produce`:

1. change the return annotation from `list[str]` to `list[Candidate]`
2. wrap the returned list in `plain(...)`
3. add `Candidate` and `plain` to the `denckring.core.base` import as needed

So `anagram.py`'s current tail:

```python
        return [" ".join(found)]
```

becomes:

```python
        return plain([" ".join(found)])
```

Do **not** give `paragram` real metrics here, even though it computes a ranking it discards. Its score is not sourced the way a SCOWL band is, and naming a metric for it is a separate argument. It wraps with `plain()` like the other twenty-five.

Find them all with:

```bash
grep -rln "def _produce" src/denckring/procedures/
```

- [ ] **Step 5: Run the gate**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
```

Expected: all green, `119 procedures · 353 passed · 0 failed`, `154 · 128 · 119 · 119 · 26`.

`mypy --strict` is the real check here — it is what proves all 27 were migrated rather than most of them.

- [ ] **Step 6: Commit**

```bash
git add src/denckring/core/base.py src/denckring/procedures/ tests/test_production.py
git commit -m "feat: _produce returns candidates, one primitive still"
```

- [ ] **Step 7: Write ADR 0027**

Create `docs/adr/0027-candidates-carry-their-scores.md`, in the house register: a real problem, a decision, and consequences that admit costs. `docs/adr/0015-lexicon-capabilities.md` is the model for admitting a cost honestly.

It must record, in the Consequences section and not softened:

- this is churn across 27 files to serve one row's ranking, on a surface stabilised the day before;
- the alternative considered was a `_produce_scored` overlay, rejected because it reintroduces the two-primitive condition ADR 0026 named;
- `Production.texts` is retained as a computed field rather than removed, so nothing outside had to change — which also means the new field is invisible to every existing consumer until one asks for it;
- it amends ADR 0026 rather than replacing it.

```bash
git add docs/adr/0027-candidates-carry-their-scores.md
git commit -m "docs: ADR 0027, candidates carry their scores, amending 0026"
```

---

### Task 4: Vendor SCOWL into `denckring-en-data`

**Files:**
- Create: `packages/denckring-en-data/scripts/build_graded_words.py`
- Create: `packages/denckring-en-data/src/denckring_en_data/data/graded_words.txt.gz`
- Create: `packages/denckring-en-data/LICENSE-SCOWL`
- Modify: `packages/denckring-en-data/src/denckring_en_data/data/metadata.json`
- Modify: `packages/denckring-en-data/NOTICE`, `packages/denckring-en-data/pyproject.toml`, `packages/denckring-en-data/README.md`

**Interfaces:**
- Consumes: nothing
- Produces: `data/graded_words.txt.gz`, lines of `word\tband`, sorted, band as an integer SCOWL size. Read by Task 5.

- [ ] **Step 1: Write the build script**

Model it on `packages/denckring-de-data/scripts/build_lexicon.py` — same docstring shape, same `mtime=0` gzip trick, same metadata write.

```python
"""Regenerate the vendored graded English word list from SCOWL.

Committed so the data file is reproducible and diffable, and so neither
installation nor use touches the network (ADR 0013).

    python scripts/build_graded_words.py

SCOWL is MIT-like: no share-alike, no non-commercial clause. It is derived from
several sources with their own terms, and UKACD's requires its notice be
reproduced verbatim — which is why LICENSE-SCOWL is SCOWL's whole Copyright file
rather than a summary of it. See LICENSE-SCOWL.
"""
```

Key decisions to encode, each with its comment:

```python
#: Pinned, not "latest": the shipped band of every word is part of this package's
#: observable behaviour, so an unpinned build would silently reorder anagram
#: results between releases.
RELEASE = "2020.12.07"
URL = f"https://downloads.sourceforge.net/project/wordlist/SCOWL/{RELEASE}/scowl-{RELEASE}.tar.gz"

#: Only `*-words.*`. SCOWL also ships `*-proper-names.*` and `*-abbreviations.*`,
#: and those are precisely the defect being fixed: `sutphen`, `dority` and
#: `romito` are why the existing `known_words()` oracle cannot tell `room` from
#: `romito`. A general word list that readmits surnames would have bought nothing.
WANTED = re.compile(r"^(english|american)-words\.(\d+)$")

#: 60 is where the shipped list stops, and the number is SCOWL's own: its
#: documentation calls 60 "the largest size that I am fairly confident does not
#: contain any misspellings or invalid words". `max_size` lets a caller ask for
#: less; nothing ships the sizes above it, so nothing can ask for more.
MAX_BAND = 60

#: SCOWL's files are Latin-1, not UTF-8.
ENCODING = "iso-8859-1"
```

A word appearing in several size files takes its **lowest** band — the smallest list it appears in is the strongest statement of its commonness.

Filter to purely alphabetic entries, mirroring `noun_list()`'s restriction and for the related reason: a cover made of `cat's-paw` cannot survive the tokenizer that reads the result back. Casefold on the way in.

Write `word\tband` lines sorted by word, gzipped with `mtime=0`.

- [ ] **Step 2: Fetch the upstream licence text and confirm it before committing data**

Download the release, and copy its `Copyright` file **verbatim** to `packages/denckring-en-data/LICENSE-SCOWL`.

Read it. Confirm before proceeding:
- no share-alike clause;
- no non-commercial clause;
- the specific attribution and verbatim-reproduction terms of every component source, UKACD's in particular.

**If any of that does not hold, stop and report rather than shipping the data.** The spec's licence reading is not legal advice and is not a substitute for the shipped file. This step is the one that makes the claim true.

- [ ] **Step 3: Run the build and record what it produced**

```bash
cd packages/denckring-en-data && python scripts/build_graded_words.py
```

Record the entry count and the compressed size. Resolve the documented discrepancy while here: the research note says band 95 is archaic; upstream v2 says 85 is archaic and does not ship 95 at all, 95 being v1's "insane" tier. Note which the vendored release actually uses, in `metadata.json`'s `source` string and in the script's comment. Neither the research note nor the spec is authoritative here; the release is.

- [ ] **Step 4: Update metadata and the licence surface**

`metadata.json` gains a `graded_words.txt.gz` count beside the existing two, and its `source` string names SCOWL, the pinned release, and `LICENSE-SCOWL`.

`pyproject.toml`: add `LICENSE-SCOWL` to `license-files`, and widen the `license` expression. It is currently `"Apache-2.0 AND CC-BY-4.0 AND BSD-2-Clause"`; add SCOWL's identifier as read from the actual Copyright file in Step 2 — do not guess it from this plan.

`NOTICE` and `README.md`: a paragraph naming SCOWL, the release, and what the list is for.

- [ ] **Step 5: Add the loader, beside the data it reads**

In `packages/denckring-en-data/src/denckring_en_data/__init__.py`, beside `noun_list()` and `gloss_table()`:

```python
GRADED_WORDS_PATH = Path(str(files("denckring_en_data") / "data" / "graded_words.txt.gz"))


@lru_cache(maxsize=1)
def graded_words() -> Mapping[str, int]:
    """Word to SCOWL size band, from the vendored graded list.

    Unlike `known_words()`, this is not a union of two lists built for other
    purposes: it is one list whose whole point is that its entries are ordered by
    commonness. `known_words()` stays exactly as it is — `semordnilap` and
    `charade` ask membership, and are right to keep asking the broad oracle ADR
    0015 describes.
    """
    table: dict[str, int] = {}
    with gzip.open(GRADED_WORDS_PATH, mode="rt", encoding="utf-8") as handle:
        for line in handle:
            word, _, band = line.rstrip("\n").partition("\t")
            if band:
                table[word] = int(band)
    return table
```

This is a plain module-level loader, not a pack method and not a capability — Task 5 adds those. It lives here because Step 6's tests cannot run without it, and because the loader belongs beside the data file it reads, as `noun_list()` and `gloss_table()` already do.

- [ ] **Step 6: Test the shipped data**

```python
def test_the_graded_list_ships_the_words_the_search_needs() -> None:
    """The five words the chapter turns on, and the four it must have dropped."""
    graded = graded_words()
    for word in ("room", "dirty", "silent", "listen", "tinsel"):
        assert word in graded, f"{word} missing: the famous covers are unreachable"
    for surname in ("dority", "romito", "stinel", "sutphen"):
        assert surname not in graded, (
            f"{surname} present: proper names are what made the old oracle unrankable"
        )


def test_common_words_sit_in_lower_bands_than_rare_ones() -> None:
    """SCOWL's numbering runs backwards from intuition: larger means less common.
    The whole ranking rests on this, so it is asserted rather than assumed."""
    graded = graded_words()
    assert graded["room"] < 60
    assert graded["dirty"] < 60


def test_the_shipped_counts_match_the_metadata() -> None:
    """A silent corpus change fails loudly instead of drifting unnoticed — the
    same guard `denckring-de-data` puts on its two files."""
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert len(graded_words()) == metadata["counts"]["graded_words.txt.gz"]
```

- [ ] **Step 7: Run the gate and commit**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
git add packages/denckring-en-data/scripts/build_graded_words.py \
        packages/denckring-en-data/src/denckring_en_data/__init__.py \
        packages/denckring-en-data/src/denckring_en_data/data/graded_words.txt.gz \
        packages/denckring-en-data/src/denckring_en_data/data/metadata.json \
        packages/denckring-en-data/LICENSE-SCOWL packages/denckring-en-data/NOTICE \
        packages/denckring-en-data/pyproject.toml packages/denckring-en-data/README.md \
        tests/test_lang_en_data.py
git commit -m "feat: vendor SCOWL's graded word list into denckring-en-data"
```

---

### Task 5: The `lexicon.graded_words` capability

**Files:**
- Modify: `src/denckring/lang/base.py:23` (constants), and `BasePack`
- Modify: `src/denckring/core/protocol.py:206` (the `LanguagePack` protocol)
- Modify: `packages/denckring-en-data/src/denckring_en_data/__init__.py`
- Test: `tests/test_lang_en_data.py`, `tests/test_capabilities.py`

**Interfaces:**
- Consumes: `data/graded_words.txt.gz` from Task 4
- Produces: `GRADED_WORDS = "lexicon.graded_words"`; `LanguagePack.graded_words(self) -> Mapping[str, int]`

- [ ] **Step 1: Write the failing test**

```python
def test_a_pack_without_the_capability_refuses_rather_than_approximating() -> None:
    """ADR 0004's rule. German's Wikidata list is flat, so it cannot answer this
    question and must not pretend to — a flat list would rank every cover equally
    and the search would be back where it started."""
    with pytest.raises(MissingCapability):
        GermanPack().graded_words()


def test_graded_words_is_a_separate_capability_from_words() -> None:
    """ADR 0015: one capability per question the lexicon is asked. "Is this a
    word" and "give me the words, with how common each is" are different
    questions, and a pack can honestly answer the first and not the second."""
    assert GRADED_WORDS != WORDS
    assert GRADED_WORDS in EnglishDataPack.capabilities
    assert GRADED_WORDS not in GermanDataPack.capabilities
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_capabilities.py -k graded`
Expected: FAIL — `GRADED_WORDS` is not defined.

- [ ] **Step 3: Implement**

In `src/denckring/lang/base.py`, beside `WORDS`:

```python
GRADED_WORDS = "lexicon.graded_words"
```

On `BasePack`:

```python
    def graded_words(self) -> Mapping[str, int]:
        """Every word the lexicon knows, with how common it is.

        A `Mapping`, where `nouns()` is a `Sequence`: N+7 indexes into the noun
        list positionally, so its order is load-bearing, while nothing indexes
        into this one. The anagram search needs band *lookup* and builds its own
        letter-keyed index over the keys, so a mapping is the shape that matches
        the question being asked.

        Values are SCOWL size bands, and **larger means less common** — 60 is the
        largest band SCOWL is confident carries no misspellings. A caller ranking
        by this sorts ascending.

        Separate from `lexicon.words` because ADR 0015's rule is one capability
        per question, and "is this a word" is answerable by a pack that cannot
        answer this one.
        """
        raise MissingCapability(DIRECT_CALL, self.lang, GRADED_WORDS)
```

Add `def graded_words(self) -> Mapping[str, int]: ...` to the `LanguagePack` protocol in `protocol.py`, beside `nouns`.

In `packages/denckring-en-data/src/denckring_en_data/__init__.py`, `graded_words()` already exists — Task 4 added it beside the data file it reads. Task 5 only exposes it as a capability:

```python
    def graded_words(self) -> Mapping[str, int]:
        return graded_words()
```

on `EnglishDataPack`, and `GRADED_WORDS` added to its `capabilities` frozenset.

Do **not** add anything to `GermanDataPack`. Its Wikidata list is flat, so it cannot answer this question, and ADR 0004's rule is that a pack whose capability is undeclared must raise rather than approximate. The inherited `BasePack.graded_words` does exactly that.

- [ ] **Step 4: Run to verify it passes, then the gate**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring status
```

Expected: green. `status` should still read `154 · 128 · 119 · 119 · 26` — no row declares the new capability yet, so nothing moves.

- [ ] **Step 5: Commit**

```bash
git add src/denckring/lang/base.py src/denckring/core/protocol.py \
        packages/denckring-en-data/src/denckring_en_data/__init__.py \
        tests/test_capabilities.py tests/test_lang_en_data.py
git commit -m "feat: lexicon.graded_words, the question a flat word list cannot answer"
```

---

### Task 6: The anagram multi-cover search

**Files:**
- Modify: `src/denckring/procedures/anagram.py`
- Modify: `src/denckring/data/catalogue.yaml` (the `anagram` row's `apply_requires`)
- Test: `tests/test_anagram.py`

**Interfaces:**
- Consumes: `Candidate`/`plain` (Task 3), `graded_words()` (Task 5)
- Produces: nothing later tasks depend on

- [ ] **Step 1: Write the failing test — the one the whole chapter is for**

```python
def test_dormitory_yields_dirty_room_and_ranks_it_above_the_junk() -> None:
    """The assertion the chapter exists to make true.

    `room dirty` was always reachable — it is one of sixty-five two-word covers
    over the old oracle — and the search was never the problem. What was missing
    was any way to tell it from `morty dior`, which the old oracle rated equally.

    Asserts the spec's claim and not a stronger one: present, and ranked above
    the named junk cover. Demanding it rank strictly first would fail if some
    third cover's least-common word were commoner than `dirty`, which would not
    make the ranking wrong.
    """
    texts = Anagram().produce("dormitory", lang="en", max_results=100).texts
    famous = {"room dirty", "dirty room"}
    assert famous & set(texts), f"the famous cover is unreachable: {texts[:10]}"
    junk = [t for t in texts if set(t.split()) == {"morty", "dior"}]
    if junk:
        best = min(texts.index(t) for t in famous & set(texts))
        assert best < texts.index(junk[0]), "ranked a surname cover above the famous one"


def test_astronomer_no_longer_returns_itself() -> None:
    """The reported defect. `astronomer` is a noun, so under a noun-only search
    it was the longest cover of its own letters and the guard refused it."""
    assert Anagram().apply("astronomer", lang="en") != "astronomer"


def test_every_cover_uses_exactly_the_source_letters() -> None:
    """The round-trip property in miniature, pinned at row level: the search may
    reorder and rank, but it may never lose or invent a letter."""
    procedure = Anagram()
    for candidate in procedure.produce("dormitory", lang="en").texts:
        assert procedure.check(candidate, lang="en", source="dormitory").satisfied


def test_candidates_carry_the_band_they_were_ranked_by() -> None:
    """The concrete use ADR 0027 exists for. Without it the order is an assertion
    the caller has to take on trust."""
    for candidate in Anagram().produce("dormitory", lang="en").candidates:
        assert "max_band" in candidate.metrics
        assert candidate.metrics["words"] == float(len(candidate.text.split()))


def test_the_ranking_keys_are_in_the_order_the_spec_names() -> None:
    """Fewest words first, then lowest maximum band. Asserted as the sort key
    rather than by naming winners, so it keeps holding when the lexicon changes."""
    candidates = Anagram().produce("dormitory", lang="en").candidates
    keys = [(c.metrics["words"], c.metrics["max_band"]) for c in candidates]
    assert keys == sorted(keys)


def test_the_node_budget_truncates_deterministically() -> None:
    """A wall-clock budget would make this machine-dependent, and the row is
    `deterministic: true`. Two runs at the same budget must agree exactly,
    including about having stopped early."""
    first = Anagram().produce("astronomer", lang="en", max_nodes=500)
    second = Anagram().produce("astronomer", lang="en", max_nodes=500)
    assert first.texts == second.texts
    assert first.truncated == second.truncated


def test_min_word_length_refuses_orphan_letters() -> None:
    """The direct answer to single letters passing as words."""
    for candidate in Anagram().produce("dormitory", lang="en", min_word_length=3).texts:
        assert all(len(word) >= 3 for word in candidate.split())
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_anagram.py`
Expected: FAIL — `DegenerateOutput` on `dormitory`, and `max_nodes` is not a parameter.

- [ ] **Step 3: Fix the catalogue row and the false comment**

In `src/denckring/data/catalogue.yaml`, the `anagram` row:

```yaml
    apply_requires:
      - lexicon.graded_words
```

In `anagram.py`, the `_produce` docstring currently says `lexicon.words` is declared on `apply_requires`. That sentence's *reasoning* is right and stays — `apply_requires` rather than `requires`, because ADR 0002 makes `apply` the optional half. Only the capability name was ever wrong, and the code was wronger still: it called `pack.nouns()`. Correct both:

```python
        `lexicon.graded_words` is declared on the catalogue row's `apply_requires`,
        not its `requires`: the latter gates `check` too, and `check` has always
        run on core alone. ADR 0002 makes `apply` the optional half, and
        `apply_requires` is how the optional half states its own cost.

        The row declared `lexicon.words` and the code called `pack.nouns()` —
        neither the capability it named nor the one it used was the one it wanted.
        Nouns are why `astronomer` returned itself: a source word that is itself a
        noun is the longest cover of its own letters. Narrowing to nouns could not
        have been the fix either, since `dirty` and `silent` are not nouns.
```

- [ ] **Step 4: Implement the search**

Add to `AnagramApplyParams`:

```python
class AnagramApplyParams(AnagramParams, ApplyParams):
    max_words: int = Field(
        default=3,
        ge=1,
        description="How many words a cover may use.",
    )
    min_word_length: int = Field(
        default=2,
        ge=1,
        description="Shortest word a cover may use, which is what keeps orphan letters out.",
    )
    # `le=60` matches `MAX_BAND` in the build script: nothing above band 60 is
    # shipped, so without a ceiling `max_size=70` would silently mean 60 — a
    # parameter promising more than the data delivers, which is the defect class
    # ADR 0015 exists to prevent. Raising the ceiling means raising both.
    max_size: int = Field(
        default=60,
        ge=1,
        le=60,
        description=(
            "Largest SCOWL size band to draw words from. Larger bands are less "
            "common words; 60 is the largest SCOWL states it is confident carries "
            "no misspellings, and the largest this package ships."
        ),
    )
    # Measured against the shipped list at `max_words=3`, `min_word_length=2`:
    # `listen` exhausts in 2,994 nodes, `dormitory` in 7,958, `astronomer` in
    # 747,769 (0.92s). A million is the smallest round value that leaves the
    # worst of the three untruncated, with about 34% headroom. Work per node is
    # near-constant, so this is also what bounds wall-clock time — `MAX_LETTERS`
    # does not: an unbounded search over a seventeen-letter word runs for minutes.
    max_nodes: int = Field(
        default=1_000_000,
        ge=1,
        description="Search nodes to visit before stopping and reporting truncation.",
    )
```

Every one has a default, deliberately: a required parameter here would move `anagram` into `PARAMETER_GATED` and out of the round-trip property's reach, silently.

Replace `_longest_word` — the greedy walk over `pack.nouns()` — entirely, and replace `_produce`'s body:

```python
    def _produce(self, text: str, pack: LanguagePack, params: AnagramApplyParams) -> Produced:
        letters = sorted(ch for _, ch in letter_spans(text, pack, fold=params.fold_diacritics))
        if len(letters) > self.MAX_LETTERS:
            raise InputTooLong(self.id, len(letters), self.MAX_LETTERS)
        source = Counter(letters)

        # Filtered to words that fit before the walk begins, not inside it: the
        # pool for `astronomer` is 992 words out of the whole lexicon, and testing
        # containment once per word beats testing it once per node.
        graded = pack.graded_words()
        pool = sorted(
            word
            for word, band in graded.items()
            if band <= params.max_size
            and len(word) >= params.min_word_length
            and not Counter(word) - source
        )

        covers: list[tuple[int, int, str]] = []
        # A list, not an int, because `walk` closes over it and rebinding an int
        # inside a closure would need `nonlocal` in every branch that spends one.
        budget = [params.max_nodes]

        def walk(remaining: Counter[str], chosen: list[str], start: int) -> None:
            if not sum(remaining.values()):
                bands = [graded[word] for word in chosen]
                covers.append((len(chosen), max(bands), " ".join(chosen)))
                return
            if len(chosen) == params.max_words:
                return
            # `start` and not `start + 1`: a cover may legitimately use the same
            # word twice when the letters allow it. Not descending below `start`
            # is what keeps `room dirty` and `dirty room` from both being found —
            # they are one cover, and the ranking picks its spelling.
            for index in range(start, len(pool)):
                if budget[0] <= 0:
                    return
                budget[0] -= 1
                word = pool[index]
                if Counter(word) - remaining:
                    continue
                walk(remaining - Counter(word), [*chosen, word], index)

        walk(source, [], 0)

        # Fewest words, then commonest word last — SCOWL's bands run backwards
        # from intuition, so a cover is judged by its *least* common word (its
        # maximum band) and lower wins. Alphabetical last, from Dewdney, so the
        # order is total and the row stays `deterministic: true`.
        covers.sort()
        return Produced(
            candidates=[
                Candidate(text=text, metrics={"words": float(count), "max_band": float(band)})
                for count, band, text in covers
            ],
            truncated=budget[0] <= 0,
        )
```

Note `letter_spans` and `letter_counts` are unchanged and `_check` is untouched — the checker was never the defect.

Replace `MAX_LETTERS`'s comment, which justifies the cap in terms of the greedy walk being replaced:

```python
    #: The letter count past which the cover search is not worth starting. The
    #: candidate pool grows with the number of lexicon words that fit inside the
    #: remaining letters, and a real anagram of a paragraph is not something any
    #: depth-bounded search finds.
    #:
    #: This is not what bounds the search's cost — `max_nodes` is, and measurably:
    #: an unbounded search over a seventeen-letter input runs for minutes, and 17
    #: is well inside this cap. What this cap does is refuse the inputs where even
    #: a budgeted search would return nothing worth reading. See ADR 0028 on why
    #: the budget counts nodes and not seconds.
    MAX_LETTERS = 60
```

- [ ] **Step 5: Verify the budget actually reports, rather than merely existing**

`truncated=budget[0] <= 0` is one line and easy to get backwards. Confirm both directions by hand before trusting the test:

```bash
uv run python -c "
from denckring.procedures.anagram import Anagram
tight = Anagram().produce('astronomer', lang='en', max_nodes=500)
loose = Anagram().produce('astronomer', lang='en')
print('tight:', tight.truncated, len(tight.candidates))
print('loose:', loose.truncated, len(loose.candidates))
"
```

Expected: `tight: True`, `loose: False`. A run where both say `True` means the default budget is too small and its 200,000 needs re-measuring (spec, W3); where both say `False`, the flag is not wired to the spine.

- [ ] **Step 6: Run to verify it passes, then the whole gate**

```bash
uv run pytest -q tests/test_anagram.py
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
```

Expected: `119 procedures · 353 passed · 0 failed`, `154 · 128 · 119 · 119 · 26`.

Then confirm the reported defect by hand, which is how the developer will:

```bash
echo -n "astronomer" | uv run denckring apply anagram -
echo -n "dormitory"  | uv run denckring apply anagram - --json
```

- [ ] **Step 7: Commit**

```bash
git add src/denckring/procedures/anagram.py src/denckring/data/catalogue.yaml tests/test_anagram.py
git commit -m "feat: anagram searches the graded lexicon and ranks what it finds"
```

---

### Task 7: Record the chapter

**Files:**
- Create: `docs/adr/0028-the-graded-lexicon.md`
- Modify: `README.md`
- Modify: `docs/expansion_ideas/anagram-generation-research.md`

- [ ] **Step 1: Write ADR 0028**

The problem: the shipped oracle cannot rank, ADR 0015 said so before the caller existed, and the anagram generator is the caller that inherits it hardest.

Consequences that admit costs:
- `denckring-en-data` grows by the shipped list, so a user who wanted syllable counts now downloads a word list too — the alternative was a fourth distribution, and ADR 0013's quarantine rationale did not apply because SCOWL's licence is compatible;
- SCOWL's bands are coarse editorial size classes, not corpus frequencies, so the ranking is as good as a spell-checker's judgement and no better;
- German cannot claim the capability, so the asymmetry between the two packs is now visible in `denckring status` rather than hidden;
- SCOWL carries UKACD's verbatim-notice term, which `LICENSE-SCOWL` discharges — and which the research note wrongly said choosing SCOWL avoided.

- [ ] **Step 2: Correct the research note**

`docs/expansion_ideas/anagram-generation-research.md` is a research note, not a spec, and stays. Add a status line at the top pointing at ADR 0028 and this plan, and fix the two claims the work disproved: UKACD's verbatim term rides along inside SCOWL rather than being avoided by it, and the band-95 description. Do not rewrite the measurements — they reproduced.

- [ ] **Step 3: Update the README**

Whatever it says about `anagram` or about English data now under-describes both. Never edit `docs/index.md`; it is generated from the README and gitignored.

- [ ] **Step 4: Final gate, then commit**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
git add docs/adr/0028-the-graded-lexicon.md README.md docs/expansion_ideas/anagram-generation-research.md
git commit -m "docs: ADR 0028, the graded lexicon"
```

---

## Spec coverage

| Spec section | Task |
|---|---|
| W0 test net — derandomize, draw the seed, fix fallout | 1 |
| W1 `Production` carries candidates | 2, 3 |
| W1 ADR amending 0026 | 3 (Step 7) |
| W2 SCOWL build, vendored data, licence artefacts | 4 |
| W2 `lexicon.graded_words` capability | 5 |
| W2 `apply_requires` fix + false docstring | 6 (Step 3) |
| W3 search, params, ranking, node budget | 6 |
| W3 `MAX_LETTERS` comment rewrite | 6 (Step 4) |
| Testing — `room dirty` ranked first | 6 (Step 1) |
| Testing — determinism under truncation | 6 (Step 1) |
| Testing — coverage gap unchanged | 6 (Step 4, every param defaulted) |
| Decisions — node budget not wall-clock | 6, ADR 0028 |
| Decisions — `max_size=60` sourced | 4, 6 |
| Out of scope — spelling variants, German, paragram's ranking, Spec B | not implemented, recorded in ADR 0028 |
