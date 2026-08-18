# Catalogue Backlog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the 28 catalogued procedures that need no capability the language packs lack, and correct the seven catalogue rows that turn out to be misdescribed.

**Architecture:** Phased. The 11 `form` rows are pure declaration over the existing `rhyme_scheme.form_report`, which already composes rhyme, metre and refrains. The source-checkable rows fall into three clusters, and each cluster's shared helper is *extracted from* two or three hand-written rows rather than designed ahead of them — the way `form_report` was extracted from real sonnets. Nothing here adds a capability or changes a public signature.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, Hypothesis, ruff, mypy --strict, uv.

**Spec:** `docs/superpowers/specs/2026-08-18-catalogue-backlog-design.md`

## Global Constraints

- Python 3.11+; `mypy --strict src tests`, `ruff check src tests`, `ruff format --check src tests` all clean.
- **Baseline is 2231 tests passing** at branch point `25026fc`. Every task ends green.
- **One module per procedure**, module name equal to the procedure id (ADR 0007). `denckring new <id>` scaffolds module, test, strategy, fixture and catalogue row — use it rather than hand-creating the five files.
- **`check` is mandatory, `apply` is optional** (ADR 0002). A procedure without a working checker is not registered.
- Every procedure subclasses `BaseProcedure[P]`, is decorated `@register`, defines `id`, `params_model()` and `_check()`, and builds its Report with `self._report(...)`. Never construct `Report` directly.
- Procedures decidable only against a source text mix in **`SourceParams`** (gives `source: str`). Procedures comparing letters mix in **`DiacriticParams`** (gives `fold_diacritics: bool`). Both from `denckring.core.base`.
- `apply` signature is exactly `def apply(self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: object) -> str`.
- Text helpers live in `denckring.core.text`: `line_spans(text)` yields `(offset, line)`, `word_spans(text, pack)` yields `(offset, word)`.
- **Controller ruling R1 (binding, overrides task text below):** `form_report` gains a
  `lines: int | None = None` keyword. When given, it checks the line count itself and
  emits `wrong_line_count` with `found=f"{n} lines"`. Task 2 makes this change; every
  later form row passes `lines=` instead of copying a line-count block. Where a task
  below says "copy that block verbatim", pass `lines=` instead.
- **Reuse `denckring.core.prosody`, do not reimplement it.** `stanza_violations(text, pack, patterns)` checks a stanza whose lines each have their own metre, where `patterns[i]` is the sequence of readings acceptable for line `i`; it already emits `wrong_line_count` with `found=f"{n} lines"`. `scheme_violations` checks rhyme, `repeat_to("01", 5)` builds `"0101010101"`, and `form_report` composes scheme, metre and refrains. A form row that writes its own scanner is a defect.
- A `Violation` carries `rule`, `offset`, `found`, `expected`, and optionally `note`. `offset` is an index into the *checked text*, or `None` where no single character is at fault.
- **The scoreboard is an acceptance criterion.** At the end, `uv run denckring status` must read
  `152 catalogued · 126 implementable · 114 implemented · 114 validated · 26 not mechanically checkable`.
- Golden fixtures live in `src/denckring/eval/fixtures/golden/<id>.yaml`; Hypothesis strategies in `tests/strategies/<id>.py` exposing `satisfying()` and `violating()` returning `CaseStrategy`.
- Run the suite with `uv run pytest -q` and the scoreboard with `uv run denckring eval`.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/denckring/data/catalogue.yaml` (modify) | The seven corrections: 4 understated `requires`, 1 rename, 3 reclassifications, plus 24 language declarations. |
| `src/denckring/procedures/<id>.py` (create ×28) | One per procedure. |
| `src/denckring/core/source_compare.py` (create) | The three cluster helpers: `selection_report`, `letter_class_report`, `rearrangement_report`. Extracted in Tasks 6, 7 and 9, never written ahead of them. |
| `src/denckring/eval/fixtures/golden/<id>.yaml` (create ×28) | At least one satisfying and one violating case each. |
| `tests/strategies/<id>.py` (create ×28) | `satisfying()` / `violating()`. |
| `tests/test_catalogue_corrections.py` (create) | Asserts the seven corrections, so they cannot be silently reverted. |
| `tests/test_requires_honesty.py` (create) | Asserts no implemented row declares a capability it never reaches. The defect group B is made of. |
| `CHANGELOG.md` (modify) | The batch entry. |

---

### Task 1: The catalogue corrections

Do this first. Every later task builds on rows whose metadata is correct, and the
rename in particular must not land after code refers to the old id.

**Files:**
- Modify: `src/denckring/data/catalogue.yaml`
- Test: `tests/test_catalogue_corrections.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: corrected rows. Later tasks rely on `multiple_constraint` existing and on
  `word_ladder`/`tmesis` declaring `lexicon.words`, `haikuization`/`spoonerism` declaring `phonemes`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_catalogue_corrections.py`:

```python
"""The catalogue is a published dataset. A row that misstates what a procedure
needs is a defect in it, and these are the seven this batch corrects.
"""

import pytest

from denckring.core import catalogue
from denckring.core.errors import UnknownProcedure

UNDERSTATED = {
    "word_ladder": "lexicon.words",
    "tmesis": "lexicon.words",
    "haikuization": "phonemes",
    "spoonerism": "phonemes",
}

BLOCKED = {
    "homosyntaxism": "pos",
    "verbless_prose": "pos",
    "homophonic_translation": "phonemes.bilingual",
    "perverb": "corpus.proverbs",
}

UNDECIDABLE = ["back_translation", "transduction", "intralingual_translation"]


@pytest.mark.parametrize("procedure_id,capability", sorted(UNDERSTATED.items()))
def test_understated_requires_are_corrected(procedure_id: str, capability: str) -> None:
    assert capability in catalogue.get(procedure_id).requires


@pytest.mark.parametrize("procedure_id,capability", sorted(BLOCKED.items()))
def test_blocked_rows_name_what_they_need(procedure_id: str, capability: str) -> None:
    """A row blocked on a capability nothing provides must still say which one."""
    assert capability in catalogue.get(procedure_id).requires


@pytest.mark.parametrize("procedure_id", UNDECIDABLE)
def test_undecidable_rows_are_reclassified(procedure_id: str) -> None:
    meta = catalogue.get(procedure_id)
    assert meta.checkability == "none"
    assert meta.notes, f"{procedure_id} must record why no criterion exists"


def test_the_generic_composite_row_is_renamed() -> None:
    """Its definition describes any composite constraint, not one named pair."""
    with pytest.raises(UnknownProcedure):
        catalogue.get("univocalic_lipogram_pair")
    assert catalogue.get("multiple_constraint")
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/test_catalogue_corrections.py -q
```

Expected: failures on every test — the corrections are not made yet.

- [ ] **Step 3: Correct the four understated `requires`**

In `src/denckring/data/catalogue.yaml`, add the capability to each row's `requires`
list, keeping the existing entries:

- `word_ladder`: `requires: [tokens, fold_diacritics, lexicon.words]`
- `tmesis`: `requires: [tokens, lexicon.words]`
- `haikuization`: `requires: [tokens, phonemes]`
- `spoonerism`: `requires: [tokens, fold_diacritics, phonemes]`
- `ottava_rima`: `requires: [tokens, phonemes, syllables]` *(controller ruling R2 — it
  scans metre, which reaches the syllable machinery)*
- `ballade`: `requires: [tokens, phonemes, syllables]` *(controller ruling R2, same reason)*

- [ ] **Step 4: Name what the four blocked rows actually need**

These stay unimplemented. Correcting them is the point — a row that understates its
needs looks buildable and is not.

- `homosyntaxism`: `requires: [tokens, pos]`
- `verbless_prose`: `requires: [tokens, pos]`
- `homophonic_translation`: `requires: [tokens, phonemes, phonemes.bilingual]`
- `perverb`: `requires: [tokens, corpus.proverbs]`

Add to each row a `notes` line saying the capability does not exist yet, e.g. for
`homosyntaxism`:

```yaml
    notes: >-
      Blocked: substituting words of the same part of speech needs a `pos`
      capability no pack provides. `verbless_prose` needs the same one.
```

- [ ] **Step 5: Reclassify the three undecidable rows**

Set `checkability: none` and record why, e.g.:

```yaml
  - id: back_translation
    checkability: none
    notes: >-
      No acceptance criterion exists. Deciding that a text was translated onward
      and returned requires translation, not comparison: any difference from the
      source is equally consistent with a bad back-translation and with an
      unrelated text.
```

Use the same shape for `transduction` ("a chain through several languages; the drift
is the point and nothing measures it") and `intralingual_translation` ("register and
period are not mechanically detectable").

- [ ] **Step 6: Rename the composite row**

Change `- id: univocalic_lipogram_pair` to `- id: multiple_constraint`, and update its
`names` to `{ en: Multiple constraint, de: Mehrfachbeschränkung, fr: Contrainte multiple }`.
Keep the definition — it is the accurate half. Add the old id to `aliases` so a search
for it still resolves:

```yaml
    aliases: [univocalic lipogram pair, multiple constraint]
```

- [ ] **Step 7: Run the test and the full suite**

```bash
uv run pytest tests/test_catalogue_corrections.py -q
uv run pytest -q
```

Expected: the new file passes; the suite stays green. If a catalogue-shape test
elsewhere fails on the rename, fix that test — the rename is deliberate.

- [ ] **Step 8: Commit**

```bash
git add src/denckring/data/catalogue.yaml tests/test_catalogue_corrections.py
git commit -m "fix: correct seven misdescribed catalogue rows"
```

---

### Task 2: `sonnet`

**Files:**
- Create: `src/denckring/procedures/sonnet.py`
- Create: `src/denckring/eval/fixtures/golden/sonnet.yaml`
- Create: `tests/strategies/sonnet.py`
- Test: `tests/test_sonnet.py` (create)

**Interfaces:**
- Consumes: `form_report` from `denckring.procedures.rhyme_scheme`.
- Produces: nothing later tasks use.

The catalogue defines this as "Fourteen lines in a fixed metre and rhyme scheme" —
**fixed by the caller, not by the row.** So `scheme` and `metre` are parameters, which
is what keeps this from swallowing `petrarchan_sonnet` and `shakespearean_sonnet`: those
hard-code their scheme, this one is told it. It adds one check they do not make — that
there are exactly fourteen lines.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sonnet.py`:

```python
"""The generic sonnet: fourteen lines, in whatever scheme the caller names."""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams

SHAKESPEAREAN = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the birds will sing before the break of day
the fox will hide beneath the fallen stone
the owl will call across the dark alone
the mice will creep beside the ancient way
the rain will fall upon the open moor
the wind will turn the weather vane around
the door will stand ajar upon the floor
the light will settle softly on the ground
the night will come and close the day at last
the stars will hold the memory of the past"""


def test_fourteen_lines_in_the_named_scheme() -> None:
    report = check("sonnet", SHAKESPEAREAN, scheme="ABABCDCDEFEFGG", metre="01" * 5)
    assert report.satisfied is True


def test_thirteen_lines_is_not_a_sonnet() -> None:
    thirteen = "\n".join(SHAKESPEAREAN.splitlines()[:13])
    report = check("sonnet", thirteen, scheme="ABABCDCDEFEF" + "G", metre="01" * 5)
    assert report.satisfied is False
    assert any(v.rule == "wrong_line_count" for v in report.violations)


def test_the_line_count_violation_says_what_it_wanted() -> None:
    thirteen = "\n".join(SHAKESPEAREAN.splitlines()[:13])
    report = check("sonnet", thirteen, scheme="ABABCDCDEFEFG", metre="01" * 5)
    violation = next(v for v in report.violations if v.rule == "wrong_line_count")
    assert violation.found == "13 lines"
    assert violation.expected == "14 lines"


def test_a_scheme_of_the_wrong_length_is_rejected_not_ignored() -> None:
    """A 12-letter scheme cannot describe a sonnet; accepting it would check nothing."""
    with pytest.raises(InvalidParams):
        check("sonnet", SHAKESPEAREAN, scheme="ABABCDCDEFEF", metre="01" * 5)
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/test_sonnet.py -q
```

Expected: FAIL — `UnknownProcedure: No procedure with id 'sonnet'`.

- [ ] **Step 3: Implement**

Create `src/denckring/procedures/sonnet.py`:

```python
"""Sonnet — fourteen lines in a fixed metre and rhyme scheme.

Generic where `petrarchan_sonnet` and `shakespearean_sonnet` are specific: those
hard-code their scheme, this one is told it. What it adds is the line count, which
is the one property every sonnet shares.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.rhyme_scheme import form_report

LINES = 14


class SonnetParams(BaseModel):
    scheme: str = Field(
        default="ABABCDCDEFEFGG",
        description="Rhyme pattern, one letter per line. Must be fourteen letters.",
    )
    metre: str = Field(
        default="01" * 5,
        description="Stress pattern per line; 0 unstressed, 1 stressed.",
    )

    @field_validator("scheme")
    @classmethod
    def _fourteen_letters(cls, value: str) -> str:
        letters = [ch for ch in value if ch.isalpha()]
        if len(letters) != LINES:
            raise ValueError(f"scheme must name {LINES} lines, got {len(letters)}")
        return value


@register
class Sonnet(BaseProcedure[SonnetParams]):
    """Fourteen lines, plus whatever scheme and metre the caller names."""

    id = "sonnet"

    @classmethod
    def params_model(cls) -> type[SonnetParams]:
        return SonnetParams

    def _check(self, text: str, pack: LanguagePack, params: SonnetParams) -> Report:
        lines = list(line_spans(text))
        result = form_report(text, pack, scheme=params.scheme, metre=params.metre)
        violations = list(result.violations)
        good = result.good
        total = result.total + 1
        if len(lines) == LINES:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected=f"{LINES} lines",
                )
            )
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={
                "lines": float(len(lines)),
                "estimated_words": float(result.estimated),
            },
        )
```

- [ ] **Step 4: Run the test**

```bash
uv run pytest tests/test_sonnet.py -q
```

Expected: PASS.

- [ ] **Step 5: Add the golden fixture**

Create `src/denckring/eval/fixtures/golden/sonnet.yaml`:

```yaml
procedure: sonnet
lang: en
cases:
  - name: shakespearean-scheme
    source: constructed example
    text: |-
      the cat can see the moon above the tree
      the dog will run across the field today
      a bird can fly around the house at three
      the sun will set behind the hill in may
      the birds will sing before the break of day
      the fox will hide beneath the fallen stone
      the owl will call across the dark alone
      the mice will creep beside the ancient way
      the rain will fall upon the open moor
      the wind will turn the weather vane around
      the door will stand ajar upon the floor
      the light will settle softly on the ground
      the night will come and close the day at last
      the stars will hold the memory of the past
    params: { scheme: ABABCDCDEFEFGG, metre: "0101010101" }
    satisfied: true
  - name: thirteen-lines
    source: constructed counterexample
    text: |-
      the cat can see the moon above the tree
      the dog will run across the field today
      a bird can fly around the house at three
      the sun will set behind the hill in may
      the birds will sing before the break of day
      the fox will hide beneath the fallen stone
      the owl will call across the dark alone
      the mice will creep beside the ancient way
      the rain will fall upon the open moor
      the wind will turn the weather vane around
      the door will stand ajar upon the floor
      the light will settle softly on the ground
      the night will come and close the day at last
    params: { scheme: ABABCDCDEFEFG, metre: "0101010101" }
    satisfied: false
```

- [ ] **Step 6: Add the Hypothesis strategy**

Create `tests/strategies/sonnet.py`:

```python
"""Generators for sonnet.

A valid instance cannot be generated blind — the rhyme families must be chosen in
advance — so these sample verified texts, as `rhyme_royal` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the birds will sing before the break of day
the fox will hide beneath the fallen stone
the owl will call across the dark alone
the mice will creep beside the ancient way
the rain will fall upon the open moor
the wind will turn the weather vane around
the door will stand ajar upon the floor
the light will settle softly on the ground
the night will come and close the day at last
the stars will hold the memory of the past"""

VIOLATING = "\n".join(CONFORMING.splitlines()[:13])

PARAMS: dict[str, object] = {"scheme": "ABABCDCDEFEFGG", "metre": "0101010101"}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, dict(PARAMS)))
```

- [ ] **Step 7: Run the suite and the scoreboard**

```bash
uv run pytest -q
uv run denckring eval
```

Expected: green. The scoreboard gains one implemented, one validated row.

- [ ] **Step 8: Commit**

```bash
git add src/denckring/procedures/sonnet.py src/denckring/eval/fixtures/golden/sonnet.yaml tests/strategies/sonnet.py tests/test_sonnet.py
git commit -m "feat: implement sonnet"
```

---

### Task 3: The stanzaic forms — `ottava_rima`, `spenserian_stanza`, `ballade`

**Files:**
- Create: `src/denckring/procedures/{ottava_rima,spenserian_stanza,ballade}.py`
- Create: `src/denckring/eval/fixtures/golden/{ottava_rima,spenserian_stanza,ballade}.yaml`
- Create: `tests/strategies/{ottava_rima,spenserian_stanza,ballade}.py`
- Test: `tests/test_stanzaic_forms.py` (create)

**Interfaces:**
- Consumes: `form_report` (`denckring.procedures.rhyme_scheme`), `stanza_violations` and `repeat_to` (`denckring.core.prosody`).
- Produces: nothing later tasks use.

Three rows, one shape: a fixed line count, a fixed scheme, a metre. `spenserian_stanza`
is the one that needs `stanza_violations` rather than `form_report`, because its ninth
line is an alexandrine and the other eight are pentameters — a single `metre=` string
cannot say that.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_stanzaic_forms.py`:

```python
"""Three stanzas that differ only in length, scheme and metre."""

from denckring import check

OTTAVA = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the owl will call across the dark at sea
the fox will hide beneath the fallen way
the mice will creep beside the ancient stone
the birds will sing before the day has flown"""

SPENSERIAN = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the birds will sing before the break of day
the fox will hide beneath the fallen stone
the owl will call across the dark alone
the mice will creep beside the ancient way
the rain will fall upon the open field before the dawn"""


def test_ottava_rima_accepts_abababcc() -> None:
    assert check("ottava_rima", OTTAVA).satisfied is True


def test_ottava_rima_rejects_the_wrong_line_count() -> None:
    report = check("ottava_rima", "\n".join(OTTAVA.splitlines()[:7]))
    assert report.satisfied is False
    assert any(v.rule == "wrong_line_count" for v in report.violations)


def test_spenserian_final_line_is_an_alexandrine() -> None:
    """Eight pentameters and a hexameter. A ninth pentameter is the classic error."""
    assert check("spenserian_stanza", SPENSERIAN).satisfied is True
    short_last = "\n".join(SPENSERIAN.splitlines()[:8] + ["the rain will fall upon the moor"])
    assert check("spenserian_stanza", short_last).satisfied is False


def test_ballade_requires_the_refrain_to_repeat() -> None:
    """Three eight-line stanzas and a four-line envoi, every stanza ending alike."""
    stanza = OTTAVA.splitlines()[:7] + ["and that is all the summer had to say"]
    text = "\n".join(stanza * 3 + stanza[4:])
    assert check("ballade", text).satisfied is True
    broken = "\n".join(stanza * 3 + stanza[4:7] + ["a different closing line entirely"])
    report = check("ballade", broken)
    assert report.satisfied is False
    assert any(v.rule == "broken_refrain" for v in report.violations)
```

- [ ] **Step 2: Run them and watch them fail**

```bash
uv run pytest tests/test_stanzaic_forms.py -q
```

Expected: FAIL — none of the three procedures exist.

- [ ] **Step 3: Implement `ottava_rima`**

Create `src/denckring/procedures/ottava_rima.py`:

```python
"""Ottava rima — eight hendecasyllables rhyming ABABABCC."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import repeat_to
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report

SCHEME = "ABABABCC"


@register
class OttavaRima(BaseProcedure[BaseModel]):
    """Assembled from the shared rhyme and metre checks."""

    id = "ottava_rima"

    @classmethod
    def params_model(cls) -> type[BaseModel]:
        return BaseModel

    def _check(self, text: str, pack: LanguagePack, params: BaseModel) -> Report:
        result = form_report(text, pack, scheme=SCHEME, metre=repeat_to("01", 5))
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={
                "checks": float(result.total),
                "estimated_words": float(result.estimated),
            },
        )
```

Note: `form_report` does not itself count lines. Add the count check the way `sonnet`
does in Task 2 — copy that block verbatim, with `LINES = 8`.

- [ ] **Step 4: Implement `spenserian_stanza`**

Create `src/denckring/procedures/spenserian_stanza.py`:

```python
"""Spenserian stanza — ABABBCBCC, eight pentameters and a closing alexandrine.

The last line is the form. A ninth pentameter is the error this checks for, so the
metre is per-line and `stanza_violations` does the scanning rather than `form_report`,
whose single `metre=` string cannot say "all but the last".
"""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import repeat_to, scheme_violations, stanza_violations
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register

SCHEME = "ABABBCBCC"
PENTAMETER = repeat_to("01", 5)
ALEXANDRINE = repeat_to("01", 6)
PATTERNS = [[PENTAMETER]] * 8 + [[ALEXANDRINE]]


@register
class SpenserianStanza(BaseProcedure[BaseModel]):
    """Nine lines, the ninth one foot longer than the rest."""

    id = "spenserian_stanza"

    @classmethod
    def params_model(cls) -> type[BaseModel]:
        return BaseModel

    def _check(self, text: str, pack: LanguagePack, params: BaseModel) -> Report:
        metre = stanza_violations(text, pack, PATTERNS)
        found, matched, checks = scheme_violations(text, pack, SCHEME)
        return self._report(
            good=metre.good + matched,
            total=metre.total + checks,
            violations=metre.violations + found,
            metrics={
                "checks": float(metre.total + checks),
                "estimated_words": float(metre.estimated),
            },
        )
```

- [ ] **Step 5: Implement `ballade`**

Create `src/denckring/procedures/ballade.py`:

```python
"""Ballade — three ababbcbc stanzas and a bcbc envoi, every part ending on the refrain.

The refrain is the form's point: the same line closes all four parts. `form_report`
already checks refrains by line index, so this row is three constants.
"""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import repeat_to
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.rhyme_scheme import form_report

SCHEME = "ababbcbc" * 3 + "bcbc"
LINES = 28
#: The refrain closes stanza one at index 7, and must return at 15, 23 and 27.
REFRAINS = [(7, 15), (7, 23), (7, 27)]


@register
class Ballade(BaseProcedure[BaseModel]):
    """Twenty-eight lines, four of them the same line."""

    id = "ballade"

    @classmethod
    def params_model(cls) -> type[BaseModel]:
        return BaseModel

    def _check(self, text: str, pack: LanguagePack, params: BaseModel) -> Report:
        lines = line_spans(text)
        result = form_report(
            text, pack, scheme=SCHEME, metre=repeat_to("01", 4), refrains=REFRAINS
        )
        violations = list(result.violations)
        good = result.good
        total = result.total + 1
        if len(lines) == LINES:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected=f"{LINES} lines",
                )
            )
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={
                "lines": float(len(lines)),
                "estimated_words": float(result.estimated),
            },
        )
```

- [ ] **Step 6: Run the tests**

```bash
uv run pytest tests/test_stanzaic_forms.py -q
```

Expected: PASS. If the ballade metre rejects the constructed example, relax
`metre=` to `None` and record in the docstring that the ballade's line length varies
by tradition — do **not** loosen the refrain or scheme checks, which are the form.

- [ ] **Step 7: Add fixtures and strategies**

For each of the three, create `src/denckring/eval/fixtures/golden/<id>.yaml` with one
satisfying and one violating case, and `tests/strategies/<id>.py` exposing
`satisfying()` and `violating()`. Follow the exact shape given in Task 2, Steps 5 and 6,
substituting the texts from `tests/test_stanzaic_forms.py`.

- [ ] **Step 8: Full suite and commit**

```bash
uv run pytest -q && uv run denckring eval
git add src/denckring/procedures/ottava_rima.py src/denckring/procedures/spenserian_stanza.py src/denckring/procedures/ballade.py src/denckring/eval/fixtures/golden/ottava_rima.yaml src/denckring/eval/fixtures/golden/spenserian_stanza.yaml src/denckring/eval/fixtures/golden/ballade.yaml tests/strategies/ottava_rima.py tests/strategies/spenserian_stanza.py tests/strategies/ballade.py tests/test_stanzaic_forms.py
git commit -m "feat: implement ottava_rima, spenserian_stanza and ballade"
```

---

### Task 4: `rondeau` and `ghazal` — the two with a repeating element

**Files:**
- Create: `src/denckring/procedures/{rondeau,ghazal}.py`
- Create: fixtures and strategies for both
- Test: `tests/test_repeating_forms.py` (create)

**Interfaces:**
- Consumes: `scheme_violations`, `line_spans`, `word_spans`.
- Produces: nothing later tasks use.

Neither fits `form_report`'s refrain check, which compares whole lines.

- **`rondeau`**: fifteen lines. Lines 9 and 15 are the *rentrement* — the opening
  **words** of line 1, not the whole line, and they do not rhyme. So the scheme covers
  the thirteen full lines and the rentrement is a prefix check.
- **`ghazal`**: couplets ending in a repeated word (the *radif*), with the rhyme
  (*qafia*) immediately before it. Both lines of the opening couplet carry it; then
  every second line does.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_repeating_forms.py`:

```python
"""Two forms whose repeating element is a fragment, not a line."""

from denckring import check

RONDEAU = """the summer holds the door
a bird will cross the sky
the light will slowly die
and settle on the floor
the rain will come once more
the wind will wander by
the summer holds
the field will ask no more
the swallows leave the shore
and no one answers why
the stones will not reply
the year has closed its store
the summer holds"""

GHAZAL = """i cannot find the road tonight
the lamps have all been slowed tonight
the river takes another turn
and leaves its heavy load tonight
the letters that i never sent
are lying in the code tonight"""


def test_rondeau_accepts_the_rentrement() -> None:
    report = check("rondeau", RONDEAU, rentrement_words=3)
    assert any(v.rule == "wrong_line_count" for v in report.violations) is False


def test_rondeau_rejects_a_changed_rentrement() -> None:
    broken = RONDEAU.replace("the summer holds\nthe field", "the winter holds\nthe field")
    report = check("rondeau", broken, rentrement_words=3)
    assert report.satisfied is False
    assert any(v.rule == "broken_rentrement" for v in report.violations)


def test_ghazal_requires_the_radif_on_every_second_line() -> None:
    assert check("ghazal", GHAZAL).satisfied is True


def test_ghazal_names_the_line_that_drops_the_radif() -> None:
    broken = GHAZAL.replace("in the code tonight", "in the code today")
    report = check("ghazal", broken)
    assert report.satisfied is False
    violation = next(v for v in report.violations if v.rule == "missing_radif")
    assert violation.expected == "tonight"
```

- [ ] **Step 2: Run them and watch them fail**

```bash
uv run pytest tests/test_repeating_forms.py -q
```

Expected: FAIL — neither procedure exists.

- [ ] **Step 3: Implement `rondeau`**

Create `src/denckring/procedures/rondeau.py`:

```python
"""Rondeau — fifteen lines on two rhymes, with a rentrement closing two of them.

The rentrement is the opening *words* of the first line, not the whole line, and it
does not rhyme. That is why this cannot use `form_report`'s refrain check, which
compares whole lines: doing so would demand a rhyme the form forbids.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.prosody import scheme_violations
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans

#: The thirteen full lines. Indices 6 and 12 are the rentrement and carry no letter.
SCHEME = "AABBAAABAABBA"
RENTREMENT_LINES = (6, 12)
LINES = 13 + len(RENTREMENT_LINES)


class RondeauParams(BaseModel):
    rentrement_words: int = Field(
        default=3, ge=1, description="How many opening words the rentrement repeats."
    )


@register
class Rondeau(BaseProcedure[RondeauParams]):
    """Two rhymes across thirteen lines, plus two unrhymed rentrements."""

    id = "rondeau"

    @classmethod
    def params_model(cls) -> type[RondeauParams]:
        return RondeauParams

    def _check(self, text: str, pack: LanguagePack, params: RondeauParams) -> Report:
        lines = [line for _, line in line_spans(text)]
        violations: list[Violation] = []
        good = 0
        total = 1
        if len(lines) == LINES:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected=f"{LINES} lines",
                )
            )
        if lines:
            opening = " ".join(lines[0].split()[: params.rentrement_words]).casefold()
            for index in RENTREMENT_LINES:
                total += 1
                actual = lines[index].strip().casefold() if index < len(lines) else ""
                if actual == opening:
                    good += 1
                else:
                    violations.append(
                        Violation(
                            rule="broken_rentrement",
                            offset=None,
                            found=actual,
                            expected=opening,
                        )
                    )
        rhyming = "\n".join(
            line for index, line in enumerate(lines) if index not in RENTREMENT_LINES
        )
        found, matched, checks = scheme_violations(rhyming, pack, SCHEME)
        return self._report(
            good=good + matched,
            total=total + checks,
            violations=violations + found,
            metrics={"lines": float(len(lines))},
        )
```

- [ ] **Step 4: Implement `ghazal`**

Create `src/denckring/procedures/ghazal.py`:

```python
"""Ghazal — couplets closing on a repeated word, the radif.

The radif is taken from the opening couplet rather than given as a parameter: the
form defines it as whatever word the first couplet repeats, so asking the caller
would let a text declare its own compliance.
"""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans, word_spans


@register
class Ghazal(BaseProcedure[BaseModel]):
    """Every second line ends on the word both lines of the first couplet end on."""

    id = "ghazal"

    @classmethod
    def params_model(cls) -> type[BaseModel]:
        return BaseModel

    def _check(self, text: str, pack: LanguagePack, params: BaseModel) -> Report:
        lines = [line for _, line in line_spans(text)]
        violations: list[Violation] = []
        if len(lines) < 2:
            return self._report(
                good=0,
                total=1,
                violations=[
                    Violation(
                        rule="wrong_line_count",
                        offset=None,
                        found=f"{len(lines)} lines",
                        expected="at least 2 lines",
                    )
                ],
                metrics={"couplets": 0.0},
            )

        def last_word(line: str) -> str:
            words = [word.casefold() for _, word in word_spans(line, pack)]
            return words[-1] if words else ""

        radif = last_word(lines[0])
        good = 0
        total = 0
        # The opening couplet carries the radif on both lines; thereafter every second.
        carriers = [1] + list(range(3, len(lines), 2))
        for index in carriers:
            total += 1
            actual = last_word(lines[index])
            if actual == radif:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="missing_radif",
                        offset=None,
                        found=actual,
                        expected=radif,
                    )
                )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"couplets": float(len(lines) // 2)},
        )
```

- [ ] **Step 5: Controller ruling R3 — add the qafia check to `ghazal`**

A ghazal is radif **and** qafia: the repeated end word, and a rhyme immediately before
it. The check above tests only the radif, which both under-specifies the form and leaves
the row's declared `phonemes` capability unreached — Task 16's honesty test would fail
on it.

Add: for each line carrying the radif, the word *before* the radif must rhyme with the
word before the radif in line 1. Use `pack.rhyme_key(word)`. Emit `rule="broken_qafia"`
with the two keys in `found`/`expected`. Score it as one more check rather than a hard
gate — real ghazals vary in how strictly the qafia is kept.

Add this test to `tests/test_repeating_forms.py`:

```python
def test_ghazal_checks_the_rhyme_before_the_radif() -> None:
    broken = GHAZAL.replace("been slowed tonight", "been painted tonight")
    report = check("ghazal", broken)
    assert any(v.rule == "broken_qafia" for v in report.violations)
```

- [ ] **Step 6: Run the tests**

```bash
uv run pytest tests/test_repeating_forms.py -q
```

Expected: PASS.

- [ ] **Step 6: Fixtures, strategies, suite and commit**

Add both fixtures and both strategies in the Task 2 shape, then:

```bash
uv run pytest -q && uv run denckring eval
git add src/denckring/procedures/rondeau.py src/denckring/procedures/ghazal.py src/denckring/eval/fixtures/golden/rondeau.yaml src/denckring/eval/fixtures/golden/ghazal.yaml tests/strategies/rondeau.py tests/strategies/ghazal.py tests/test_repeating_forms.py
git commit -m "feat: implement rondeau and ghazal"
```

---

### Task 5: `curtal_sonnet`, `englyn`, `clerihew`

**Files:**
- Create: `src/denckring/procedures/{curtal_sonnet,englyn,clerihew}.py`
- Create: fixtures and strategies for all three
- Test: `tests/test_short_forms.py` (create)

**Interfaces:**
- Consumes: `form_report`, `scheme_violations`, and `pattern_result` from `denckring.procedures.syllable_count`.
- Produces: nothing later tasks use.

- **`curtal_sonnet`** (Hopkins): eleven lines, ABCABC DBCDC — a sonnet shrunk by a
  consistent fraction, not truncated.
- **`englyn`** is **syllabic, not accentual**: four lines of 10, 6, 7 and 7 syllables.
  Use `pattern_result`, the same helper `haiku` uses, not the metre scanner.
- **`clerihew`** is deliberately metrically irregular — that irregularity is the joke.
  Check the AABB rhyme and the four lines, and check **nothing** about metre. Say so in
  the docstring, or someone will "fix" it later.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_short_forms.py`:

```python
"""Three short forms: one shrunken sonnet, one syllabic, one deliberately loose."""

from denckring import check

CURTAL = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the owl will call across the dark at sea
the fox will hide beneath the fallen way
the mice will creep beside the ancient stone
the birds will sing before the break of day
the rain will fall upon the open moor
the wind will turn the weather vane alone
the light has gone"""

ENGLYN = """the summer evening settles on the water
beside the older stone
the swallows turn for home
the river answers on its own"""

CLERIHEW = """sir humphrey davy
abominated gravy
he lived in the odium
of having discovered sodium"""


def test_curtal_sonnet_is_eleven_lines() -> None:
    assert check("curtal_sonnet", CURTAL).satisfied is True
    assert check("curtal_sonnet", "\n".join(CURTAL.splitlines()[:10])).satisfied is False


def test_englyn_counts_syllables_not_stresses() -> None:
    report = check("englyn", ENGLYN)
    assert "estimated_words" in report.metrics


def test_englyn_rejects_the_wrong_syllable_pattern() -> None:
    wrong = "\n".join(["a short first line"] + ENGLYN.splitlines()[1:])
    assert check("englyn", wrong).satisfied is False


def test_clerihew_checks_rhyme_and_says_nothing_about_metre() -> None:
    """Its metre is irregular on purpose; checking it would reject every real one."""
    assert check("clerihew", CLERIHEW).satisfied is True
    assert all("metre" not in v.rule for v in check("clerihew", CLERIHEW).violations)
```

- [ ] **Step 2: Run them and watch them fail**

```bash
uv run pytest tests/test_short_forms.py -q
```

Expected: FAIL — none of the three exist.

- [ ] **Step 3: Implement all three**

`src/denckring/procedures/curtal_sonnet.py`:

```python
"""Curtal sonnet — Hopkins's eleven-line contraction, rhyming ABCABCDBCDC."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import repeat_to
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.rhyme_scheme import form_report

SCHEME = "ABCABCDBCDC"
LINES = 11


@register
class CurtalSonnet(BaseProcedure[BaseModel]):
    """A sonnet shrunk by a consistent fraction, not a sonnet cut short."""

    id = "curtal_sonnet"

    @classmethod
    def params_model(cls) -> type[BaseModel]:
        return BaseModel

    def _check(self, text: str, pack: LanguagePack, params: BaseModel) -> Report:
        lines = line_spans(text)
        result = form_report(text, pack, scheme=SCHEME, metre=repeat_to("01", 5))
        violations = list(result.violations)
        good = result.good
        total = result.total + 1
        if len(lines) == LINES:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected=f"{LINES} lines",
                )
            )
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={
                "lines": float(len(lines)),
                "estimated_words": float(result.estimated),
            },
        )
```

`src/denckring/procedures/englyn.py`:

```python
"""Englyn — a Welsh quatrain of ten, six, seven and seven syllables.

Syllabic, not accentual. Welsh metre counts syllables and this checks what the form
counts, so it uses the same helper `haiku` does rather than the stress scanner.
"""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import scheme_violations
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.syllable_count import pattern_result

PATTERN = [10, 6, 7, 7]


SCHEME = "AAAA"


@register
class Englyn(BaseProcedure[BaseModel]):
    """Syllable pattern and the single rhyme. The cynghanedd is not code's business.

    *Unodl* means one rhyme: all four lines share it. Checking syllables alone would
    under-specify the form and leave the row's declared `phonemes` unreached
    (controller ruling R4).
    """

    id = "englyn"

    @classmethod
    def params_model(cls) -> type[BaseModel]:
        return BaseModel

    def _check(self, text: str, pack: LanguagePack, params: BaseModel) -> Report:
        syllabic = pattern_result(text, pack, PATTERN)._asdict()
        found, matched, checks = scheme_violations(text, pack, SCHEME)
        return self._report(
            good=syllabic["good"] + matched,
            total=syllabic["total"] + checks,
            violations=syllabic["violations"] + found,
            metrics=syllabic["metrics"],
        )
```

`src/denckring/procedures/clerihew.py`:

```python
"""Clerihew — four lines rhyming AABB, the first naming a person.

**No metre check, deliberately.** The clerihew's metre is irregular by design; the
lopsidedness is the joke. A metre check here would reject every real clerihew,
including Bentley's own.
"""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import scheme_violations
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans

SCHEME = "AABB"
LINES = 4


@register
class Clerihew(BaseProcedure[BaseModel]):
    """Rhyme and line count only."""

    id = "clerihew"

    @classmethod
    def params_model(cls) -> type[BaseModel]:
        return BaseModel

    def _check(self, text: str, pack: LanguagePack, params: BaseModel) -> Report:
        lines = line_spans(text)
        violations: list[Violation] = []
        good = 0
        total = 1
        if len(lines) == LINES:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected=f"{LINES} lines",
                )
            )
        found, matched, checks = scheme_violations(text, pack, SCHEME)
        return self._report(
            good=good + matched,
            total=total + checks,
            violations=violations + found,
            metrics={"lines": float(len(lines))},
        )
```

- [ ] **Step 4: Run the tests, then fixtures, strategies, suite and commit**

```bash
uv run pytest tests/test_short_forms.py -q
# add the three fixtures and three strategies in the Task 2 shape
uv run pytest -q && uv run denckring eval
git add src/denckring/procedures/curtal_sonnet.py src/denckring/procedures/englyn.py src/denckring/procedures/clerihew.py src/denckring/eval/fixtures/golden/curtal_sonnet.yaml src/denckring/eval/fixtures/golden/englyn.yaml src/denckring/eval/fixtures/golden/clerihew.yaml tests/strategies/curtal_sonnet.py tests/strategies/englyn.py tests/strategies/clerihew.py tests/test_short_forms.py
git commit -m "feat: implement curtal_sonnet, englyn and clerihew"
```

---

### Task 6: `alliterative_verse` and `assonance_constraint`

**Files:**
- Create: `src/denckring/procedures/{alliterative_verse,assonance_constraint}.py`
- Create: fixtures and strategies for both
- Test: `tests/test_line_sound.py` (create)

**Interfaces:**
- Consumes: `word_spans`, `line_spans`, `pack.phonemes`.
- Produces: nothing later tasks use.

These are the two `form` rows that are **not stanzaic**. They constrain sound *within*
the line, so they sit alongside `form_report` rather than inside it. Neither has a line
count, a scheme or a metre.

- `alliterative_verse` requires at least three of the four stressed words in a line to
  share an initial sound. `requires` is `[fold_diacritics, tokens]` — no phonemes — so
  it compares **initial letters**, and the docstring must record that this is an
  approximation of initial *sound*, the same way other rows record theirs.
- `assonance_constraint` requires a repeated vowel sound across the line, which
  `requires: [phonemes, tokens]` supports properly.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_line_sound.py`:

```python
"""Two form rows that constrain sound inside the line rather than across lines."""

from denckring import check

ALLITERATIVE = """in a summer season when soft was the sun
i shaped me in shrouds as a shepherd were
bright was the bank where the birds were bold
in a wide wild wood i wandered west"""


def test_alliterative_verse_accepts_three_in_four() -> None:
    assert check("alliterative_verse", ALLITERATIVE, minimum=3).satisfied is True


def test_alliterative_verse_names_the_line_that_fails() -> None:
    broken = ALLITERATIVE.replace(
        "in a wide wild wood i wandered west", "the quiet evening came down slowly"
    )
    report = check("alliterative_verse", broken, minimum=3)
    assert report.satisfied is False
    assert any(v.rule == "too_few_alliterating" for v in report.violations)


def test_assonance_repeats_a_vowel_across_the_line() -> None:
    report = check("assonance_constraint", "the rain in spain stays mainly plain")
    assert report.satisfied is True


def test_assonance_rejects_a_line_with_no_repeated_vowel() -> None:
    report = check("assonance_constraint", "the dog runs")
    assert report.satisfied is False
```

- [ ] **Step 2: Run them and watch them fail**

```bash
uv run pytest tests/test_line_sound.py -q
```

Expected: FAIL — neither procedure exists.

- [ ] **Step 3: Implement `alliterative_verse`**

Create `src/denckring/procedures/alliterative_verse.py`:

```python
"""Alliterative verse — most words in a line beginning on the same sound.

**Initial letter stands in for initial sound.** The catalogue row requires only
`tokens` and `fold_diacritics`, not `phonemes`, so this compares first letters. That
is an approximation: it reads *knight* and *king* as alliterating, which Old English
metre would not. It is recorded here rather than hidden, and the row would need
`phonemes` in `requires` to do better.
"""

from __future__ import annotations

from collections import Counter

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans, word_spans


class AlliterativeVerseParams(DiacriticParams):
    minimum: int = Field(
        default=3, ge=2, description="How many words in a line must share an initial."
    )


@register
class AlliterativeVerse(BaseProcedure[AlliterativeVerseParams]):
    """Each line must carry `minimum` words on one initial."""

    id = "alliterative_verse"

    @classmethod
    def params_model(cls) -> type[AlliterativeVerseParams]:
        return AlliterativeVerseParams

    def _check(
        self, text: str, pack: LanguagePack, params: AlliterativeVerseParams
    ) -> Report:
        violations: list[Violation] = []
        good = 0
        total = 0
        for offset, line in line_spans(text):
            words = [word for _, word in word_spans(line, pack)]
            if not words:
                continue
            total += 1
            initials = Counter(
                pack.fold_diacritics(word[0]).casefold()
                if params.fold_diacritics
                else word[0].casefold()
                for word in words
                if word
            )
            best, count = initials.most_common(1)[0]
            if count >= params.minimum:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="too_few_alliterating",
                        offset=offset,
                        found=f"{count} on {best!r}",
                        expected=f"{params.minimum} sharing an initial",
                    )
                )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"lines": float(total)},
        )
```

`LanguagePack.fold_diacritics(ch) -> str` folds a single character; there is no
`fold(word)`. Compare the folded first character, as above.

- [ ] **Step 4: Implement `assonance_constraint`**

Create `src/denckring/procedures/assonance_constraint.py`:

```python
"""Assonance — a vowel sound repeated across the words of a line.

Unlike `alliterative_verse`, this row declares `phonemes`, so it compares vowel
phonemes rather than written vowels and reads *rain* and *stays* as assonant.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans, word_spans

#: A CMU-style vowel phoneme carries a stress digit; a consonant does not.
def _vowels(word: str, pack: LanguagePack) -> list[str]:
    return [p.rstrip("012") for p in pack.phonemes(word) if p[-1:].isdigit()]


class AssonanceParams(BaseModel):
    minimum: int = Field(
        default=2, ge=2, description="How many words in a line must share a vowel."
    )


@register
class AssonanceConstraint(BaseProcedure[AssonanceParams]):
    """Each line must carry `minimum` words sharing one vowel sound."""

    id = "assonance_constraint"

    @classmethod
    def params_model(cls) -> type[AssonanceParams]:
        return AssonanceParams

    def _check(self, text: str, pack: LanguagePack, params: AssonanceParams) -> Report:
        violations: list[Violation] = []
        good = 0
        total = 0
        for offset, line in line_spans(text):
            words = [word for _, word in word_spans(line, pack)]
            if not words:
                continue
            total += 1
            carried: Counter[str] = Counter()
            for word in words:
                carried.update(set(_vowels(word, pack)))
            best, count = carried.most_common(1)[0] if carried else ("", 0)
            if count >= params.minimum:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="no_repeated_vowel",
                        offset=offset,
                        found=f"{count} on {best!r}" if best else "no vowels found",
                        expected=f"{params.minimum} words sharing a vowel",
                    )
                )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"lines": float(total)},
        )
```

`LanguagePack.phonemes(word) -> list[str]` is confirmed to exist and returns
CMU-style phonemes, so the vowel filter above is correct as written.

- [ ] **Step 5: Run, add fixtures and strategies, suite, commit**

```bash
uv run pytest tests/test_line_sound.py -q
# add both fixtures and both strategies in the Task 2 shape
uv run pytest -q && uv run denckring eval
git add src/denckring/procedures/alliterative_verse.py src/denckring/procedures/assonance_constraint.py src/denckring/eval/fixtures/golden/alliterative_verse.yaml src/denckring/eval/fixtures/golden/assonance_constraint.yaml tests/strategies/alliterative_verse.py tests/strategies/assonance_constraint.py tests/test_line_sound.py
git commit -m "feat: implement alliterative_verse and assonance_constraint"
```

**The eleven form rows are now complete.** `uv run denckring status` should read
`97 implemented`.

---

### Task 7: Letter-class cluster — `homoconsonantism`, `homovocalism`

**Files:**
- Create: `src/denckring/procedures/{homoconsonantism,homovocalism}.py`
- Create: `src/denckring/core/source_compare.py`
- Create: fixtures and strategies for both
- Test: `tests/test_letter_class.py` (create)

**Interfaces:**
- Consumes: `SourceParams`, `DiacriticParams`, `letter_spans`.
- Produces: **`letter_class_report(text, source, pack, *, keep, fold) -> ClassResult`** in
  `denckring.core.source_compare`, where `keep` is `"consonants"` or `"vowels"`.
  `ClassResult` is a NamedTuple `(violations, good, total)`. Task 8 and Task 10 add
  further functions to this same module.

These two are the same procedure with the classes swapped: one keeps the consonants of
the source in order and replaces every vowel, the other does the reverse. Write
`homoconsonantism` first, then write `homovocalism` and let the helper fall out of what
they share — do not write the helper first.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_letter_class.py`:

```python
"""One skeleton kept, the other class replaced. Two rows, one function."""

from denckring import check

SOURCE = "the cat sat"


def test_homoconsonantism_keeps_the_consonant_skeleton() -> None:
    """th-c-t-s-t preserved in order, every vowel free to change."""
    report = check("homoconsonantism", "at the coast, it sits", source=SOURCE)
    assert report.satisfied is True


def test_homoconsonantism_rejects_a_changed_consonant() -> None:
    report = check("homoconsonantism", "the bat sat", source=SOURCE)
    assert report.satisfied is False
    violation = next(v for v in report.violations if v.rule == "wrong_consonant")
    assert violation.expected == "c"


def test_homovocalism_keeps_the_vowels() -> None:
    report = check("homovocalism", "he ran back", source="the cat sat")
    assert isinstance(report.satisfied, bool)


def test_homovocalism_rejects_a_changed_vowel() -> None:
    report = check("homovocalism", "the cot sat", source=SOURCE)
    assert report.satisfied is False
    assert any(v.rule == "wrong_vowel" for v in report.violations)
```

- [ ] **Step 2: Run them and watch them fail**

```bash
uv run pytest tests/test_letter_class.py -q
```

Expected: FAIL — neither procedure exists.

- [ ] **Step 3: Write `homoconsonantism` by hand, with no helper**

Create `src/denckring/procedures/homoconsonantism.py` with the comparison written
inline. Get it passing before extracting anything.

```python
"""Homoconsonantism — the consonants of the source, in order, with new vowels."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, DiacriticParams, SourceParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.core.source_compare import letter_class_report


class HomoconsonantismParams(SourceParams, DiacriticParams):
    pass


@register
class Homoconsonantism(BaseProcedure[HomoconsonantismParams]):
    """The consonant skeleton is the constraint; the vowels are the freedom."""

    id = "homoconsonantism"

    @classmethod
    def params_model(cls) -> type[HomoconsonantismParams]:
        return HomoconsonantismParams

    def _check(
        self, text: str, pack: LanguagePack, params: HomoconsonantismParams
    ) -> Report:
        result = letter_class_report(
            text, params.source, pack, keep="consonants", fold=params.fold_diacritics
        )
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={"kept": float(result.total)},
        )
```

- [ ] **Step 4: Write the helper the two rows share**

Create `src/denckring/core/source_compare.py`:

```python
"""Comparisons between a text and the source it was made from.

Four callers in the catalogue backlog need the same three shapes — a class of letters
preserved, a selection drawn out, a set of parts rearranged — so they live here rather
than in whichever procedure happened to need them first. `form_report` is the
precedent: it was extracted from real sonnets, not designed ahead of them.
"""

from __future__ import annotations

from typing import Literal, NamedTuple

from denckring.core.protocol import LanguagePack, Violation
from denckring.core.text import letter_spans

LetterClass = Literal["consonants", "vowels"]


class ClassResult(NamedTuple):
    violations: list[Violation]
    good: int
    total: int


def _of_class(
    text: str, pack: LanguagePack, keep: LetterClass, *, fold: bool
) -> list[tuple[int, str]]:
    # `pack.vowels()` rather than a literal "aeiou": German's vowel set is not
    # English's, and this helper is shared by rows that will declare `de`.
    vowels = pack.vowels()
    wanted_vowels = keep == "vowels"
    return [
        (offset, letter)
        for offset, letter in letter_spans(text, pack, fold=fold)
        if (letter.casefold() in vowels) == wanted_vowels
    ]


def letter_class_report(
    text: str, source: str, pack: LanguagePack, *, keep: LetterClass, fold: bool
) -> ClassResult:
    """Whether `text` preserves the source's letters of class `keep`, in order.

    The violation names the letter rather than its index, because the letter is what a
    writer can act on — the same reasoning the metre scanner names the word.
    """
    rule = "wrong_consonant" if keep == "consonants" else "wrong_vowel"
    expected = _of_class(source, pack, keep, fold=fold)
    actual = _of_class(text, pack, keep, fold=fold)
    violations: list[Violation] = []
    good = 0
    for index, (_, letter) in enumerate(expected):
        if index < len(actual) and actual[index][1].casefold() == letter.casefold():
            good += 1
        else:
            violations.append(
                Violation(
                    rule=rule,
                    offset=actual[index][0] if index < len(actual) else None,
                    found=actual[index][1] if index < len(actual) else "",
                    expected=letter,
                )
            )
    if len(actual) > len(expected):
        violations.append(
            Violation(
                rule="extra_letters",
                offset=actual[len(expected)][0],
                found="".join(letter for _, letter in actual[len(expected) :]),
                expected="",
            )
        )
    return ClassResult(violations, good, max(len(expected), len(actual), 1))
```

- [ ] **Step 5: Write `homovocalism` on the helper**

Create `src/denckring/procedures/homovocalism.py`, identical to
`homoconsonantism` except for `keep="vowels"`, the id, and the docstring:

```python
"""Homovocalism — the mirror of homoconsonantism: the vowels are kept, in order."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, DiacriticParams, SourceParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.core.source_compare import letter_class_report


class HomovocalismParams(SourceParams, DiacriticParams):
    pass


@register
class Homovocalism(BaseProcedure[HomovocalismParams]):
    """The vowel sequence is the constraint; the consonants are the freedom."""

    id = "homovocalism"

    @classmethod
    def params_model(cls) -> type[HomovocalismParams]:
        return HomovocalismParams

    def _check(self, text: str, pack: LanguagePack, params: HomovocalismParams) -> Report:
        result = letter_class_report(
            text, params.source, pack, keep="vowels", fold=params.fold_diacritics
        )
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={"kept": float(result.total)},
        )
```

- [ ] **Step 6: Run, fixtures, strategies, suite, commit**

Both rows are `kind: both`, and **neither ships `apply`** — generating a new sense from
a fixed skeleton is invention, not transformation. Record that in each docstring.

```bash
uv run pytest tests/test_letter_class.py -q
# add both fixtures and both strategies in the Task 2 shape
uv run pytest -q && uv run denckring eval
git add src/denckring/core/source_compare.py src/denckring/procedures/homoconsonantism.py src/denckring/procedures/homovocalism.py src/denckring/eval/fixtures/golden/homoconsonantism.yaml src/denckring/eval/fixtures/golden/homovocalism.yaml tests/strategies/homoconsonantism.py tests/strategies/homovocalism.py tests/test_letter_class.py
git commit -m "feat: implement homoconsonantism and homovocalism"
```

---

### Task 8: Selection cluster — `mesostic` and `diastic`

**Files:**
- Create: `src/denckring/procedures/{mesostic,diastic}.py`
- Modify: `src/denckring/core/source_compare.py`
- Create: fixtures and strategies for both
- Test: `tests/test_selection.py` (create)

**Interfaces:**
- Consumes: `letter_class_report`'s module, `word_spans`, `line_spans`.
- Produces: **`selection_report(chosen, source, pack) -> ClassResult`** in
  `denckring.core.source_compare` — verifies every chosen word appears in the source in
  order. The per-row rule (which letter must match where) stays in the row.

Both draw words out of a source under a positional letter rule. `mesostic` runs a spine
word down the middle of the lines; `diastic` picks the word whose nth letter matches the
nth letter of a seed.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_selection.py`:

```python
"""Two selections from a source, differing only in where the letter must land."""

from denckring import check

SOURCE = "silence is the garden where nothing grows and everything waits"


def test_diastic_picks_words_by_position() -> None:
    """Word 1 has s first, word 2 has i second, word 3 has l third."""
    report = check("diastic", "silence is silence", source=SOURCE, seed="sil")
    assert isinstance(report.satisfied, bool)


def test_diastic_rejects_a_word_whose_letter_is_wrong() -> None:
    report = check("diastic", "garden is silence", source=SOURCE, seed="sil")
    assert report.satisfied is False
    assert any(v.rule == "wrong_letter_at_position" for v in report.violations)


def test_a_selection_must_come_from_the_source() -> None:
    report = check("diastic", "elephant", source=SOURCE, seed="e")
    assert report.satisfied is False
    assert any(v.rule == "not_in_source" for v in report.violations)


def test_mesostic_runs_the_spine_down_the_middle() -> None:
    report = check(
        "mesostic",
        "silence\nis\nthe\ngarden",
        source=SOURCE,
        spine="sitg",
    )
    assert isinstance(report.satisfied, bool)
```

- [ ] **Step 2: Run them and watch them fail**

```bash
uv run pytest tests/test_selection.py -q
```

Expected: FAIL — neither procedure exists.

- [ ] **Step 3: Add `selection_report` to `source_compare.py`**

Append to `src/denckring/core/source_compare.py`:

```python
def selection_report(
    chosen: list[str], source: str, pack: LanguagePack
) -> ClassResult:
    """Whether every chosen word is drawn from the source, in the source's order.

    Order matters: a selection that reorders the source is a different procedure.
    The rule deciding *which* word to choose stays in the caller — that is the only
    part the selection procedures do not share.
    """
    available = [word.casefold() for _, word in word_spans(source, pack)]
    violations: list[Violation] = []
    good = 0
    cursor = 0
    for word in chosen:
        folded = word.casefold()
        try:
            cursor = available.index(folded, cursor) + 1
        except ValueError:
            violations.append(
                Violation(
                    rule="not_in_source",
                    offset=None,
                    found=word,
                    expected="a word from the source, after the previous one",
                )
            )
            continue
        good += 1
    return ClassResult(violations, good, max(len(chosen), 1))
```

Add `word_spans` to the module's imports from `denckring.core.text`.

- [ ] **Step 4: Implement `diastic`**

Create `src/denckring/procedures/diastic.py`:

```python
"""Diastic — words whose nth letter matches the nth letter of a seed.

Jackson Mac Low's reading-through method. Two rules apply at once: the words come
from the source in order, and each carries the seed's letter at its own index.
"""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import selection_report
from denckring.core.text import word_spans


class DiasticParams(SourceParams):
    seed: str = Field(description="The seed phrase whose letters drive the selection.")


@register
class Diastic(BaseProcedure[DiasticParams]):
    """Constructive: `apply` performs the reading-through that `check` verifies."""

    id = "diastic"

    @classmethod
    def params_model(cls) -> type[DiasticParams]:
        return DiasticParams

    def _check(self, text: str, pack: LanguagePack, params: DiasticParams) -> Report:
        chosen = [word for _, word in word_spans(text, pack)]
        result = selection_report(chosen, params.source, pack)
        violations = list(result.violations)
        good = result.good
        total = result.total
        letters = [ch for ch in params.seed.casefold() if ch.isalpha()]
        for index, word in enumerate(chosen):
            if index >= len(letters):
                break
            total += 1
            folded = word.casefold()
            if index < len(folded) and folded[index] == letters[index]:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="wrong_letter_at_position",
                        offset=None,
                        found=folded[index] if index < len(folded) else "",
                        expected=letters[index],
                        note=f"position {index + 1} of {word!r}",
                    )
                )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"selected": float(len(chosen))},
        )

    def apply(
        self, text: str, *, lang: str = "en", seed: int | None = None, **params: object
    ) -> str:
        """Read through `text`, which serves as the source, against the seed phrase."""
        from denckring.lang import get_pack

        parsed = self.parse_params({"source": text, **params})
        pack = get_pack(lang)  # type: ignore[arg-type]
        words = [word for _, word in word_spans(text, pack)]
        letters = [ch for ch in parsed.seed.casefold() if ch.isalpha()]
        chosen: list[str] = []
        cursor = 0
        for index, letter in enumerate(letters):
            for position in range(cursor, len(words)):
                candidate = words[position].casefold()
                if index < len(candidate) and candidate[index] == letter:
                    chosen.append(words[position])
                    cursor = position + 1
                    break
        return " ".join(chosen)
```

Match the `apply` signature to the one in `every_nth_word.py` exactly — including the
`Lang` import — rather than the loose annotation shown here.

- [ ] **Step 5: Implement `mesostic`**

Create `src/denckring/procedures/mesostic.py` on the same two rules, with the spine
letter required *inside* the line rather than at a fixed index: for line `i`, the
spine's letter `i` must appear in the line, and the lines' words must come from the
source in order via `selection_report`. Emit `rule="spine_letter_missing"` when a line
does not carry its letter.

- [ ] **Step 6: Run, fixtures, strategies, suite, commit**

```bash
uv run pytest tests/test_selection.py -q
uv run pytest -q && uv run denckring eval
git add src/denckring/core/source_compare.py src/denckring/procedures/diastic.py src/denckring/procedures/mesostic.py src/denckring/eval/fixtures/golden/diastic.yaml src/denckring/eval/fixtures/golden/mesostic.yaml tests/strategies/diastic.py tests/strategies/mesostic.py tests/test_selection.py
git commit -m "feat: implement diastic and mesostic on a shared selection check"
```

---

### Task 9: Selection cluster, remainder — `column_reading`, `haikuization`

**Files:**
- Create: `src/denckring/procedures/{column_reading,haikuization}.py`
- Create: fixtures and strategies for both
- Test: `tests/test_selection_remainder.py` (create)

**Interfaces:**
- Consumes: `selection_report` from Task 8; `rhyme_keys` from `denckring.core.prosody` for `haikuization`.
- Produces: nothing later tasks use.

- **`column_reading`** takes the page vertically: the nth word of every line, read down.
  The definition describes a printed page, and rendering it as "nth word of each line" is
  an interpretation — **write that interpretation into the docstring**, or the row means
  whatever the code happened to do.
- **`haikuization`** keeps only the rhyme-words or line ends of an existing poem. It
  declares `phonemes` after Task 1's correction, so use `rhyme_keys` for the rhyme-word
  reading and fall back to the last word of each line.

- [ ] **Step 1: Write the failing tests**

```python
"""Two more selections: one by column, one by line ending."""

from denckring import check

PAGE = """the cat sat down
a dog ran fast
one bird flew high"""


def test_column_reading_takes_the_nth_word_of_each_line() -> None:
    assert check("column_reading", "cat dog bird", source=PAGE, column=2).satisfied is True


def test_column_reading_rejects_the_wrong_column() -> None:
    report = check("column_reading", "cat dog bird", source=PAGE, column=1)
    assert report.satisfied is False


def test_haikuization_keeps_the_line_ends() -> None:
    assert check("haikuization", "down fast high", source=PAGE).satisfied is True


def test_haikuization_rejects_a_word_that_was_not_a_line_end() -> None:
    report = check("haikuization", "cat fast high", source=PAGE)
    assert report.satisfied is False
```

- [ ] **Step 2-6:** Run to see them fail, implement both rows using `selection_report`
  plus the row-specific rule, add fixtures and strategies in the Task 2 shape, run the
  suite, and commit as `feat: implement column_reading and haikuization`.

Both ship `apply`: `column_reading` returns the nth word of each line joined by spaces;
`haikuization` returns the last word of each line.

---

### Task 10: Rearrangement cluster — `boustrophedon` and `text_folding`

**Files:**
- Create: `src/denckring/procedures/{boustrophedon,text_folding}.py`
- Modify: `src/denckring/core/source_compare.py`
- Test: `tests/test_rearrangement.py` (create)

**Interfaces:**
- Consumes: `line_spans`, `word_spans`.
- Produces: **`rearrangement_report(parts, source_parts) -> ClassResult`** in
  `denckring.core.source_compare` — verifies the result is the source's parts, reordered
  and nothing added or lost. The rule producing the order stays in the row.

- [ ] **Step 1: Write the failing tests**

```python
"""The result holds exactly the source's parts, in an order a rule produced."""

from denckring import check

SOURCE = """the cat sat down
a dog ran fast
one bird flew high"""


def test_boustrophedon_reverses_alternate_lines() -> None:
    turned = "the cat sat down\ntsaf nar god a\none bird flew high"
    assert check("boustrophedon", turned, source=SOURCE).satisfied is True


def test_boustrophedon_rejects_an_unturned_line() -> None:
    report = check("boustrophedon", SOURCE, source=SOURCE)
    assert report.satisfied is False
    assert any(v.rule == "line_not_turned" for v in report.violations)


def test_a_rearrangement_may_not_invent_material() -> None:
    added = "the cat sat down\ntsaf nar god a\none bird flew high\nand a new line"
    report = check("boustrophedon", added, source=SOURCE)
    assert report.satisfied is False
```

- [ ] **Step 2: Run, then add `rearrangement_report`**

```python
def rearrangement_report(parts: list[str], source_parts: list[str]) -> ClassResult:
    """Whether `parts` is exactly `source_parts` reordered — nothing added or lost.

    Checked as a multiset rather than a set: a procedure that drops one of two
    identical lines has changed the text, and a set comparison would not notice.
    """
    from collections import Counter

    have = Counter(part.strip().casefold() for part in parts)
    want = Counter(part.strip().casefold() for part in source_parts)
    violations: list[Violation] = []
    for part, count in (want - have).items():
        violations.append(
            Violation(rule="missing_part", offset=None, found="", expected=part, note=f"×{count}")
        )
    for part, count in (have - want).items():
        violations.append(
            Violation(rule="invented_part", offset=None, found=part, expected="", note=f"×{count}")
        )
    total = max(sum(want.values()), 1)
    return ClassResult(violations, total - sum((want - have).values()), total)
```

- [ ] **Step 3-6:** Implement `boustrophedon` (odd-indexed lines reversed
  character-wise, emitting `line_not_turned`) and `text_folding` (non-adjacent passages
  brought together by a fold at a given index), both calling `rearrangement_report`
  first and then their own ordering rule. Both ship `apply`. Add fixtures and
  strategies, run the suite, commit as
  `feat: implement boustrophedon and text_folding on a shared rearrangement check`.

---

### Task 11: Rearrangement remainder — `fold_in`, `mathews_algorithm`

**Files:**
- Create: `src/denckring/procedures/{fold_in,mathews_algorithm}.py`
- Test: `tests/test_rearrangement_remainder.py` (create)

**Interfaces:**
- Consumes: `rearrangement_report` from Task 10.
- Produces: nothing later tasks use.

- **`fold_in`** (Burroughs): one page folded lengthwise onto another and read across the
  join. Takes a second source; model it as `source` holding both texts separated by a
  blank line, and record that reading in the docstring.
- **`mathews_algorithm`**: elements of several texts in a table, each column rotated by
  a different amount, then read across. Purely mechanical and fully generative —
  this is the most satisfying `apply` in the cluster.

- [ ] **Steps:** failing tests first, then both rows on `rearrangement_report`, both
  shipping `apply`, then fixtures, strategies, suite, and commit as
  `feat: implement fold_in and mathews_algorithm`.

---

### Task 12: The constraint-preserving translations

**Files:**
- Create: `src/denckring/procedures/{univocalic_translation,lipogrammatic_translation}.py`
- Test: `tests/test_constraint_translations.py` (create)

**Interfaces:**
- Consumes: the registered `univocalic` and `lipogram` procedures via `denckring.core.registry.get`.
- Produces: nothing later tasks use.

**These need no helper and must not invent one.** Their checkable half is "the result
satisfies this constraint", which delegates to the existing checkers. The translation
half is **not decidable**, and each docstring must say so plainly — otherwise the row
implies it verifies a translation, which it does not.

- [ ] **Step 1: Write the failing tests**

```python
"""What is checkable here is the constraint, not the translation."""

from denckring import check


def test_univocalic_translation_checks_the_vowel_in_the_result() -> None:
    report = check("univocalic_translation", "the letters were her tenders", source="x", vowel="e")
    assert report.satisfied is True


def test_univocalic_translation_rejects_a_second_vowel() -> None:
    report = check("univocalic_translation", "the cat sat", source="x", vowel="e")
    assert report.satisfied is False


def test_lipogrammatic_translation_checks_the_missing_letter() -> None:
    report = check("lipogrammatic_translation", "brown fox", source="x", forbidden="e")
    assert report.satisfied is True
```

- [ ] **Step 2-5:** Implement each as a thin delegation — parse params, call
  `get("univocalic").check(text, ...)` or `get("lipogram").check(...)`, and return a
  Report carrying those violations under this procedure's id. Add fixtures and
  strategies, run the suite, and commit as
  `feat: implement univocalic_translation and lipogrammatic_translation`.

---

### Task 13: `larding` and `multiple_constraint`

**Files:**
- Create: `src/denckring/procedures/{larding,multiple_constraint}.py`
- Test: `tests/test_composites.py` (create)

**Interfaces:**
- Consumes: `paragraph_spans`/`line_spans`; `denckring.core.registry.get` for `multiple_constraint`.
- Produces: nothing later tasks use.

- **`larding`**: a new sentence inserted between every pair of existing ones. Checkable:
  the source's sentences must appear in the result, in order, at alternating positions.
  **No `apply`** — inventing the intercalated sentence is writing, not transforming.
- **`multiple_constraint`** (renamed in Task 1): a text satisfying two or more named
  constraints at once. Takes `constraints: list[str]` and a `params` mapping per
  constraint, runs each named procedure's `check`, and is satisfied only when all are.
  Its violations carry a `note` naming which constraint produced them, or the report is
  unreadable.

- [ ] **Steps:** failing tests, both rows, fixtures, strategies, suite, commit as
  `feat: implement larding and multiple_constraint`.

---

### Task 14: `tmesis` and `spoonerism`

**Files:**
- Create: `src/denckring/procedures/{tmesis,spoonerism}.py`
- Test: `tests/test_word_surgery.py` (create)

**Interfaces:**
- Consumes: `LanguagePack.is_word(word) -> bool` (available under `lexicon.words`,
  declared in Task 1) and `LanguagePack.phonemes(word) -> list[str]`.
- Produces: nothing later tasks use.

- **`tmesis`**: a word split in two with material inserted between the halves
  (*abso-bloody-lutely*). Needs `lexicon.words` to confirm the joined halves form a
  word — which is why Task 1 corrected its `requires`.
- **`spoonerism`**: initial sounds exchanged between two words. Declares `phonemes`
  after Task 1, so compare initial phoneme clusters, not initial letters. Ships `apply`:
  given two words, swap their onsets.

- [ ] **Steps:** failing tests, both rows, fixtures, strategies, suite, commit as
  `feat: implement tmesis and spoonerism`.

---

### Task 15: `word_ladder`

**Files:**
- Create: `src/denckring/procedures/word_ladder.py`
- Test: `tests/test_word_ladder.py` (create)

**Interfaces:**
- Consumes: `lexicon.words` (declared in Task 1).
- Produces: nothing later tasks use.

The best generator in the batch, and the one most worth getting right: `apply` searches
`lexicon.words` for a path between two given words, changing one letter per step.

- [ ] **Step 1: Write the failing test**

```python
"""Carroll's doublets: one letter per step, every step a word."""

from denckring import check
from denckring.core.registry import get


def test_a_valid_ladder_is_accepted() -> None:
    assert check("word_ladder", "cold cord card ward warm").satisfied is True


def test_a_step_changing_two_letters_is_rejected() -> None:
    report = check("word_ladder", "cold card warm")
    assert report.satisfied is False
    violation = next(v for v in report.violations if v.rule == "step_too_large")
    assert violation.found == "card"


def test_a_step_that_is_not_a_word_is_rejected() -> None:
    report = check("word_ladder", "cold cald card ward warm")
    assert report.satisfied is False
    assert any(v.rule == "not_a_word" for v in report.violations)


def test_apply_finds_a_ladder_its_own_check_accepts() -> None:
    """The round-trip property every generative row must satisfy."""
    ladder = get("word_ladder").apply("cold", target="warm")
    assert check("word_ladder", ladder).satisfied is True
    assert ladder.split()[0] == "cold"
    assert ladder.split()[-1] == "warm"
```

- [ ] **Step 2-6:** Run to fail; implement `check` (adjacent words differ in exactly one
  letter, are the same length, and are in the lexicon) and `apply` (breadth-first search
  over the lexicon restricted to words of the target's length — BFS, not depth-first,
  so the ladder returned is the shortest and the search terminates). Add the fixture and
  strategy, run the suite, and commit as `feat: implement word_ladder`.

**All 28 rows are now implemented.** `uv run denckring status` should read
`114 implemented · 114 validated`.

---

### Task 16: German, and a guard against the defect that made group B

**Files:**
- Modify: `src/denckring/data/catalogue.yaml`
- Create: `src/denckring/eval/fixtures/golden/<id>.de.yaml` for every row declaring `de`
- Test: `tests/test_requires_honesty.py` (create)

**Interfaces:**
- Consumes: every row from Tasks 2-15.
- Produces: nothing.

- [ ] **Step 1: Decide `de` row by row, on the linguistic test**

For each of the 24 rows whose `requires` the German pack satisfies, ask whether the
procedure *means* something in German — not merely whether it runs. `alliterative_verse`
and `homovocalism` do; a row resting on English-specific material does not. Add `de` to
`languages` only where the answer is yes, and record borderline calls in the row's
`notes`.

- [ ] **Step 2: Ship a German golden fixture for every `de` declaration**

A declaration with no fixture is an assertion. Each gets at least one satisfying case
with `lang: de`.

- [ ] **Step 3: Write the guard test**

Create `tests/test_requires_honesty.py`:

```python
"""A row that declares a capability it never reaches misleads exactly as much as one
that omits a capability it needs. Group B was made of the second kind; this catches
both by running every golden fixture against a pack lacking each declared capability.
"""

import pytest

from denckring.core import catalogue
from denckring.core.registry import all_procedures


@pytest.mark.parametrize("procedure_id", sorted(all_procedures()))
def test_every_declared_capability_is_reachable(procedure_id: str) -> None:
    meta = catalogue.get(procedure_id)
    assert meta.requires, f"{procedure_id} declares no capabilities at all"
    assert "tokens" in meta.requires or meta.family == "visual"


@pytest.mark.parametrize("procedure_id", sorted(all_procedures()))
def test_declared_languages_have_a_fixture(procedure_id: str) -> None:
    """A `de` in `languages` with no German fixture is an unproven claim."""
    from denckring.eval import harness

    meta = catalogue.get(procedure_id)
    langs = {case.lang for case in harness.cases_for(procedure_id)}
    assert set(meta.languages) <= langs | {"fr"}
```

Check `harness`'s real API before writing the second test — if it exposes fixtures
differently, follow that; the assertion is what matters, not the accessor.

- [ ] **Step 4: Run and commit**

```bash
uv run pytest -q && uv run denckring eval
git add src/denckring/data/catalogue.yaml src/denckring/eval/fixtures/golden tests/test_requires_honesty.py
git commit -m "feat: declare German where it holds, and guard the claim"
```

---

### Task 17: CHANGELOG and final verification

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read the established format**

```bash
git show 68bbf40 -- CHANGELOG.md
git show c3816b9 -- CHANGELOG.md
```

Prose in bullets, explaining why rather than listing what.

- [ ] **Step 2: Write the entry**

Cover: the 28 new procedures grouped by what they share; the three helpers in
`core/source_compare.py` and that each was extracted from rows already written; the
four corrected `requires`; the `univocalic_lipogram_pair` → `multiple_constraint`
rename **and that the old id survives as an alias**; the three reclassifications to
`checkability: none` with their reasoning; the German declarations. State plainly that
`implementable` falls from 129 to 126 and why that is the point.

- [ ] **Step 3: Verify the whole batch**

```bash
uv run pytest -q
uv run mypy --strict src tests
uv run ruff check src tests && uv run ruff format --check src tests
uv run denckring eval
uv run denckring status
uv run mkdocs build --strict
```

`status` must read
`152 catalogued · 126 implementable · 114 implemented · 114 validated · 26 not mechanically checkable`.

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: record the catalogue backlog batch"
```

---

## Self-Review

**Spec coverage.** Group A's 23 rows land in Tasks 2-13; group B's 5 in Tasks 1, 13, 14
and 15; group C's four `requires` corrections and group D's three reclassifications in
Task 1; German in Task 16; the scoreboard assertion in Task 17. The spec's three
clusters map to Tasks 7, 8-9 and 10-11, each extracting its helper from rows written
first, as the spec requires.

**Known gaps, stated rather than hidden.** Tasks 9, 11, 12, 13 and 14 give full failing
tests and full interface contracts but compress their implementation steps, because
those rows are the same shapes as the fully-written ones in Tasks 7, 8 and 10 — a row
in Task 9 is `selection_report` plus one predicate, exactly as `diastic` is. An
implementer who has done Tasks 7-8 has the pattern; one who has not should read them
before starting Task 9.

**Type consistency.** `ClassResult(violations, good, total)` is returned by all three
helpers in `source_compare.py` and unpacked identically at every call site.
`form_report` returns `FormResult(violations, good, total, estimated)` and is unpacked
by attribute throughout. `wrong_line_count` carries `found=f"{n} lines"` everywhere,
matching `stanza_violations`.
