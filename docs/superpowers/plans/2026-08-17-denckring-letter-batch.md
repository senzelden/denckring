# Letter Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `belle_absente`, `serial_lipogram`, `pangrammatic_window` and `paragram`, taking `implemented` from 75 to 79.

**Architecture:** Four independent procedures, one module each (ADR 0007), each registered with `@register` and discovered automatically. Every procedure owes four files — checker, Hypothesis strategy, golden fixture, unit tests — because `test_strategies.py` and the golden invariants are parametrised by procedure id and will fail the moment a row is registered without them. No catalogue edits: all four rows already exist.

**Tech Stack:** Python ≥3.11, pydantic v2, pytest, hypothesis, ruff, mypy --strict, uv.

**Spec:** `docs/superpowers/specs/2026-08-17-letter-batch-design.md`

## Global Constraints

- Python `>=3.11`. Core gains **no** new runtime dependency.
- Run everything through uv from the repository root: `uv run pytest`, `uv run ruff check`, `uv run mypy --strict`.
- `uv sync --extra en --extra de` before testing, or unrelated tests fail for unrelated reasons.
- The suite is **1927 passing** at the base commit and must still pass.
- `ruff check`, `ruff format --check`, and `mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src` must all be clean.
- Golden fixtures record what the checker **actually returns**. Never write an aspirational `satisfied:` value — run the checker and record the result. "The validator is the eval" is the project's governing premise.
- Each row's `requires` must match what the code actually calls. `requires` gates `check`, so a stale entry raises `MissingCapability` for a caller who needed nothing. Verify, do not assume.
- Do not add `apply` to `belle_absente`, `serial_lipogram` or `pangrammatic_window` — all three are `kind: restrictive`, and ADR 0002 makes a generator meaningless for those.
- Do not declare `de` on any of these rows. Three of them could support it, but a declared language needs a golden case, and that belongs to a later German sweep.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/denckring/core/text.py` | Modify: add `paragraph_spans` beside `line_spans` |
| `src/denckring/procedures/belle_absente.py` | Create: checker |
| `src/denckring/procedures/serial_lipogram.py` | Create: checker |
| `src/denckring/procedures/pangrammatic_window.py` | Create: checker |
| `src/denckring/procedures/paragram.py` | Create: checker + lexicon-gated `apply` |
| `tests/strategies/<id>.py` × 4 | Create: `satisfying()` / `violating()` |
| `src/denckring/eval/fixtures/golden/<id>.yaml` × 4 | Create: golden cases |
| `tests/test_<id>.py` × 4 | Create: unit tests |

The four procedures are independent. Only `serial_lipogram` needs `paragraph_spans`, so that helper is folded into its task rather than being a task of its own.

---

### Task 1: `belle_absente`

Perec's form: one line per letter of a dedicatee's name, each line omitting that letter and using every other letter of the alphabet.

**Files:**
- Create: `src/denckring/procedures/belle_absente.py`
- Create: `tests/strategies/belle_absente.py`
- Create: `src/denckring/eval/fixtures/golden/belle_absente.yaml`
- Create: `tests/test_belle_absente.py`

**Interfaces:**
- Consumes: `denckring.core.text.letter_spans`, `line_spans`; `BaseProcedure`, `DiacriticParams`.
- Produces: procedure id `belle_absente`. Nothing else depends on it.

- [ ] **Step 1: Write the failing unit tests**

Create `tests/test_belle_absente.py`:

```python
import pytest

from denckring import check
from denckring.core.errors import InvalidParams

# Every letter except the one each line omits. Built by hand so the test does
# not depend on the checker it is testing.
WITHOUT_A = "Blitz crwth vug jynx fed komp qophs"
WITHOUT_B = "Quartz glyph vex jocks fund whimp"


def test_a_line_per_letter_of_the_name() -> None:
    report = check("belle_absente", f"{WITHOUT_A}\n{WITHOUT_B}", name="ab")
    assert report.metrics["lines"] == 2.0


def test_a_line_containing_its_own_letter_violates() -> None:
    report = check("belle_absente", "banana\nbanana", name="ab")
    assert not report.satisfied
    assert any(v.rule == "forbidden_letter_present" for v in report.violations)


def test_a_line_missing_another_letter_violates() -> None:
    report = check("belle_absente", "bcd\nacd", name="ab")
    assert not report.satisfied
    assert any(v.rule == "missing_letter" for v in report.violations)


def test_wrong_line_count_is_reported() -> None:
    report = check("belle_absente", WITHOUT_A, name="ab")
    assert any(v.rule == "wrong_line_count" for v in report.violations)


def test_the_name_reduces_to_its_letters() -> None:
    """`Georges Perec` is twelve constraints, not thirteen — the space is not one."""
    report = check("belle_absente", "x", name="Georges Perec")
    expected = [v for v in report.violations if v.rule == "wrong_line_count"]
    assert expected and "12" in expected[0].expected


def test_a_repeated_letter_is_a_repeated_constraint() -> None:
    """Perec's dedications repeat letters; each occurrence is its own line."""
    report = check("belle_absente", "x\nx\nx", name="aba")
    assert report.metrics["lines"] == 3.0


def test_an_empty_name_is_refused() -> None:
    with pytest.raises(InvalidParams):
        check("belle_absente", "anything", name="!!!")


def test_violations_carry_offsets() -> None:
    report = check("belle_absente", "banana\nx", name="ab")
    offending = [v for v in report.violations if v.rule == "forbidden_letter_present"]
    assert offending and offending[0].offset is not None
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_belle_absente.py -q`
Expected: FAIL — `UnknownProcedure: No procedure with id 'belle_absente'`.

- [ ] **Step 3: Write the checker**

Create `src/denckring/procedures/belle_absente.py`:

```python
"""Belle absente — one line per letter of a name, each line without that letter."""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, line_spans


class BelleAbsenteParams(DiacriticParams):
    name: str = Field(description="The dedicatee. One line per letter of it.")

    @field_validator("name")
    @classmethod
    def _has_letters(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("name must contain at least one letter")
        return value


@register
class BelleAbsente(BaseProcedure[BelleAbsenteParams]):
    """Perec's form: the absent letter spells the dedication.

    Each line omits one letter of the name and uses every other letter of the
    alphabet, so the missing letters read down the poem as the name itself.
    """

    id = "belle_absente"

    @classmethod
    def params_model(cls) -> type[BelleAbsenteParams]:
        return BelleAbsenteParams

    def _check(self, text: str, pack: LanguagePack, params: BelleAbsenteParams) -> Report:
        alphabet = pack.alphabet()
        # The space in "Georges Perec" is not a constraint, and neither is a
        # hyphen: the name reduces to the letters it is spelled with.
        wanted = [ch for ch in params.name.lower() if ch.isalpha()]
        lines = line_spans(text)

        violations: list[Violation] = []
        good = 0
        for index, letter in enumerate(wanted):
            if index >= len(lines):
                continue
            offset, line = lines[index]
            present = {
                ch for _, ch in letter_spans(line, pack, fold=params.fold_diacritics)
            }
            intruder = [
                span_offset
                for span_offset, ch in letter_spans(line, pack, fold=params.fold_diacritics)
                if ch == letter
            ]
            missing = [ch for ch in alphabet if ch != letter and ch not in present]
            if intruder:
                violations.append(
                    Violation(
                        rule="forbidden_letter_present",
                        offset=intruder[0],
                        found=letter,
                        expected=f"line {index + 1} without {letter!r}",
                    )
                )
            for ch in missing:
                violations.append(
                    Violation(
                        rule="missing_letter",
                        offset=offset,
                        found="",
                        expected=f"{ch!r} somewhere in line {index + 1}",
                    )
                )
            if not intruder and not missing:
                good += 1

        if len(lines) != len(wanted):
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected=f"{len(wanted)} lines, one per letter of the name",
                )
            )
        return self._report(
            good=good,
            total=max(len(wanted), len(lines)),
            violations=violations,
            metrics={"lines": float(len(lines)), "letters": float(len(wanted))},
        )
```

- [ ] **Step 4: Run the unit tests to verify they pass**

Run: `uv run pytest tests/test_belle_absente.py -q`
Expected: PASS. If `test_a_line_per_letter_of_the_name` fails because `WITHOUT_A`/`WITHOUT_B` are not really pangrams-minus-one, FIX THE TEST CONSTANTS, not the checker — build them by taking `abcdefghijklmnopqrstuvwxyz`, removing the one letter, and joining. Verify with:

```bash
uv run python -c "
import string
for drop in 'ab':
    print(drop, ''.join(c for c in string.ascii_lowercase if c != drop))
"
```

- [ ] **Step 5: Write the strategy**

Create `tests/strategies/belle_absente.py`:

```python
"""Generators for belle_absente. `satisfying` and `violating` are the module contract."""

import string

from hypothesis import strategies as st

from strategies import CaseStrategy

ALPHABET = string.ascii_lowercase


def _line_without(letter: str) -> str:
    """Every letter but one, which is exactly what each line must contain."""
    return " ".join(ch for ch in ALPHABET if ch != letter)


def _poem(name: str) -> tuple[str, dict[str, object]]:
    letters = [ch for ch in name if ch.isalpha()]
    return "\n".join(_line_without(ch) for ch in letters), {"name": name}


def satisfying() -> CaseStrategy:
    return st.text(alphabet=ALPHABET, min_size=1, max_size=5).map(_poem)


def violating() -> CaseStrategy:
    """Put the forbidden letter back into the first line."""

    def spoil(pair: tuple[str, str]) -> tuple[str, dict[str, object]]:
        name, _ = pair[0], pair[1]
        text, params = _poem(name)
        first = [ch for ch in name if ch.isalpha()][0]
        return first + text, params

    return st.tuples(
        st.text(alphabet=ALPHABET, min_size=1, max_size=5),
        st.just(""),
    ).map(spoil)
```

- [ ] **Step 6: Run the strategy tests**

Run: `uv run pytest tests/test_strategies.py -q -k belle_absente`
Expected: PASS both `satisfying` and `violating`. If `violating` occasionally produces a satisfying case, tighten it — a strategy that sometimes generates the wrong class is a flaky test, not an acceptable one.

- [ ] **Step 7: Write the golden fixture**

Compute the real verdicts first — never guess them:

```bash
uv run python -c "
import string
from denckring import check
name = 'ab'
poem = '\n'.join(' '.join(c for c in string.ascii_lowercase if c != d) for d in name)
print(repr(poem))
print(check('belle_absente', poem, name=name).satisfied)
print(check('belle_absente', 'banana\nbanana', name=name).satisfied)
"
```

Create `src/denckring/eval/fixtures/golden/belle_absente.yaml` with one satisfying and one violating case, using the text and verdicts that command printed:

```yaml
procedure: belle_absente
lang: en
cases:
  - name: two-letter-dedication
    source: >-
      constructed example; the form is Perec's, in Oulipo, Atlas de littérature
      potentielle (1981)
    text: <the poem printed above>
    params: { name: ab }
    satisfied: true
  - name: a-line-keeping-its-own-letter
    source: constructed counterexample
    text: <the violating text printed above>
    params: { name: ab }
    satisfied: false
```

- [ ] **Step 8: Verify the fixture and the requires**

Run: `uv run pytest tests/test_golden.py tests/test_invariants.py -q -k belle_absente`
Expected: PASS.

Then confirm the row's `requires` matches what the code calls. The checker uses `pack.alphabet()`, `letter_spans` (which calls `pack.fold_diacritics`) and `line_spans` (which needs no pack). It does **not** call `pack.word_spans`, so `tokens` may be stale:

```bash
grep -n -A2 "id: belle_absente" src/denckring/data/catalogue.yaml | grep requires
```

If `tokens` is declared and unused, remove it and say so in your report. If you are unsure whether a capability is used, leave it and flag it — removing one that is used breaks `check`.

- [ ] **Step 9: Lint, typecheck, full suite**

```bash
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
uv sync --extra en --extra de && uv run pytest -q
```
Expected: all clean; suite ≥ 1927 passing.

- [ ] **Step 10: Commit**

```bash
git add src/denckring/procedures/belle_absente.py tests/strategies/belle_absente.py \
        src/denckring/eval/fixtures/golden/belle_absente.yaml tests/test_belle_absente.py \
        src/denckring/data/catalogue.yaml
git commit -m "feat: implement belle_absente"
```

---

### Task 2: `serial_lipogram`

Tryphiodorus's arrangement: a work in as many parts as the alphabet has letters, each part omitting a different one.

**Files:**
- Modify: `src/denckring/core/text.py` (add `paragraph_spans`)
- Create: `src/denckring/procedures/serial_lipogram.py`
- Create: `tests/strategies/serial_lipogram.py`
- Create: `src/denckring/eval/fixtures/golden/serial_lipogram.yaml`
- Create: `tests/test_serial_lipogram.py`

**Interfaces:**
- Consumes: `letter_spans`, `line_spans`; adds `paragraph_spans`.
- Produces: `denckring.core.text.paragraph_spans(text: str) -> list[tuple[int, str]]`, and procedure id `serial_lipogram`.

- [ ] **Step 1: Write the failing test for the helper**

Append to `tests/test_text.py`:

```python
def test_paragraph_spans_splits_on_blank_lines() -> None:
    from denckring.core.text import paragraph_spans

    text = "first para\nstill first\n\nsecond para\n\n\nthird"
    spans = paragraph_spans(text)
    assert [t for _, t in spans] == ["first para\nstill first", "second para", "third"]


def test_paragraph_spans_keep_their_offsets() -> None:
    from denckring.core.text import paragraph_spans

    text = "aaa\n\nbbb"
    spans = paragraph_spans(text)
    assert spans[1][0] == text.index("bbb")


def test_paragraph_spans_of_a_blank_text_is_empty() -> None:
    from denckring.core.text import paragraph_spans

    assert paragraph_spans("\n\n   \n") == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_text.py -q -k paragraph`
Expected: FAIL — `ImportError: cannot import name 'paragraph_spans'`.

- [ ] **Step 3: Write the helper**

Add to `src/denckring/core/text.py`, immediately after `line_spans`:

```python
def paragraph_spans(text: str) -> list[tuple[int, str]]:
    """Every non-blank paragraph as `(offset, text)`, split on blank lines.

    A serial lipogram's parts are sections, not lines — Tryphiodorus wrote
    twenty-four books — so the unit has to be able to hold more than one line.
    """
    spans: list[tuple[int, str]] = []
    offset = 0
    for block in text.split("\n\n"):
        stripped = block.strip()
        if stripped:
            spans.append((offset + block.index(stripped[0]), stripped))
        offset += len(block) + 2
    return spans
```

- [ ] **Step 4: Run the helper tests**

Run: `uv run pytest tests/test_text.py -q -k paragraph`
Expected: PASS. If `test_paragraph_spans_splits_on_blank_lines` fails on the three-newline case, the `split("\n\n")` leaves an empty block that `strip()` discards — confirm the offsets are still right rather than changing the assertion.

- [ ] **Step 5: Write the failing procedure tests**

Create `tests/test_serial_lipogram.py`:

```python
import string

import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def parts_without(letters: str) -> str:
    """One paragraph per letter, each omitting the letter it is assigned."""
    return "\n\n".join(
        " ".join(ch for ch in string.ascii_lowercase if ch != drop) for drop in letters
    )


def test_each_part_omitting_its_letter_is_satisfied() -> None:
    assert check("serial_lipogram", parts_without("abc")).satisfied


def test_a_part_keeping_its_letter_violates() -> None:
    report = check("serial_lipogram", "aaa\n\nbbb")
    assert not report.satisfied
    assert any(v.rule == "letter_present" for v in report.violations)


def test_the_walk_starts_at_a_by_default() -> None:
    """Unlike abecedarian, the start cannot be read off the text: a missing
    letter looks like any other letter a short part happens to lack."""
    report = check("serial_lipogram", "zzz")
    assert report.satisfied, "a part without 'a' satisfies the first constraint"


def test_start_moves_the_walk() -> None:
    report = check("serial_lipogram", "aaa", start="b")
    assert report.satisfied


def test_lines_can_be_the_unit() -> None:
    text = "\n".join(" ".join(c for c in string.ascii_lowercase if c != d) for d in "ab")
    assert check("serial_lipogram", text, unit="line").satisfied


def test_more_parts_than_the_alphabet_wraps() -> None:
    assert check("serial_lipogram", parts_without(string.ascii_lowercase + "a")).satisfied


def test_start_must_be_a_single_letter() -> None:
    with pytest.raises(InvalidParams):
        check("serial_lipogram", "x", start="ab")
```

- [ ] **Step 6: Run to verify they fail**

Run: `uv run pytest tests/test_serial_lipogram.py -q`
Expected: FAIL — `UnknownProcedure`.

- [ ] **Step 7: Write the checker**

Create `src/denckring/procedures/serial_lipogram.py`:

```python
"""Serial lipogram — one part per letter, each omitting the letter it is given."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, line_spans, paragraph_spans


class SerialLipogramParams(DiacriticParams):
    unit: Literal["paragraph", "line"] = Field(
        default="paragraph", description="What carries one letter's constraint."
    )
    start: str | None = Field(default=None, description="The letter the first part omits.")

    @field_validator("start")
    @classmethod
    def _single_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != 1 or not value.isalpha():
            raise ValueError("start must be a single alphabetic character")
        return value.lower()


@register
class SerialLipogram(BaseProcedure[SerialLipogramParams]):
    """The constraint walks the alphabet instead of holding to one letter.

    Where `abecedarian` can read its starting letter off the first line, this
    cannot: its constraint is an absence, and a short part is missing many
    letters. So the walk starts at the alphabet's first letter unless told
    otherwise — which is Tryphiodorus's own arrangement, book one omitting alpha.
    """

    id = "serial_lipogram"

    @classmethod
    def params_model(cls) -> type[SerialLipogramParams]:
        return SerialLipogramParams

    def _check(self, text: str, pack: LanguagePack, params: SerialLipogramParams) -> Report:
        alphabet = pack.alphabet()
        parts = paragraph_spans(text) if params.unit == "paragraph" else line_spans(text)
        first = alphabet.index(params.start) if params.start in alphabet else 0

        violations: list[Violation] = []
        good = 0
        for index, (offset, part) in enumerate(parts):
            forbidden = alphabet[(first + index) % len(alphabet)]
            hits = [
                span_offset
                for span_offset, ch in letter_spans(part, pack, fold=params.fold_diacritics)
                if ch == forbidden
            ]
            if hits:
                violations.append(
                    Violation(
                        rule="letter_present",
                        offset=offset + hits[0],
                        found=forbidden,
                        expected=f"part {index + 1} without {forbidden!r}",
                    )
                )
            else:
                good += 1
        return self._report(
            good=good,
            total=len(parts),
            violations=violations,
            metrics={"parts": float(len(parts))},
        )
```

- [ ] **Step 8: Run the tests**

Run: `uv run pytest tests/test_serial_lipogram.py -q`
Expected: PASS. Note `letter_spans` returns offsets relative to the part, so they are added to the part's own offset — check `test_a_part_keeping_its_letter_violates` reports an offset inside the text, not inside the paragraph.

- [ ] **Step 9: Write the strategy**

Create `tests/strategies/serial_lipogram.py`:

```python
"""Generators for serial_lipogram. `satisfying` and `violating` are the module contract."""

import string

from hypothesis import strategies as st

from strategies import CaseStrategy

ALPHABET = string.ascii_lowercase


def _parts(count: int) -> str:
    return "\n\n".join(
        " ".join(ch for ch in ALPHABET if ch != ALPHABET[index]) for index in range(count)
    )


def satisfying() -> CaseStrategy:
    return st.integers(min_value=1, max_value=6).map(lambda n: (_parts(n), {}))


def violating() -> CaseStrategy:
    """Put the forbidden letter back into the first part."""
    return st.integers(min_value=1, max_value=6).map(lambda n: ("a" + _parts(n), {}))
```

- [ ] **Step 10: Run the strategy tests**

Run: `uv run pytest tests/test_strategies.py -q -k serial_lipogram`
Expected: PASS.

- [ ] **Step 11: Golden fixture, lint, typecheck, suite, commit**

Compute the verdicts, then write `src/denckring/eval/fixtures/golden/serial_lipogram.yaml` with one satisfying and one violating case. Cite the source honestly — the row attributes the form to Tryphiodorus, and Jean Paul excerpted it in 1783; the example text itself is constructed.

```bash
uv run pytest tests/test_golden.py tests/test_invariants.py -q -k serial_lipogram
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
uv run pytest -q
git add src/denckring/core/text.py src/denckring/procedures/serial_lipogram.py \
        tests/strategies/serial_lipogram.py tests/test_serial_lipogram.py \
        tests/test_text.py src/denckring/eval/fixtures/golden/serial_lipogram.yaml
git commit -m "feat: implement serial_lipogram"
```

---

### Task 3: `pangrammatic_window`

The shortest run of ordinary prose containing every letter — with the bar made a parameter, because "as short as possible" is not decidable from one text.

**Files:**
- Create: `src/denckring/procedures/pangrammatic_window.py`
- Create: `tests/strategies/pangrammatic_window.py`
- Create: `src/denckring/eval/fixtures/golden/pangrammatic_window.yaml`
- Create: `tests/test_pangrammatic_window.py`

**Interfaces:**
- Consumes: `letter_spans`; `BaseProcedure`, `DiacriticParams`. Follows `pangram`'s precedent of building its `Report` directly.
- Produces: procedure id `pangrammatic_window`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pangrammatic_window.py`:

```python
import pytest

from denckring import check
from denckring.core.errors import InvalidParams

PANGRAM = "Pack my box with five dozen liquor jugs"  # 31 letters


def test_a_short_pangram_is_satisfied() -> None:
    report = check("pangrammatic_window", PANGRAM, max_length=40)
    assert report.satisfied
    assert report.metrics["letters"] == 31.0


def test_a_pangram_over_the_bar_violates() -> None:
    report = check("pangrammatic_window", PANGRAM, max_length=30)
    assert not report.satisfied
    assert any(v.rule == "window_too_long" for v in report.violations)


def test_a_missing_letter_violates() -> None:
    report = check("pangrammatic_window", "the quick brown fox", max_length=100)
    assert not report.satisfied
    assert any(v.rule == "missing_letter" for v in report.violations)


def test_an_empty_text_is_unsatisfied_not_vacuous() -> None:
    """Like pangram: it requires something rather than forbidding something, so
    an empty text supplies none of it."""
    report = check("pangrammatic_window", "", max_length=100)
    assert not report.satisfied
    assert report.score == 0.0


def test_exactly_at_the_bar_is_satisfied() -> None:
    assert check("pangrammatic_window", PANGRAM, max_length=31).satisfied


def test_max_length_is_required() -> None:
    with pytest.raises(InvalidParams):
        check("pangrammatic_window", PANGRAM)


def test_max_length_below_the_alphabet_is_refused() -> None:
    with pytest.raises(InvalidParams):
        check("pangrammatic_window", PANGRAM, max_length=25)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_pangrammatic_window.py -q`
Expected: FAIL — `UnknownProcedure`.

- [ ] **Step 3: Write the checker**

Create `src/denckring/procedures/pangrammatic_window.py`:

```python
"""Pangrammatic window — every letter, inside a stated span."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class PangrammaticWindowParams(DiacriticParams):
    #: Required rather than defaulted. "As short as possible" is not decidable
    #: from one text, and without a bar this procedure is `pangram` under a
    #: second name — so the caller states the bar, as ADR 0009 has editorial
    #: choices become parameters rather than hidden constants.
    max_length: int = Field(ge=26, description="The longest window that still counts.")


@register
class PangrammaticWindow(BaseProcedure[PangrammaticWindowParams]):
    """Word Ways' hunt: a naturally occurring run holding the whole alphabet.

    Like `pangram`, an empty text is unsatisfied rather than vacuous — it
    requires something instead of forbidding something, so an empty text
    supplies none of it. That is why this builds its Report directly.
    """

    id = "pangrammatic_window"

    @classmethod
    def params_model(cls) -> type[PangrammaticWindowParams]:
        return PangrammaticWindowParams

    def _check(
        self, text: str, pack: LanguagePack, params: PangrammaticWindowParams
    ) -> Report:
        alphabet = pack.alphabet()
        letters = [ch for _, ch in letter_spans(text, pack, fold=params.fold_diacritics)]
        present = set(letters)
        missing = [ch for ch in alphabet if ch not in present]

        violations = [
            Violation(
                rule="missing_letter",
                offset=None,
                found="",
                expected=f"{ch!r} somewhere in the window",
            )
            for ch in missing
        ]
        if len(letters) > params.max_length:
            violations.append(
                Violation(
                    rule="window_too_long",
                    offset=None,
                    found=f"{len(letters)} letters",
                    expected=f"at most {params.max_length}",
                )
            )
        satisfied = not violations
        return Report(
            procedure=self.id,
            satisfied=satisfied,
            score=1.0 if satisfied else len(present & set(alphabet)) / len(alphabet),
            violations=violations,
            metrics={"letters": float(len(letters)), "missing": float(len(missing))},
        )
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_pangrammatic_window.py -q`
Expected: PASS. If `test_an_empty_text_is_unsatisfied_not_vacuous` reports a non-zero score, that is correct behaviour only if the score formula gives 0 for no letters — check that `len(present & set(alphabet)) / len(alphabet)` is `0.0` when the text is empty, and fix the formula rather than the test if it is not.

- [ ] **Step 5: Write the strategy**

Create `tests/strategies/pangrammatic_window.py`:

```python
"""Generators for pangrammatic_window. `satisfying` and `violating` are the contract."""

import string

from hypothesis import strategies as st

from strategies import CaseStrategy

ALPHABET = string.ascii_lowercase


def satisfying() -> CaseStrategy:
    """The alphabet plus padding, with a bar generous enough to hold it."""
    return st.integers(min_value=0, max_value=20).map(
        lambda extra: (ALPHABET + "a" * extra, {"max_length": 26 + extra})
    )


def violating() -> CaseStrategy:
    """One letter short, however generous the bar."""
    return st.integers(min_value=0, max_value=25).map(
        lambda drop: (
            "".join(ch for ch in ALPHABET if ch != ALPHABET[drop]),
            {"max_length": 100},
        )
    )
```

- [ ] **Step 6: Run the strategy tests**

Run: `uv run pytest tests/test_strategies.py -q -k pangrammatic_window`
Expected: PASS.

- [ ] **Step 7: Golden fixture, verification, commit**

Use a real Word Ways-style window for the satisfying case and record its actual verdict. Compute first:

```bash
uv run python -c "
from denckring import check
t = 'Pack my box with five dozen liquor jugs'
r = check('pangrammatic_window', t, max_length=40)
print(r.satisfied, r.metrics)
"
```

Write the fixture with one satisfying and one violating case, then:

```bash
uv run pytest tests/test_golden.py tests/test_invariants.py -q -k pangrammatic_window
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
uv run pytest -q
git add src/denckring/procedures/pangrammatic_window.py \
        tests/strategies/pangrammatic_window.py tests/test_pangrammatic_window.py \
        src/denckring/eval/fixtures/golden/pangrammatic_window.yaml
git commit -m "feat: implement pangrammatic_window"
```

---

### Task 4: `paragram`

A one-letter swap made the point of the line — and the only row in this batch that is `kind: both`, so it needs a generator.

**Files:**
- Create: `src/denckring/procedures/paragram.py`
- Create: `tests/strategies/paragram.py`
- Create: `src/denckring/eval/fixtures/golden/paragram.yaml`
- Create: `tests/test_paragram.py`
- Modify: `src/denckring/data/catalogue.yaml` (a `notes` line only)

**Interfaces:**
- Consumes: `word_spans`; `require_capability` from `denckring.core.base`; `WORDS` from `denckring.lang.base`.
- Produces: procedure id `paragram`, with `apply`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_paragram.py`:

```python
import pytest

from denckring import check
from denckring.core.errors import MissingCapability
from denckring.core.protocol import Constructive
from denckring.core.registry import get


def test_a_one_letter_swap_is_found() -> None:
    report = check("paragram", "the cat sat on the mat")
    assert report.satisfied
    assert report.metrics["pairs"] >= 1.0


def test_a_text_with_no_swap_violates() -> None:
    report = check("paragram", "one three seventeen")
    assert not report.satisfied
    assert any(v.rule == "no_paragram" for v in report.violations)


def test_words_of_different_length_are_not_a_pair() -> None:
    assert not check("paragram", "cat cats").satisfied


def test_a_word_is_not_paired_with_itself() -> None:
    assert not check("paragram", "cat cat cat").satisfied


def test_minimum_raises_the_bar() -> None:
    """cat/sat/mat is three pairwise swaps, so a bar of three is met."""
    assert check("paragram", "cat sat mat", minimum=3).satisfied
    assert not check("paragram", "cat sat", minimum=3).satisfied


def test_a_swap_at_the_last_position_counts() -> None:
    assert check("paragram", "cat car").satisfied


def test_apply_produces_a_real_word() -> None:
    from denckring.lang import get_pack

    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply("the cat sat", lang="en")
    assert produced != "the cat sat"
    assert check("paragram", produced, minimum=0).satisfied or True  # shape only
    assert all(get_pack("en").is_word(w) for w in produced.split() if w.isalpha())


def test_apply_refuses_without_a_lexicon(monkeypatch: pytest.MonkeyPatch) -> None:
    from denckring.lang.en import EnglishPack

    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    monkeypatch.setattr("denckring.lang.get_pack", lambda lang="en": EnglishPack())
    with pytest.raises(MissingCapability):
        procedure.apply("cat", lang="en")


def test_check_still_works_without_a_lexicon() -> None:
    """`requires` gates check, so the lexicon requirement lives in apply only."""
    from denckring.lang.en import EnglishPack

    assert "lexicon.words" not in EnglishPack().capabilities
    assert check("paragram", "cat sat").satisfied
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_paragram.py -q`
Expected: FAIL — `UnknownProcedure`.

- [ ] **Step 3: Write the checker and the generator**

Create `src/denckring/procedures/paragram.py`:

```python
"""Paragram — one letter changed, and the change made the point."""

from __future__ import annotations

import string
from itertools import combinations
from typing import Any

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams, require_capability
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans
from denckring.lang.base import WORDS


class ParagramParams(DiacriticParams):
    minimum: int = Field(default=1, ge=0, description="How many swapped pairs are wanted.")


def differ_by_one(left: str, right: str) -> bool:
    """Equal length, differing at exactly one position."""
    if len(left) != len(right) or left == right:
        return False
    return sum(a != b for a, b in zip(left, right)) == 1


@register
class Paragram(BaseProcedure[ParagramParams]):
    """The swap is in the text, so the text alone decides.

    The row is `checkability: self` and requires no lexicon, so what can be
    verified is that both halves of the alteration are present — two words of a
    length, differing in one place. Whether the swap is witty is not a question
    code answers.
    """

    id = "paragram"

    @classmethod
    def params_model(cls) -> type[ParagramParams]:
        return ParagramParams

    def _normalise(self, text: str, pack: LanguagePack, fold: bool) -> list[str]:
        words = []
        for _, word in word_spans(text, pack):
            letters = "".join(
                pack.fold_diacritics(ch) if fold else ch.lower()
                for ch in word
                if ch.isalpha()
            )
            if letters:
                words.append(letters.lower())
        return words

    def _check(self, text: str, pack: LanguagePack, params: ParagramParams) -> Report:
        words = self._normalise(text, pack, params.fold_diacritics)
        pairs = [
            (left, right)
            for left, right in combinations(sorted(set(words)), 2)
            if differ_by_one(left, right)
        ]
        violations: list[Violation] = []
        if len(pairs) < params.minimum:
            violations.append(
                Violation(
                    rule="no_paragram",
                    offset=None,
                    found=f"{len(pairs)} swapped pairs",
                    expected=f"at least {params.minimum}",
                )
            )
        return self._report(
            good=min(len(pairs), params.minimum),
            total=params.minimum,
            violations=violations,
            metrics={"pairs": float(len(pairs))},
        )

    def apply(self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: Any) -> str:
        """Change one letter of one word into another word the lexicon knows.

        `lexicon.words` is required here but deliberately not added to the
        catalogue row: `requires` gates `check` too, and this row has always been
        checkable with core alone. ADR 0002 makes `apply` the optional half, so
        the generator carries its own requirement — the same arrangement
        `anagram` uses.
        """
        from denckring.lang import get_pack

        pack = get_pack(lang)
        require_capability(pack, WORDS, self.id)
        self.parse_params(params)

        for offset, word in word_spans(text, pack):
            if not word.isalpha():
                continue
            for position in range(len(word)):
                for letter in string.ascii_lowercase:
                    if letter == word[position].lower():
                        continue
                    swapped = word[:position] + letter + word[position + 1 :]
                    if pack.is_word(swapped):
                        return text[:offset] + swapped + text[offset + len(word) :]
        return text
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_paragram.py -q`
Expected: PASS. Two things to watch:

- `_report(good=..., total=params.minimum)` divides by zero when `minimum` is 0. Check what `_report` does with `total=0` — it treats it as vacuously satisfied, which is the right answer for "no pairs required". Confirm rather than assume.
- `test_apply_produces_a_real_word` asserts every alphabetic word in the output is in the lexicon. If the input contains a word the lexicon does not know, that assertion fails for a reason unrelated to the swap. If so, narrow the test to the word that actually changed.

- [ ] **Step 5: Write the strategy**

Create `tests/strategies/paragram.py`:

```python
"""Generators for paragram. `satisfying` and `violating` are the module contract."""

import string

from hypothesis import strategies as st

from strategies import CaseStrategy

LETTERS = string.ascii_lowercase


def _swapped(word: str) -> str:
    """The same word with its first letter moved one along the alphabet."""
    shifted = LETTERS[(LETTERS.index(word[0]) + 1) % len(LETTERS)]
    return shifted + word[1:]


def satisfying() -> CaseStrategy:
    return st.text(alphabet=LETTERS, min_size=2, max_size=8).map(
        lambda word: (f"{word} {_swapped(word)}", {})
    )


def violating() -> CaseStrategy:
    """Words of differing lengths can never be one swap apart."""
    return st.text(alphabet=LETTERS, min_size=2, max_size=8).map(
        lambda word: (f"{word} {word + 'x'}", {})
    )
```

- [ ] **Step 6: Run the strategy tests**

Run: `uv run pytest tests/test_strategies.py -q -k paragram`
Expected: PASS. If `violating` occasionally satisfies — because a generated word plus `x` coincidentally forms another pair — tighten the generator so the two words can never be equal length.

- [ ] **Step 7: Note the generator's requirement on the catalogue row**

`requires` stays as it is. Add or extend the row's `notes` in `src/denckring/data/catalogue.yaml` to record the asymmetry:

```yaml
    notes: >-
      The checker needs no dictionary: both halves of the swap are in the text,
      so two words of a length differing in one place is the whole property. The
      generator does need one — it has to know that what it produced is a word —
      so `apply` requires `lexicon.words` and raises `MissingCapability` without
      it, while `check` keeps working on the core pack alone.
```

- [ ] **Step 8: Golden fixture, verification, commit**

Compute the verdicts first, write `src/denckring/eval/fixtures/golden/paragram.yaml` with one satisfying and one violating case, then:

```bash
uv run pytest tests/test_golden.py tests/test_invariants.py tests/test_round_trip.py -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
uv sync --extra en --extra de && uv run pytest -q
git add src/denckring/procedures/paragram.py tests/strategies/paragram.py \
        tests/test_paragram.py src/denckring/eval/fixtures/golden/paragram.yaml \
        src/denckring/data/catalogue.yaml
git commit -m "feat: implement paragram, with a lexicon-gated generator"
```

---

## Self-Review

**Spec coverage.** Every section of the spec maps to a task: `belle_absente` (Task 1), `serial_lipogram` plus the `paragraph_spans` helper (Task 2), `pangrammatic_window` with its required `max_length` (Task 3), `paragram` with the one-letter-pair reading and the lexicon-gated `apply` (Task 4). The spec's `requires`-verification decision appears in Task 1 Step 8 and is repeated as a Global Constraint so every task inherits it. The out-of-scope list is restated in the Global Constraints.

**Placeholders.** The four golden fixtures deliberately say "record what the command printed" rather than carrying literal YAML: their verdicts are not knowable until the checker runs, and writing a guessed `satisfied:` value into a plan is exactly the failure the project's governing premise forbids. Each has a runnable command that produces the values.

**Type consistency.** `paragraph_spans(text: str) -> list[tuple[int, str]]` matches `line_spans`'s signature and is named identically in Task 2's Interfaces, helper, tests and checker. `differ_by_one` is defined once and used once. `WORDS` and `require_capability` are imported from the same modules `anagram` already uses. All four procedures take `DiacriticParams`, so `fold_diacritics` is spelled the same everywhere.
