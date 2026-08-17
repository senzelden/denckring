# Syllabic Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the seven unbuilt catalogued rows whose constraint is measured in syllables, taking `implemented` from 79 to 86, and repair the two prosody defects that make four of them uncheckable today.

**Architecture:** Four changes to the shared `core/prosody.py` land first, because `dactylic_hexameter`, `elegiac_couplet`, `sapphic_stanza` and `alcaic_stanza` cannot be written against the current machinery at all. The three stanza-shape rows (`double_dactyl`, `renga`, `haibun`) then compose the existing `syllable_count` helpers with the new per-line scanner. No procedure reimplements scansion; every one assembles it from shared parts, the way `rhyme_scheme.form_report` already does.

**Tech Stack:** Python 3.11+, Pydantic v2, hypothesis, pytest, ruff, mypy --strict, uv.

**Spec:** `docs/superpowers/specs/2026-08-17-syllabic-batch-design.md`

## Global Constraints

- Every procedure owes FOUR files, landing in one commit or the parametrised invariants fail: `src/denckring/procedures/<id>.py`, `tests/strategies/<id>.py` exporting `satisfying()` and `violating()` (both returning `CaseStrategy`), `src/denckring/eval/fixtures/golden/<id>.yaml`, and `tests/test_<id>.py`.
- `CaseStrategy` is a hypothesis strategy of `(text, params_dict)` tuples. Import it as `from strategies import CaseStrategy`.
- ADR 0002: `check` is mandatory, `apply` optional. All seven rows are `kind: restrictive`; **no `apply` anywhere in this batch**.
- ADR 0007: one module per procedure.
- ADR 0009: diacritic folding is a procedure parameter, never a data-layer policy.
- `requires` in `src/denckring/data/catalogue.yaml` **gates `check`, not just `apply`**. A capability used but undeclared is a latent crash; one declared but unused raises `MissingCapability` for a caller who needed nothing. Verify every row against what its checker actually calls.
- Golden fixtures record what the checker **actually returns**, never what it ideally should.
- Capability constants live in `src/denckring/lang/base.py` (`PHONEMES = "phonemes"`, `SYLLABLES`, `TOKENS`).
- `mypy --strict`, `ruff check src tests`, `ruff format --check src tests` all clean.
- **No vacuous verdicts.** An empty text must be unsatisfied *and* carry violations. A report that is unsatisfied while listing no violation is a defect — it shipped twice in this project before being caught.
- **Strategies must reach every violation rule they can.** A `violating()` producing only one rule is a defect; every draw must be genuinely rejected.
- Stress notation: `1` stressed, `0` unstressed, `?` anceps/free.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/denckring/core/prosody.py` (modify) | All shared scansion. Gains anceps in `_fits`, `word_stress`, `MetreResult`, `line_metre`, `stanza_violations`, `feet`. |
| `src/denckring/procedures/rhyme_scheme.py` (modify) | Sole existing caller of `metre_violations`; updated for the new return type. |
| `tests/test_prosody.py` (modify) | Direct tests for every new helper. |
| `src/denckring/procedures/<id>.py` × 7 | One checker each. |
| `tests/strategies/<id>.py` × 7 | `satisfying()` / `violating()`. |
| `src/denckring/eval/fixtures/golden/<id>.yaml` × 7 | Recorded verdicts. |
| `tests/test_<id>.py` × 7 | Unit tests. |
| `src/denckring/data/catalogue.yaml` (modify) | `requires` and `notes` per row. |

---

### Task 1: Prosody repairs — anceps and out-of-dictionary words

**Files:**
- Modify: `src/denckring/core/prosody.py`
- Modify: `src/denckring/procedures/rhyme_scheme.py:53-58`
- Test: `tests/test_prosody.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `word_stress(word: str, pack: LanguagePack) -> tuple[list[str], bool]`
  - `class MetreResult(NamedTuple): violations: list[Violation]; good: int; total: int; estimated: int`
  - `metre_violations(line: str, pack: LanguagePack, pattern: str, offset: int) -> MetreResult` — **return type changed from a plain 3-tuple**

- [ ] **Step 1: Write the failing test for anceps in a pattern**

Add to `tests/test_prosody.py`:

```python
from denckring.core.prosody import FREE, _fits


def test_anceps_in_the_pattern_accepts_any_mark() -> None:
    """`?` on the pattern side is the classical anceps: the position takes
    either. Before this, `?` was honoured only on the word side, so a pattern
    written with anceps rejected every fixed-stress word at that position."""
    assert _fits("1", "?")
    assert _fits("0", "?")
    assert _fits("101", "10?")


def test_a_free_monosyllable_still_takes_whatever_the_line_needs() -> None:
    """The pre-existing word-side meaning must not change."""
    assert _fits(FREE, "1")
    assert _fits(FREE, "0")


def test_fits_still_rejects_a_real_mismatch() -> None:
    assert not _fits("10", "01")
    assert not _fits("10", "100")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_prosody.py::test_anceps_in_the_pattern_accepts_any_mark -v`
Expected: FAIL — `assert _fits("1", "?")` is currently `False`.

- [ ] **Step 3: Add anceps to `_fits`**

Replace `_fits` in `src/denckring/core/prosody.py:23-26`:

```python
def _fits(stress: str, wanted: str) -> bool:
    """`?` means "either" on both sides.

    On the word side it is a monosyllable taking whatever beat the line needs.
    On the pattern side it is the classical anceps — the position that may be
    long or short — which sapphics and alcaics both have.
    """
    return len(stress) == len(wanted) and all(
        want == FREE or mark in (FREE, want)
        for mark, want in zip(stress, wanted, strict=True)
    )
```

- [ ] **Step 4: Run to verify all three pass**

Run: `uv run pytest tests/test_prosody.py -v -k fits or anceps or monosyllable`
Expected: PASS.

- [ ] **Step 5: Write the failing test for out-of-dictionary words**

Add to `tests/test_prosody.py`:

```python
import pytest

from denckring.core.errors import MissingCapability
from denckring.core.prosody import word_stress
from denckring.lang import get_pack


def test_a_known_word_reports_its_real_patterns() -> None:
    patterns, exact = word_stress("forest", get_pack("en"))
    assert exact
    assert "10" in patterns


def test_an_unknown_word_is_scanned_for_length_but_constrains_no_beat() -> None:
    """`hemlocks` is an ordinary English noun absent from CMUdict. Before this,
    it raised MissingCapability and aborted the whole check — naming a
    capability the pack actually provides."""
    patterns, exact = word_stress("hemlocks", get_pack("en"))
    assert not exact
    assert patterns == ["??"]


def test_a_pack_genuinely_lacking_phonemes_still_raises() -> None:
    """The repair must not swallow the real capability error it is named for."""
    from denckring.lang.en import EnglishPack

    with pytest.raises(MissingCapability):
        word_stress("forest", EnglishPack())
```

- [ ] **Step 6: Run to verify it fails**

Run: `uv run pytest tests/test_prosody.py -v -k word_stress or unknown_word or known_word`
Expected: FAIL with `ImportError: cannot import name 'word_stress'`.

- [ ] **Step 7: Implement `word_stress`**

Add to `src/denckring/core/prosody.py`, after the `MAX_COMBINATIONS` constant:

```python
def word_stress(word: str, pack: LanguagePack) -> tuple[list[str], bool]:
    """Every stress pattern a word can take, and whether they are known.

    Mirrors `pack.syllable_count`'s `(value, exact)` contract, for the same
    reason: a pronouncing dictionary does not carry every word, and an unknown
    word is a normal event in verse rather than an exceptional one. The
    dictionary raises `MissingCapability` for a word it lacks — naming a
    capability the pack does provide — so that case is caught here and turned
    into a scan that measures the word's length while constraining no beat.

    A pack that genuinely lacks `phonemes` still raises, which is what the
    exception is for.
    """
    if PHONEMES not in pack.capabilities:
        raise MissingCapability(f"<word {word!r}>", pack.lang, PHONEMES)
    try:
        return pack.stress_patterns(word), True
    except MissingCapability:
        count, _ = pack.syllable_count(word)
        return [FREE * max(count, 1)], False
```

Add the imports at the top of the file:

```python
from denckring.core.errors import MissingCapability
from denckring.lang.base import PHONEMES
```

- [ ] **Step 8: Run to verify the three word_stress tests pass**

Run: `uv run pytest tests/test_prosody.py -v -k word_stress or unknown_word or known_word or lacking_phonemes`
Expected: PASS.

If `test_an_unknown_word_...` fails on the exact value `["??"]`, the heuristic
gives `hemlocks` a different syllable count than 2. Fix the **assertion** to the
count the heuristic actually returns — do not change `word_stress` to force it.

- [ ] **Step 9: Write the failing test for the estimated count reaching the caller**

```python
def test_metre_violations_reports_how_many_words_were_estimated() -> None:
    """`estimated_words` is what keeps a heuristic honest — the syllabic
    procedures already carry it, and the metrical ones must too."""
    from denckring.core.prosody import metre_violations

    pack = get_pack("en")
    known = metre_violations("the forest", pack, "?10", 0)
    assert known.estimated == 0

    unknown = metre_violations("the hemlocks", pack, "???", 0)
    assert unknown.estimated == 1
```

- [ ] **Step 10: Run to verify it fails**

Run: `uv run pytest tests/test_prosody.py::test_metre_violations_reports_how_many_words_were_estimated -v`
Expected: FAIL — `metre_violations` returns a tuple with no `.estimated`.

- [ ] **Step 11: Change `metre_violations` to return a `MetreResult`**

Add the NamedTuple above `metre_violations` in `src/denckring/core/prosody.py`:

```python
class MetreResult(NamedTuple):
    """A scan's outcome. Named rather than a bare tuple because it grew a
    fourth field, and `PatternResult` in `syllable_count` sets the precedent.
    """

    violations: list[Violation]
    good: int
    total: int
    estimated: int
```

Import `NamedTuple` from `typing` at the top of the file.

Then in `metre_violations`, replace the `pack.stress_patterns(word)` lookup and
every `return` so the function reads:

```python
def metre_violations(line: str, pack: LanguagePack, pattern: str, offset: int) -> MetreResult:
    """Check a line against a stress pattern, treating `?` as satisfiable.

    Because each free syllable is independent of every other, this is a linear
    scan rather than a search: a fixed syllable landing on the wrong beat is the
    only way to fail. The violation names the word rather than the syllable
    index, because the word is what a writer can act on.
    """
    tokens = pack.tokenize(line)
    combinations = 1
    words: list[tuple[str, list[str]]] = []
    estimated = 0
    for word in tokens:
        forms, exact = word_stress(word, pack)
        if not exact:
            estimated += 1
        combinations *= max(len(forms), 1)
        words.append((word, forms if combinations <= MAX_COMBINATIONS else forms[:1]))

    fitted = _scan(words, pattern, 0, 0)
    if fitted is not None:
        return MetreResult([], len(words), max(len(words), 1), estimated)

    violations: list[Violation] = []
    # No combination fits. Report against the first pronunciation of each word,
    # which is the reading a writer is most likely to have had in mind.
    first = [(word, forms[0]) for word, forms in words]
    actual = "".join(stress for _, stress in first)
    if len(actual) != len(pattern):
        violations.append(
            Violation(
                rule="wrong_line_length",
                offset=offset,
                found=f"{len(actual)} syllables",
                expected=f"{len(pattern)} syllables",
            )
        )
        return MetreResult(violations, 0, 1, estimated)

    matched = 0
    position = 0
    for word, stress in first:
        wanted = pattern[position : position + len(stress)]
        if _fits(stress, wanted):
            matched += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_stress", offset=offset, found=f"{word} ({stress})", expected=wanted
                )
            )
        position += len(stress)
    return MetreResult(violations, matched, max(len(words), 1), estimated)
```

- [ ] **Step 12: Update the only existing caller**

In `src/denckring/procedures/rhyme_scheme.py`, replace lines 53-58:

```python
    if metre is not None:
        for offset, line in line_spans(text):
            result = metre_violations(line, pack, metre, offset)
            violations += result.violations
            good += result.good
            total += result.total
```

`form_report`'s own signature and return type are unchanged — it still returns
`tuple[list[Violation], int, int]`. The estimated count is deliberately not
threaded through it: no rhymed form in this batch reports it, and batch C will
decide how it surfaces there.

- [ ] **Step 13: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS. Baseline before this task is 2036; this task adds 6 tests.

Every `rhyme_scheme`, `sonnet`-adjacent and metre test must still pass — if any
fails, the return-type change missed a caller. Find it with
`uv run grep -rn "metre_violations" src tests`.

- [ ] **Step 14: Lint and type-check**

```bash
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
```

- [ ] **Step 15: Commit**

```bash
git add src/denckring/core/prosody.py src/denckring/procedures/rhyme_scheme.py tests/test_prosody.py
git commit -m "fix: honour anceps in metre patterns and tolerate words CMUdict lacks"
```

---

### Task 2: Per-line patterns and substitutable feet

**Files:**
- Modify: `src/denckring/core/prosody.py`
- Test: `tests/test_prosody.py`

**Interfaces:**
- Consumes: `MetreResult`, `metre_violations` from Task 1.
- Produces:
  - `feet(units: Sequence[Sequence[str]]) -> list[str]`
  - `line_metre(line: str, pack: LanguagePack, options: Sequence[str], offset: int) -> MetreResult`
  - `stanza_violations(text: str, pack: LanguagePack, patterns: Sequence[Sequence[str]]) -> MetreResult`

- [ ] **Step 1: Write the failing test for `feet`**

```python
from denckring.core.prosody import feet

DACTYL = ("100", "11")
HEXAMETER = [DACTYL, DACTYL, DACTYL, DACTYL, ("100",), ("11", "10")]


def test_feet_expands_every_substitution() -> None:
    """A dactyl may be a spondee, so a metre is a set of readings, not one."""
    patterns = feet(HEXAMETER)
    assert len(patterns) == 32
    assert len(set(patterns)) == 32
    assert min(len(p) for p in patterns) == 13
    assert max(len(p) for p in patterns) == 17


def test_feet_of_a_single_option_is_one_pattern() -> None:
    assert feet([("100",), ("11",)]) == ["10011"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_prosody.py -v -k feet`
Expected: FAIL with `ImportError: cannot import name 'feet'`.

- [ ] **Step 3: Implement `feet`**

```python
def feet(units: Sequence[Sequence[str]]) -> list[str]:
    """Every pattern a line of substitutable feet can take.

    Classical metre substitutes: a dactyl may be a spondee, so a hexameter is
    thirty-two readings rather than one. `feet` enumerates them, and the set is
    bounded by construction — no metre in the catalogue has more than six feet.
    """
    return ["".join(combination) for combination in itertools.product(*units)]
```

Add `import itertools` and `from collections.abc import Sequence` at the top.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_prosody.py -v -k feet`
Expected: PASS.

- [ ] **Step 5: Write the failing test for `line_metre`**

```python
from denckring.core.prosody import line_metre


def test_a_line_satisfies_if_it_fits_any_reading() -> None:
    pack = get_pack("en")
    # "the forest" is ?10 — fits the second option, not the first.
    result = line_metre("the forest", pack, ["111", "?10"], 0)
    assert not result.violations


def test_the_closest_reading_supplies_the_violations() -> None:
    """Reporting all thirty-two failures would tell a writer nothing. The
    candidate that matched most words is the one scansion worth showing."""
    pack = get_pack("en")
    result = line_metre("the forest primeval", pack, ["000000", "?10010"], 0)
    assert result.violations
    # Only the closest candidate's violations, not both candidates' combined.
    assert len(result.violations) <= 3
```

- [ ] **Step 6: Run to verify it fails**

Run: `uv run pytest tests/test_prosody.py -v -k line_metre or closest_reading or any_reading`
Expected: FAIL with `ImportError: cannot import name 'line_metre'`.

- [ ] **Step 7: Implement `line_metre`**

```python
def line_metre(
    line: str, pack: LanguagePack, options: Sequence[str], offset: int
) -> MetreResult:
    """Scan a line against several acceptable readings, reporting the closest.

    A substitutable foot makes a metre a set rather than a single pattern, so
    the line satisfies if it fits any member. When none fits, the violations
    come from the candidate that matched the most words — the writer is told
    about one scansion rather than thirty-two.
    """
    best: MetreResult | None = None
    for pattern in options:
        result = metre_violations(line, pack, pattern, offset)
        if not result.violations:
            return result
        if best is None or result.good > best.good:
            best = result
    if best is None:
        raise ValueError("line_metre needs at least one pattern")
    return best
```

- [ ] **Step 8: Run to verify it passes**

Run: `uv run pytest tests/test_prosody.py -v -k line_metre or closest_reading or any_reading`
Expected: PASS.

- [ ] **Step 9: Write the failing test for `stanza_violations`**

```python
from denckring.core.prosody import stanza_violations


def test_each_line_is_checked_against_its_own_pattern() -> None:
    """Sapphics and alcaics change shape from line to line, which a single
    pattern applied to every line cannot express."""
    pack = get_pack("en")
    text = "the forest\nforest"
    result = stanza_violations(text, pack, [["?10"], ["10"]])
    assert not result.violations


def test_a_line_count_mismatch_is_reported_once() -> None:
    pack = get_pack("en")
    result = stanza_violations("the forest", pack, [["?10"], ["10"]])
    assert [v.rule for v in result.violations] == ["wrong_line_count"]
    assert not result.violations[0].offset


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    """No vacuous verdicts: a report with no violations behind it is a defect."""
    pack = get_pack("en")
    result = stanza_violations("", pack, [["?10"]])
    assert result.violations
    assert result.good < result.total
```

- [ ] **Step 10: Run to verify it fails**

Run: `uv run pytest tests/test_prosody.py -v -k stanza`
Expected: FAIL with `ImportError: cannot import name 'stanza_violations'`.

- [ ] **Step 11: Implement `stanza_violations`**

```python
def stanza_violations(
    text: str, pack: LanguagePack, patterns: Sequence[Sequence[str]]
) -> MetreResult:
    """Check a stanza whose lines each have their own metre.

    `patterns[i]` is the set of readings acceptable for line `i`. A stanza of
    the wrong length reports `wrong_line_count` and stops — scanning line three
    against line four's pattern would bury the real fault under false ones.
    """
    lines = line_spans(text)
    if len(lines) != len(patterns):
        return MetreResult(
            [
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected=f"{len(patterns)} lines",
                )
            ],
            0,
            1,
            0,
        )

    violations: list[Violation] = []
    good = 0
    total = 0
    estimated = 0
    for (offset, line), options in zip(lines, patterns, strict=True):
        result = line_metre(line, pack, options, offset)
        violations += result.violations
        good += result.good
        total += result.total
        estimated += result.estimated
    return MetreResult(violations, good, max(total, 1), estimated)
```

- [ ] **Step 12: Run the full suite, lint, type-check**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
```

- [ ] **Step 13: Commit**

```bash
git add src/denckring/core/prosody.py tests/test_prosody.py
git commit -m "feat: add per-line metre patterns and substitutable feet"
```

---

### Task 3: `dactylic_hexameter`

**Files:**
- Create: `src/denckring/procedures/dactylic_hexameter.py`
- Create: `tests/strategies/dactylic_hexameter.py`
- Create: `src/denckring/eval/fixtures/golden/dactylic_hexameter.yaml`
- Create: `tests/test_dactylic_hexameter.py`
- Modify: `src/denckring/data/catalogue.yaml` — the `dactylic_hexameter` row

**Interfaces:**
- Consumes: `feet`, `line_metre`, `MetreResult` from Tasks 1-2.
- Produces: `HEXAMETER: list[tuple[str, ...]]` and `PATTERNS: list[str]`, imported by Task 4.

- [ ] **Step 1: Write the failing test**

Create `tests/test_dactylic_hexameter.py`:

```python
"""Dactylic hexameter — six feet, the first four substitutable."""

from denckring import check
from denckring.procedures.dactylic_hexameter import PATTERNS


def test_the_pattern_set_is_the_classical_one() -> None:
    """Feet 1-4 dactyl or spondee, foot 5 dactyl, foot 6 spondee or trochee."""
    assert len(PATTERNS) == 32
    assert min(len(p) for p in PATTERNS) == 13
    assert max(len(p) for p in PATTERNS) == 17


def test_real_hexameter_from_the_literature_is_accepted() -> None:
    """Longfellow's opening line. It contains `hemlocks`, which CMUdict does not
    carry — before the out-of-dictionary repair this raised rather than scanned."""
    report = check(
        "dactylic_hexameter",
        "This is the forest primeval the murmuring pines and the hemlocks",
    )
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]
    assert report.metrics["estimated_words"] >= 1


def test_prose_of_the_right_length_is_rejected() -> None:
    """The whole argument for scanning stress rather than counting syllables: a
    count-only checker cannot tell these two apart."""
    report = check("dactylic_hexameter", "I walked down to the shop this morning to buy a loaf")
    assert not report.satisfied
    assert report.violations


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("dactylic_hexameter", "")
    assert not report.satisfied
    assert report.violations
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_dactylic_hexameter.py -v`
Expected: FAIL — no module `dactylic_hexameter`.

- [ ] **Step 3: Write the checker**

Create `src/denckring/procedures/dactylic_hexameter.py`:

```python
"""Dactylic hexameter — six feet, each a dactyl or a spondee."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import feet, line_metre
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans

#: A dactyl, or the spondee that may stand in for it.
DACTYL = ("100", "11")

#: Feet 1-4 substitute freely. The fifth is fixed as a dactyl: a spondaic fifth
#: exists but is rare enough that accepting it would cost more in false
#: positives than it buys. The sixth is a spondee or, by brevis in longo, a
#: trochee.
HEXAMETER = [DACTYL, DACTYL, DACTYL, DACTYL, ("100",), ("11", "10")]

PATTERNS = feet(HEXAMETER)


class DactylicHexameterParams(BaseModel):
    pass


@register
class DactylicHexameter(BaseProcedure[DactylicHexameterParams]):
    """Scans every line against the thirty-two readings of the hexameter.

    This is the English accentual reading of a quantitative measure: classical
    quantity is vowel length, which English does not have, so stress stands in
    for it as it has since the Renaissance. The caesura is not checked.
    """

    id = "dactylic_hexameter"

    @classmethod
    def params_model(cls) -> type[DactylicHexameterParams]:
        return DactylicHexameterParams

    def _check(
        self, text: str, pack: LanguagePack, params: DactylicHexameterParams
    ) -> Report:
        lines = line_spans(text)
        if not lines:
            return self._report(
                good=0,
                total=1,
                violations=[
                    Violation(
                        rule="wrong_line_count", offset=None, found="0 lines", expected="1 line"
                    )
                ],
                metrics={"lines": 0.0, "estimated_words": 0.0},
            )

        violations: list[Violation] = []
        good = 0
        total = 0
        estimated = 0
        for offset, line in lines:
            result = line_metre(line, pack, PATTERNS, offset)
            violations += result.violations
            good += result.good
            total += result.total
            estimated += result.estimated
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"lines": float(len(lines)), "estimated_words": float(estimated)},
        )
```

- [ ] **Step 4: Run to verify the unit tests pass**

Run: `uv run pytest tests/test_dactylic_hexameter.py -v`
Expected: PASS.

If `test_real_hexameter_from_the_literature_is_accepted` fails, print the
scansion before changing anything:

```bash
uv run python -c "
from denckring.lang import get_pack
from denckring.core.prosody import word_stress
p = get_pack('en')
for w in p.tokenize('This is the forest primeval the murmuring pines and the hemlocks'):
    print(w, word_stress(w, p))
"
```

Then widen the **pattern set** only if the classical form genuinely admits the
reading. Do not relax the checker to make one line pass.

- [ ] **Step 5: Write the strategies**

Create `tests/strategies/dactylic_hexameter.py`:

```python
"""Generators for dactylic hexameter, built from words of known stress."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Each maps to exactly one stress pattern in CMUdict, verified before use.
#: `murmuring` etc. are `100`; `forest` etc. are `10`.
_DACTYL_WORD = st.sampled_from(["murmuring", "beautiful", "carefully", "wonderful"])
_TROCHEE_WORD = st.sampled_from(["forest", "morning", "silver", "garden"])

#: CMUdict marks secondary stress, which this pack renders as `?` — so a
#: "spondee word" reads `1?` rather than `11` and fits the spondee slot through
#: the free second syllable. `shipwreck` is deliberately absent: it is `10`,
#: which does not fit `11`.
_SPONDEE_WORD = st.sampled_from(["daylight", "birthright", "moonlight"])


def _line(dactyls: list[str], close: str) -> str:
    return " ".join([*dactyls, close])


def satisfying() -> CaseStrategy:
    """Five dactyls and a trochee — the commonest reading, and always 17
    syllables, so no substitution ambiguity can creep in."""
    return st.lists(_DACTYL_WORD, min_size=5, max_size=5).flatmap(
        lambda dactyls: _TROCHEE_WORD.map(lambda close: (_line(dactyls, close), {}))
    )


def violating() -> CaseStrategy:
    """Two shapes, so both reachable rules are generated: a line of the wrong
    length, and a line of the right length whose stresses fall wrong."""
    too_short = st.lists(_DACTYL_WORD, min_size=2, max_size=3).map(
        lambda words: (" ".join(words), {})
    )
    wrong_stress = st.lists(_TROCHEE_WORD, min_size=8, max_size=8).map(
        lambda words: (" ".join(words), {})
    )
    return st.one_of(too_short, wrong_stress)
```

All eight words above were verified against CMUdict while this plan was written
— the dactyls return `['100']` and the trochees `['10']`, all exact. If you add
any word of your own, verify it the same way, because a word absent from the
dictionary scans as free and silently drains the test of its point:

```bash
uv run python -c "
from denckring.lang import get_pack
from denckring.core.prosody import word_stress
p = get_pack('en')
for w in ['murmuring','beautiful','carefully','wonderful','forest','morning','silver','garden']:
    print(w, word_stress(w, p))
"
```

Replace any word whose second element is `False` or whose pattern is not the
one the name claims.

- [ ] **Step 6: Run the parametrised strategy test**

Run: `uv run pytest tests/test_strategies.py -q -k dactylic_hexameter`
Expected: PASS — `satisfying()` checks true, `violating()` checks false.

- [ ] **Step 7: Record the golden fixture**

Create `src/denckring/eval/fixtures/golden/dactylic_hexameter.yaml`:

```yaml
procedure: dactylic_hexameter
lang: en
cases:
  - name: longfellow-evangeline
    source: Longfellow, Evangeline, opening line
    text: This is the forest primeval the murmuring pines and the hemlocks
    satisfied: true
  - name: prose-of-similar-length
    source: constructed counterexample
    text: I walked down to the shop this morning to buy a loaf
    satisfied: false
  - name: empty-text-is-not-vacuous
    source: constructed counterexample
    text: ""
    satisfied: false
```

Then verify each case against the live checker and correct the file to match
whatever it actually returns:

```bash
uv run python -c "
import yaml
from denckring import check
d = yaml.safe_load(open('src/denckring/eval/fixtures/golden/dactylic_hexameter.yaml'))
for c in d['cases']:
    r = check('dactylic_hexameter', c['text'], **c.get('params', {}))
    print(c['name'], 'recorded', c['satisfied'], 'actual', r.satisfied)
"
```

- [ ] **Step 8: Verify the catalogue row's `requires`**

The row currently declares `[tokens, syllables]`. The checker calls
`pack.tokenize` (tokens), `pack.stress_patterns` via `word_stress` (**phonemes**)
and `pack.syllable_count` (syllables). Set it to:

```yaml
    requires: [tokens, syllables, phonemes]
```

Add a note to the row:

```yaml
    notes: >-
      Checked as English accentual verse: classical quantity is vowel length,
      which English does not have, so stress stands in for it. The caesura is
      not checked, and the fifth foot is fixed as a dactyl because a spondaic
      fifth is rare enough that accepting it would cost more in false positives
      than it buys.
```

Confirm the declaration is right by running `check` and watching for
`MissingCapability`:

```bash
uv run pytest tests/test_dactylic_hexameter.py tests/test_golden.py tests/test_invariants.py -q -k dactylic_hexameter
```

- [ ] **Step 9: Full suite, lint, type-check**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
```

- [ ] **Step 10: Commit**

```bash
git add src/denckring/procedures/dactylic_hexameter.py tests/strategies/dactylic_hexameter.py tests/test_dactylic_hexameter.py src/denckring/eval/fixtures/golden/dactylic_hexameter.yaml src/denckring/data/catalogue.yaml
git commit -m "feat: implement dactylic_hexameter"
```

---

### Task 4: `elegiac_couplet`

**Files:**
- Create: `src/denckring/procedures/elegiac_couplet.py`
- Create: `tests/strategies/elegiac_couplet.py`
- Create: `src/denckring/eval/fixtures/golden/elegiac_couplet.yaml`
- Create: `tests/test_elegiac_couplet.py`
- Modify: `src/denckring/data/catalogue.yaml` — the `elegiac_couplet` row

**Interfaces:**
- Consumes: `PATTERNS` from `denckring.procedures.dactylic_hexameter` (Task 3); `feet`, `line_metre`, `MetreResult` from Tasks 1-2.
- Produces: nothing later tasks use.

- [ ] **Step 1: Write the failing test**

Create `tests/test_elegiac_couplet.py`:

```python
"""Elegiac couplet — a hexameter then a pentameter."""

from denckring import check
from denckring.procedures.elegiac_couplet import PENTAMETER_PATTERNS


def test_the_pentameter_admits_substitution_only_in_its_first_half() -> None:
    """That asymmetry is the form. A checker allowing substitution throughout
    would accept lines no elegist wrote."""
    assert len(PENTAMETER_PATTERNS) == 4
    assert min(len(p) for p in PENTAMETER_PATTERNS) == 12
    assert max(len(p) for p in PENTAMETER_PATTERNS) == 14
    # Every reading ends with the two fixed dactyls and the final long.
    assert all(p.endswith("1001001") for p in PENTAMETER_PATTERNS)


def test_an_odd_line_count_is_rejected() -> None:
    report = check("elegiac_couplet", "murmuring murmuring murmuring murmuring murmuring forest")
    assert not report.satisfied
    assert "wrong_line_count" in [v.rule for v in report.violations]


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("elegiac_couplet", "")
    assert not report.satisfied
    assert report.violations
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_elegiac_couplet.py -v`
Expected: FAIL — no module `elegiac_couplet`.

- [ ] **Step 3: Write the checker**

Create `src/denckring/procedures/elegiac_couplet.py`:

```python
"""Elegiac couplet — a dactylic hexameter answered by a pentameter."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import feet, line_metre
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.dactylic_hexameter import DACTYL, PATTERNS as HEXAMETER_PATTERNS

#: The pentameter is two hemiepes. The first admits the spondee; the second
#: never does, and that asymmetry is the form rather than an oversight.
PENTAMETER = [DACTYL, DACTYL, ("1",), ("100",), ("100",), ("1",)]

PENTAMETER_PATTERNS = feet(PENTAMETER)


class ElegiacCoupletParams(BaseModel):
    pass


@register
class ElegiacCouplet(BaseProcedure[ElegiacCoupletParams]):
    """Odd lines scan as hexameters, even lines as pentameters.

    That the pair forms one unit of sense is the form's point and is not
    checked — sense is not a property this or any checker can read.
    """

    id = "elegiac_couplet"

    @classmethod
    def params_model(cls) -> type[ElegiacCoupletParams]:
        return ElegiacCoupletParams

    def _check(self, text: str, pack: LanguagePack, params: ElegiacCoupletParams) -> Report:
        lines = line_spans(text)
        violations: list[Violation] = []
        if not lines or len(lines) % 2:
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected="an even number of lines, at least two",
                )
            )
        if not lines:
            return self._report(
                good=0,
                total=1,
                violations=violations,
                metrics={"lines": 0.0, "estimated_words": 0.0},
            )

        good = 0
        total = 0
        estimated = 0
        for index, (offset, line) in enumerate(lines):
            options = HEXAMETER_PATTERNS if index % 2 == 0 else PENTAMETER_PATTERNS
            result = line_metre(line, pack, options, offset)
            violations += result.violations
            good += result.good
            total += result.total
            estimated += result.estimated
        return self._report(
            good=good,
            total=max(total, 1) + (1 if len(lines) % 2 else 0),
            violations=violations,
            metrics={"lines": float(len(lines)), "estimated_words": float(estimated)},
        )
```

- [ ] **Step 4: Run to verify the unit tests pass**

Run: `uv run pytest tests/test_elegiac_couplet.py -v`
Expected: PASS.

- [ ] **Step 5: Write the strategies**

Create `tests/strategies/elegiac_couplet.py`:

```python
"""Generators for the elegiac couplet."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_DACTYL_WORD = st.sampled_from(["murmuring", "beautiful", "carefully", "wonderful"])
_TROCHEE_WORD = st.sampled_from(["forest", "morning", "silver", "garden"])
_STRESSED = st.sampled_from(["song", "light", "stone", "sea"])


def _hexameter(dactyls: list[str], close: str) -> str:
    return " ".join([*dactyls, close])


def satisfying() -> CaseStrategy:
    """Five dactyls plus a trochee, then the pentameter's fixed shape."""
    return st.tuples(
        st.lists(_DACTYL_WORD, min_size=5, max_size=5),
        _TROCHEE_WORD,
        st.lists(_DACTYL_WORD, min_size=2, max_size=2),
        _STRESSED,
        st.lists(_DACTYL_WORD, min_size=2, max_size=2),
        _STRESSED,
    ).map(
        lambda parts: (
            _hexameter(parts[0], parts[1])
            + "\n"
            + " ".join([*parts[2], parts[3], *parts[4], parts[5]]),
            {},
        )
    )


def violating() -> CaseStrategy:
    """Two shapes: an odd line count, and a couplet whose second line scans as
    a hexameter rather than a pentameter."""
    odd = st.lists(_DACTYL_WORD, min_size=5, max_size=5).flatmap(
        lambda dactyls: _TROCHEE_WORD.map(lambda close: (_hexameter(dactyls, close), {}))
    )
    both_hexameters = st.lists(_DACTYL_WORD, min_size=5, max_size=5).flatmap(
        lambda dactyls: _TROCHEE_WORD.map(
            lambda close: (_hexameter(dactyls, close) + "\n" + _hexameter(dactyls, close), {})
        )
    )
    return st.one_of(odd, both_hexameters)
```

- [ ] **Step 6: Run the parametrised strategy test**

Run: `uv run pytest tests/test_strategies.py -q -k elegiac_couplet`
Expected: PASS.

If `satisfying()` fails, print the scansion of the generated pentameter and
adjust the **word choice** so it matches `PENTAMETER_PATTERNS`. Do not widen the
pattern set to accommodate a generator.

- [ ] **Step 7: Record the golden fixture**

Create `src/denckring/eval/fixtures/golden/elegiac_couplet.yaml` with one
satisfying case built from the strategy's own shape, one odd-line-count case,
and an empty-text case, then verify each against the live checker exactly as in
Task 3 Step 7 and correct the file to match.

- [ ] **Step 8: Verify the catalogue row's `requires`**

Set `requires: [tokens, syllables, phonemes]` and add a note recording that the
couplet's unity of sense is not checked.

- [ ] **Step 9: Full suite, lint, type-check**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
```

- [ ] **Step 10: Commit**

```bash
git add src/denckring/procedures/elegiac_couplet.py tests/strategies/elegiac_couplet.py tests/test_elegiac_couplet.py src/denckring/eval/fixtures/golden/elegiac_couplet.yaml src/denckring/data/catalogue.yaml
git commit -m "feat: implement elegiac_couplet"
```

---

### Task 5: `sapphic_stanza` and `alcaic_stanza`

These two are one task: identical machinery, identical shape, differing only in
their pattern constants. A reviewer would accept or reject them together.

**Files:**
- Create: `src/denckring/procedures/sapphic_stanza.py`, `src/denckring/procedures/alcaic_stanza.py`
- Create: `tests/strategies/sapphic_stanza.py`, `tests/strategies/alcaic_stanza.py`
- Create: `src/denckring/eval/fixtures/golden/sapphic_stanza.yaml`, `.../alcaic_stanza.yaml`
- Create: `tests/test_sapphic_stanza.py`, `tests/test_alcaic_stanza.py`
- Modify: `src/denckring/data/catalogue.yaml` — both rows

**Interfaces:**
- Consumes: `stanza_violations`, `MetreResult` from Task 2.
- Produces: nothing later tasks use.

- [ ] **Step 1: Write the failing test asserting the patterns' own lengths**

This step comes first for a reason: the first draft of the spec gave all three
alcaic patterns the wrong length. A metre whose pattern miscounts its own line
is worse than no metre at all.

Create `tests/test_sapphic_stanza.py`:

```python
"""Sapphic stanza — three hendecasyllables and an adonic."""

from denckring import check
from denckring.procedures.sapphic_stanza import ADONIC, HENDECASYLLABLE


def test_the_patterns_are_the_right_length() -> None:
    assert len(HENDECASYLLABLE) == 11
    assert len(ADONIC) == 5


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("sapphic_stanza", "")
    assert not report.satisfied
    assert report.violations


def test_a_three_line_stanza_is_rejected() -> None:
    report = check("sapphic_stanza", "forest\nforest\nforest")
    assert not report.satisfied
    assert "wrong_line_count" in [v.rule for v in report.violations]
```

Create `tests/test_alcaic_stanza.py`:

```python
"""Alcaic stanza — two hendecasyllables, an enneasyllable, a decasyllable."""

from denckring import check
from denckring.procedures.alcaic_stanza import DECASYLLABLE, ENNEASYLLABLE, HENDECASYLLABLE


def test_the_patterns_are_the_right_length() -> None:
    """These were wrong in the spec's first draft — 10, 8 and 9 against the
    11, 9 and 10 the form requires. Pinned here before anything scans."""
    assert len(HENDECASYLLABLE) == 11
    assert len(ENNEASYLLABLE) == 9
    assert len(DECASYLLABLE) == 10


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("alcaic_stanza", "")
    assert not report.satisfied
    assert report.violations


def test_a_three_line_stanza_is_rejected() -> None:
    report = check("alcaic_stanza", "forest\nforest\nforest")
    assert not report.satisfied
    assert "wrong_line_count" in [v.rule for v in report.violations]
```

- [ ] **Step 2: Run to verify both fail**

Run: `uv run pytest tests/test_sapphic_stanza.py tests/test_alcaic_stanza.py -v`
Expected: FAIL — neither module exists.

- [ ] **Step 3: Write the sapphic checker**

Create `src/denckring/procedures/sapphic_stanza.py`:

```python
"""Sapphic stanza — three hendecasyllables closed by an adonic."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import stanza_violations
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register

#: Trochee, trochee-with-anceps, dactyl, trochee, trochee-with-anceps.
#: The `?` marks are the classical anceps, which `_fits` honours on the
#: pattern side.
HENDECASYLLABLE = "101?100101?"

#: The adonic: dactyl, trochee-with-anceps.
ADONIC = "1001?"

PATTERNS = [[HENDECASYLLABLE], [HENDECASYLLABLE], [HENDECASYLLABLE], [ADONIC]]


class SapphicStanzaParams(BaseModel):
    pass


@register
class SapphicStanza(BaseProcedure[SapphicStanzaParams]):
    """Four lines of 11, 11, 11 and 5 syllables in a fixed stress pattern.

    The English accentual reading of a quantitative measure — stress standing
    in for vowel length, which English does not have.
    """

    id = "sapphic_stanza"

    @classmethod
    def params_model(cls) -> type[SapphicStanzaParams]:
        return SapphicStanzaParams

    def _check(self, text: str, pack: LanguagePack, params: SapphicStanzaParams) -> Report:
        result = stanza_violations(text, pack, PATTERNS)
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={"lines": float(len(PATTERNS)), "estimated_words": float(result.estimated)},
        )
```

- [ ] **Step 4: Write the alcaic checker**

Create `src/denckring/procedures/alcaic_stanza.py`, identical in shape:

```python
"""Alcaic stanza — two hendecasyllables, an enneasyllable, a decasyllable."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import stanza_violations
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register

HENDECASYLLABLE = "?1011100101"
ENNEASYLLABLE = "?101?1011"
DECASYLLABLE = "100100101?"

PATTERNS = [[HENDECASYLLABLE], [HENDECASYLLABLE], [ENNEASYLLABLE], [DECASYLLABLE]]


class AlcaicStanzaParams(BaseModel):
    pass


@register
class AlcaicStanza(BaseProcedure[AlcaicStanzaParams]):
    """Four lines of 11, 11, 9 and 10 syllables in a fixed stress pattern.

    The English accentual reading of a quantitative measure, as for the
    sapphic stanza.
    """

    id = "alcaic_stanza"

    @classmethod
    def params_model(cls) -> type[AlcaicStanzaParams]:
        return AlcaicStanzaParams

    def _check(self, text: str, pack: LanguagePack, params: AlcaicStanzaParams) -> Report:
        result = stanza_violations(text, pack, PATTERNS)
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={"lines": float(len(PATTERNS)), "estimated_words": float(result.estimated)},
        )
```

- [ ] **Step 5: Run to verify the unit tests pass**

Run: `uv run pytest tests/test_sapphic_stanza.py tests/test_alcaic_stanza.py -v`
Expected: PASS. The pattern-length assertions are the ones that matter.

- [ ] **Step 6: Write both strategy modules**

For each, `satisfying()` must build a stanza that genuinely scans. Because these
patterns are fixed rather than substitutable, the reliable construction is to
choose words whose stress patterns tile the pattern exactly. Build each line
from a fixed word list, then **verify by running** before trusting it:

```bash
uv run python -c "
from denckring import check
text = 'YOUR GENERATED STANZA HERE'
r = check('sapphic_stanza', text)
print(r.satisfied, [(v.rule, v.found, v.expected) for v in r.violations])
"
```

Create `tests/strategies/sapphic_stanza.py`:

```python
"""Generators for the sapphic stanza."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Verified against CMUdict before use — see the plan's Step 6.
_TROCHEE = st.sampled_from(["forest", "morning", "silver", "garden"])
_DACTYL = st.sampled_from(["murmuring", "beautiful", "carefully", "wonderful"])
_FREE = st.sampled_from(["and", "the", "of", "in"])


def satisfying() -> CaseStrategy:
    line = st.tuples(_TROCHEE, _TROCHEE, _DACTYL, _TROCHEE, _TROCHEE).map(" ".join)
    adonic = st.tuples(_DACTYL, _TROCHEE).map(" ".join)
    return st.tuples(line, line, line, adonic).map(lambda ls: ("\n".join(ls), {}))


def violating() -> CaseStrategy:
    """Two shapes: the wrong number of lines, and four lines of the wrong
    measure — so both `wrong_line_count` and the metre rules are reached."""
    wrong_count = st.lists(_TROCHEE, min_size=2, max_size=3).map(
        lambda ws: ("\n".join(ws), {})
    )
    wrong_measure = st.lists(_FREE, min_size=4, max_size=4).map(
        lambda ws: ("\n".join(ws), {})
    )
    return st.one_of(wrong_count, wrong_measure)
```

Create `tests/strategies/alcaic_stanza.py` on the same shape, with lines built
to tile `?1011100101`, `?101?1011` and `100100101?`. Verify each generated
stanza with the snippet above before moving on — if `satisfying()` produces a
stanza the checker rejects, fix the **word choice**, never the pattern.

- [ ] **Step 7: Run the parametrised strategy tests**

Run: `uv run pytest tests/test_strategies.py -q -k sapphic_stanza or alcaic_stanza`
Expected: PASS.

- [ ] **Step 8: Record both golden fixtures**

One satisfying and one violating case each, verified against the live checker
exactly as in Task 3 Step 7. Prefer a real stanza from the literature for the
satisfying case where one scans; if none does, use a constructed one and say so
in `source`.

- [ ] **Step 9: Verify both catalogue rows' `requires`**

Both currently declare `[tokens, syllables]`. Both checkers reach
`pack.stress_patterns` through `stanza_violations`, so both become
`requires: [tokens, syllables, phonemes]`. Add a note to each recording the
accentual-for-quantitative substitution.

- [ ] **Step 10: Full suite, lint, type-check**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
```

- [ ] **Step 11: Commit**

```bash
git add src/denckring/procedures/sapphic_stanza.py src/denckring/procedures/alcaic_stanza.py tests/strategies/sapphic_stanza.py tests/strategies/alcaic_stanza.py tests/test_sapphic_stanza.py tests/test_alcaic_stanza.py src/denckring/eval/fixtures/golden/sapphic_stanza.yaml src/denckring/eval/fixtures/golden/alcaic_stanza.yaml src/denckring/data/catalogue.yaml
git commit -m "feat: implement sapphic_stanza and alcaic_stanza"
```

---

### Task 6: `double_dactyl`

**Files:**
- Create: `src/denckring/procedures/double_dactyl.py`
- Create: `tests/strategies/double_dactyl.py`
- Create: `src/denckring/eval/fixtures/golden/double_dactyl.yaml`
- Create: `tests/test_double_dactyl.py`
- Modify: `src/denckring/data/catalogue.yaml` — the `double_dactyl` row

**Interfaces:**
- Consumes: `stanza_violations` from Task 2; `line_syllables` from `denckring.procedures.syllable_count`.
- Produces: nothing later tasks use.

- [ ] **Step 1: Write the failing test**

Create `tests/test_double_dactyl.py`:

```python
"""Double dactyl — two quatrains, one line a single six-syllable word."""

from denckring import check
from denckring.procedures.double_dactyl import PATTERNS


def test_the_stanza_is_eight_lines() -> None:
    assert len(PATTERNS) == 8


def test_a_stanza_without_a_single_double_dactylic_word_is_rejected() -> None:
    """The one clause of the definition that is mechanically checkable."""
    text = "\n".join(
        ["higgledy piggledy"] * 3
        + ["carefully song"]
        + ["higgledy piggledy"] * 3
        + ["carefully song"]
    )
    report = check("double_dactyl", text)
    assert "no_double_dactylic_word" in [v.rule for v in report.violations]


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("double_dactyl", "")
    assert not report.satisfied
    assert report.violations
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_double_dactyl.py -v`
Expected: FAIL — no module `double_dactyl`.

- [ ] **Step 3: Write the checker**

Create `src/denckring/procedures/double_dactyl.py`:

```python
"""Double dactyl — two quatrains, one line a single double-dactylic word."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import stanza_violations
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans

#: Lines 1-3 and 5-7 are double dactyls; lines 4 and 8 close the quatrain.
DOUBLE_DACTYL = "100100"
CLOSE = "1001"

PATTERNS = [[DOUBLE_DACTYL]] * 3 + [[CLOSE]] + [[DOUBLE_DACTYL]] * 3 + [[CLOSE]]

#: The second quatrain is lines 5-8.
SECOND_QUATRAIN = range(4, 8)


class DoubleDactylParams(BaseModel):
    pass


@register
class DoubleDactyl(BaseProcedure[DoubleDactylParams]):
    """Checks the metre and the single double-dactylic word.

    Three clauses of the form are not checked and cannot be. That line one is a
    nonsense phrase is a lexicon question this row does not declare; that line
    two names a person needs an entity recogniser this project does not have;
    and the rhyme between lines four and eight would pull `phonemes` into a row
    that otherwise needs only syllables. A verse failing any of the three is
    still reported satisfied.
    """

    id = "double_dactyl"

    @classmethod
    def params_model(cls) -> type[DoubleDactylParams]:
        return DoubleDactylParams

    def _check(self, text: str, pack: LanguagePack, params: DoubleDactylParams) -> Report:
        result = stanza_violations(text, pack, PATTERNS)
        violations = list(result.violations)
        good = result.good
        total = result.total + 1

        lines = line_spans(text)
        if len(lines) == len(PATTERNS):
            single = [
                index
                for index in SECOND_QUATRAIN
                if len(pack.tokenize(lines[index][1])) == 1
                and pack.syllable_count(pack.tokenize(lines[index][1])[0])[0] == 6
            ]
            if single:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="no_double_dactylic_word",
                        offset=lines[SECOND_QUATRAIN.start][0],
                        found="no line of one six-syllable word",
                        expected="one line of the second quatrain to be a single "
                        "double-dactylic word",
                    )
                )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"lines": float(len(lines)), "estimated_words": float(result.estimated)},
        )
```

- [ ] **Step 4: Run to verify the unit tests pass**

Run: `uv run pytest tests/test_double_dactyl.py -v`
Expected: PASS.

- [ ] **Step 5: Write the strategies**

Create `tests/strategies/double_dactyl.py`. `satisfying()` builds eight lines
matching `PATTERNS` with one line of the second quatrain a single six-syllable
word.

**Use `vulnerability`.** It is the one candidate verified to work: CMUdict gives
it `?00100`, six syllables, exact — and `?00100` *fits* `100100` through its
free first syllable. Do not go looking for a word whose pattern **equals**
`100100`; there is none, because CMUdict marks the fourth syllable of such words
as secondary stress and this pack renders secondary stress as `?`. Candidates
that look right and are not: `geographically`, `unimaginable`, `extraordinary`,
`availability`, `respectability` — all six syllables, none fitting the metre.

If you want a second word for variety, test it before use:

```bash
uv run python -c "
from denckring.lang import get_pack
from denckring.core.prosody import _fits
p = get_pack('en')
for w in ['vulnerability', 'YOUR_CANDIDATE']:
    pats = p.stress_patterns(w)
    print(w, pats, p.syllable_count(w), any(_fits(x, '100100') for x in pats))
"
```

`violating()` must reach at least `wrong_line_count` and
`no_double_dactylic_word`, drawn among shapes rather than hard-coded to one.

- [ ] **Step 6: Run the parametrised strategy test**

Run: `uv run pytest tests/test_strategies.py -q -k double_dactyl`
Expected: PASS.

- [ ] **Step 7: Record the golden fixture, verified against the live checker**

As in Task 3 Step 7.

- [ ] **Step 8: Verify the catalogue row's `requires`**

The checker calls `pack.tokenize`, `pack.syllable_count` and — through
`stanza_violations` — `pack.stress_patterns`. So `[tokens, syllables, phonemes]`.
Add a note recording the three unchecked clauses named in the docstring.

- [ ] **Step 9: Full suite, lint, type-check**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
```

- [ ] **Step 10: Commit**

```bash
git add src/denckring/procedures/double_dactyl.py tests/strategies/double_dactyl.py tests/test_double_dactyl.py src/denckring/eval/fixtures/golden/double_dactyl.yaml src/denckring/data/catalogue.yaml
git commit -m "feat: implement double_dactyl"
```

---

### Task 7: `renga` and `haibun`

One task: both are blank-line-delimited block alternations built on the same two
helpers, and a reviewer would judge them together.

**Files:**
- Create: `src/denckring/procedures/renga.py`, `src/denckring/procedures/haibun.py`
- Create: `tests/strategies/renga.py`, `tests/strategies/haibun.py`
- Create: `src/denckring/eval/fixtures/golden/renga.yaml`, `.../haibun.yaml`
- Create: `tests/test_renga.py`, `tests/test_haibun.py`
- Modify: `src/denckring/data/catalogue.yaml` — both rows

**Interfaces:**
- Consumes: `paragraph_spans` from `denckring.core.text`; `line_syllables` from `denckring.procedures.syllable_count`.
- Produces: nothing.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_renga.py`:

```python
"""Renga — alternating three-line and two-line stanzas."""

from denckring import check

HOKKU = "cat dog mat sat run\ncat dog mat sat run sky tree\ncat dog mat sat run"
WAKIKU = "cat dog mat sat run sky tree\ncat dog mat sat run sky tree"


def test_an_alternating_chain_is_accepted() -> None:
    report = check("renga", HOKKU + "\n\n" + WAKIKU)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_a_single_stanza_is_a_hokku_not_a_renga() -> None:
    report = check("renga", HOKKU)
    assert not report.satisfied
    assert "too_few_links" in [v.rule for v in report.violations]


def test_a_chain_beginning_with_a_two_line_stanza_is_rejected() -> None:
    report = check("renga", WAKIKU + "\n\n" + HOKKU)
    assert not report.satisfied


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("renga", "")
    assert not report.satisfied
    assert report.violations
```

Create `tests/test_haibun.py`:

```python
"""Haibun — prose and haiku alternating."""

from denckring import check

HAIKU = "cat dog mat sat run\ncat dog mat sat run sky tree\ncat dog mat sat run"
PROSE = "The road turned north and the rain did not let up until evening."


def test_prose_followed_by_a_haiku_is_accepted() -> None:
    report = check("haibun", PROSE + "\n\n" + HAIKU)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_prose_alone_is_rejected() -> None:
    report = check("haibun", PROSE)
    assert not report.satisfied
    assert "missing_haiku" in [v.rule for v in report.violations]


def test_a_haiku_alone_is_rejected() -> None:
    report = check("haibun", HAIKU)
    assert not report.satisfied
    assert "missing_prose" in [v.rule for v in report.violations]


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("haibun", "")
    assert not report.satisfied
    assert report.violations
```

- [ ] **Step 2: Run to verify both fail**

Run: `uv run pytest tests/test_renga.py tests/test_haibun.py -v`
Expected: FAIL — neither module exists.

- [ ] **Step 3: Write the renga checker**

Create `src/denckring/procedures/renga.py`:

```python
"""Renga — a linked chain of alternating three-line and two-line stanzas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import paragraph_spans
from denckring.procedures.syllable_count import line_syllables

HOKKU = [5, 7, 5]
WAKIKU = [7, 7]


class RengaParams(BaseModel):
    links: int | None = Field(
        default=None, description="How many stanzas to require. Unset means any number."
    )


@register
class Renga(BaseProcedure[RengaParams]):
    """Checks the alternation of 5-7-5 and 7-7 stanzas, and nothing else.

    That a renga is composed collaboratively, and that each link joins only to
    its neighbour rather than to the whole, are the definition's substance and
    neither is a property of the text. A solo renga whose links each answer the
    entire poem will still be reported satisfied.
    """

    id = "renga"

    @classmethod
    def params_model(cls) -> type[RengaParams]:
        return RengaParams

    def _check(self, text: str, pack: LanguagePack, params: RengaParams) -> Report:
        stanzas = paragraph_spans(text)
        violations: list[Violation] = []
        good = 0
        total = 0
        estimated = 0

        if len(stanzas) < 2:
            violations.append(
                Violation(
                    rule="too_few_links",
                    offset=None,
                    found=f"{len(stanzas)} stanzas",
                    expected="at least 2 — one stanza is a hokku, not a renga",
                )
            )
            total += 1

        if params.links is not None and len(stanzas) != params.links:
            violations.append(
                Violation(
                    rule="too_few_links",
                    offset=None,
                    found=f"{len(stanzas)} stanzas",
                    expected=f"{params.links} stanzas",
                )
            )
            total += 1

        for index, (offset, stanza) in enumerate(stanzas):
            wanted = HOKKU if index % 2 == 0 else WAKIKU
            measured = line_syllables(stanza, pack)
            estimated += sum(count for _, _, count in measured)
            total += 1
            if len(measured) != len(wanted):
                violations.append(
                    Violation(
                        rule="wrong_stanza_shape",
                        offset=offset,
                        found=f"{len(measured)} lines",
                        expected=f"{len(wanted)} lines",
                    )
                )
                continue
            faults = [
                Violation(
                    rule="wrong_syllable_count",
                    offset=line_offset,
                    found=f"{syllables} syllables",
                    expected=f"{expected} syllables",
                )
                for (line_offset, syllables, _), expected in zip(measured, wanted, strict=True)
                if syllables != expected
            ]
            violations += faults
            if not faults:
                good += 1

        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"stanzas": float(len(stanzas)), "estimated_words": float(estimated)},
        )
```

- [ ] **Step 4: Write the haibun checker**

Create `src/denckring/procedures/haibun.py`:

```python
"""Haibun — prose and haiku alternating in one work."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import paragraph_spans
from denckring.procedures.syllable_count import line_syllables

HAIKU = [5, 7, 5]


def _is_haiku(block: str, pack: LanguagePack) -> bool:
    measured = line_syllables(block, pack)
    return len(measured) == len(HAIKU) and all(
        syllables == expected
        for (_, syllables, _), expected in zip(measured, HAIKU, strict=True)
    )


class HaibunParams(BaseModel):
    pass


@register
class Haibun(BaseProcedure[HaibunParams]):
    """Checks the alternation of prose and 5-7-5 verse only.

    Whether the haiku condenses the passage rather than continuing it is a
    judgement about sense, which no checker can make. It is not checked, and a
    haibun that fails it will still be reported satisfied.
    """

    id = "haibun"

    @classmethod
    def params_model(cls) -> type[HaibunParams]:
        return HaibunParams

    def _check(self, text: str, pack: LanguagePack, params: HaibunParams) -> Report:
        blocks = paragraph_spans(text)
        kinds = [(offset, _is_haiku(block, pack)) for offset, block in blocks]
        violations: list[Violation] = []
        total = 2
        good = 0

        if not any(verse for _, verse in kinds):
            violations.append(
                Violation(
                    rule="missing_haiku",
                    offset=None,
                    found=f"{len(blocks)} blocks, none a 5-7-5 verse",
                    expected="at least one haiku",
                )
            )
        else:
            good += 1

        if not any(not verse for _, verse in kinds):
            violations.append(
                Violation(
                    rule="missing_prose",
                    offset=None,
                    found=f"{len(blocks)} blocks, all verse",
                    expected="at least one prose passage",
                )
            )
        else:
            good += 1

        for index, (offset, verse) in enumerate(kinds):
            total += 1
            if verse == bool(index % 2):
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="wrong_alternation",
                        offset=offset,
                        found="verse" if verse else "prose",
                        expected="prose" if index % 2 == 0 else "verse",
                    )
                )

        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"blocks": float(len(blocks)), "estimated_words": 0.0},
        )
```

- [ ] **Step 5: Run to verify the unit tests pass**

Run: `uv run pytest tests/test_renga.py tests/test_haibun.py -v`
Expected: PASS.

- [ ] **Step 6: Write both strategy modules**

Both build from the one-syllable word list `haiku`'s strategy already uses —
`["cat", "dog", "mat", "sat", "run", "sky", "tree", "stone"]` — so counts are
exact under both the dictionary and the heuristic. `renga`'s `violating()` must
reach `too_few_links` and `wrong_stanza_shape`; `haibun`'s must reach
`missing_haiku`, `missing_prose` and `wrong_alternation`. Draw among the shapes.

- [ ] **Step 7: Run the parametrised strategy tests**

Run: `uv run pytest tests/test_strategies.py -q -k renga or haibun`
Expected: PASS.

- [ ] **Step 8: Record both golden fixtures, verified against the live checker**

As in Task 3 Step 7.

- [ ] **Step 9: Verify both catalogue rows' `requires`**

Neither checker reaches `pack.stress_patterns` — both use only `tokenize` and
`syllable_count`. So both keep `requires: [tokens, syllables]` and **must not**
gain `phonemes`. Confirm by reading the modules rather than by analogy with the
metrical rows. Add a note to each recording the unchecked clause from its
docstring.

- [ ] **Step 10: Full suite, lint, type-check**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
```

- [ ] **Step 11: Commit**

```bash
git add src/denckring/procedures/renga.py src/denckring/procedures/haibun.py tests/strategies/renga.py tests/strategies/haibun.py tests/test_renga.py tests/test_haibun.py src/denckring/eval/fixtures/golden/renga.yaml src/denckring/eval/fixtures/golden/haibun.yaml src/denckring/data/catalogue.yaml
git commit -m "feat: implement renga and haibun"
```

---

### Task 8: CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read the established format**

```bash
git show ca69ec1 -- CHANGELOG.md
git show 6432a49 -- CHANGELOG.md
```

Match their format and voice rather than inventing a style.

- [ ] **Step 2: Write the entry**

Cover the seven new procedures, the anceps fix, the out-of-dictionary repair,
and the three new prosody helpers. The out-of-dictionary repair deserves its own
clause: it changes what `MissingCapability` means in the metre path, and any
caller who had worked around the old behaviour needs to know.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: record the syllabic batch"
```

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: the anceps and
out-of-dictionary repairs to Task 1; `stanza_violations` and `feet` to Task 2;
the seven procedures to Tasks 3-7; the CHANGELOG to Task 8. The spec's
`Sequencing` section is honoured — Tasks 3-7 all depend on Tasks 1-2 and are
independent of each other, except Task 4 which imports Task 3's `PATTERNS` and
`DACTYL`.

**Type consistency.** `MetreResult` is defined in Task 1 and consumed by name in
Tasks 2-6. `metre_violations` returns `MetreResult` from Task 1 onward, and
Task 1 Step 12 updates its only existing caller. `feet` takes
`Sequence[Sequence[str]]` and returns `list[str]` in both Task 2 and its callers
in Tasks 3-4. `stanza_violations` takes `Sequence[Sequence[str]]` throughout.
`PATTERNS` is a `list[list[str]]` in Tasks 5-6 (per-line options) but a
`list[str]` in Tasks 3-4 (whole-line readings) — different shapes for different
helpers, which is why Task 4 imports Task 3's explicitly by name.

**Constants verified against CMUdict, not recalled.** Every word this plan hands
an implementer was run through the pack before being written down, and three
first drafts were wrong: `shipwreck` is `10` and does not fit a spondee slot;
none of `unimaginatively`, `antidisestablish`, `undeniability` or
`irresponsibility` is a six-syllable in-dictionary word; and no English word's
stress pattern *equals* `100100`, because this pack renders CMUdict's secondary
stress as `?`. The surviving constants — the four dactyls, the four trochees,
the three spondees, and `vulnerability` — all check out. This mattered more than
usual here: a metre plan whose example words scan wrongly sends an implementer
chasing a phantom bug in the scanner.

**Known gap, deliberately left.** Tasks 5 and 6 do not give literal generated
stanzas for their `satisfying()` strategies, because the correct word choice
depends on what CMUdict actually returns for each candidate. Both tasks instead
give the exact command to verify a candidate and the rule for resolving a
mismatch: fix the word choice, never the pattern. This is the one place the plan
asks the implementer to determine a value rather than transcribe it, and it is
bounded by an assertion that already exists (the pattern-length tests in Task 5
Step 1).
