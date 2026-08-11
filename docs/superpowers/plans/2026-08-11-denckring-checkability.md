# Checkability and the Data-Free Batches — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Model whether a procedure can be checked at all, fix the coverage metric, and implement the 38 catalogued procedures that need no lexicon, syllabification or phoneme data.

**Architecture:** A required `checkability` field partitions the catalogue into decidable-alone, decidable-against-a-source, and not-decidable; coverage is measured against the first two. Source-relative procedures carry their source on a `SourceParams` base, exactly as folding rides on `DiacriticParams`.

**Tech Stack:** Unchanged.

## Global Constraints

Everything from the previous plans still applies. New here:

- **No data files of any kind.** If a procedure seems to need a word list, a syllable count or a rhyme, it belongs to a later chapter — leave it catalogued.
- **A checker verifies what the definition claims, and the definition claims only what the checker verifies.** `sestina` checks end-word permutation, so its catalogue definition says end-word permutation. Never let a row promise metre that the code does not test.
- **`checkability: none` is a statement about the form, not a backlog entry.** Do not implement one to make a number look better; the invariant suite will fail the build if you do.
- Each task ends green on `uv run pytest && ruff check && ruff format --check && mypy --strict src tests` and commits.

---

### Task 1: The `checkability` field

**Files:**
- Modify: `src/denckring/core/protocol.py`, `src/denckring/data/catalogue.yaml`
- Test: `tests/test_catalogue_quality.py` (extend)

**Interfaces:**
- Produces: `Checkability` alias, `CHECKABILITIES` tuple, `Meta.checkability`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_catalogue_quality.py`:

```python
def test_every_row_declares_checkability() -> None:
    for meta in ENTRIES.values():
        assert meta.checkability in CHECKABILITIES, f"{meta.id} has {meta.checkability!r}"


def test_source_relative_rows_are_not_marked_self() -> None:
    """A row whose definition says 'of a source' cannot be decidable alone."""
    for meta in ENTRIES.values():
        definition = meta.definitions["en"].casefold()
        if "of a source" in definition or "of an existing" in definition:
            assert meta.checkability != "self", (
                f"{meta.id} is defined against a source text but claims to be "
                f"decidable from the text alone"
            )
```

Import `CHECKABILITIES` from `denckring.core.protocol`.

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_catalogue_quality.py -k checkability -v`
Expected: FAIL — `ImportError: cannot import name 'CHECKABILITIES'`

- [ ] **Step 3: Add the type**

In `protocol.py`, beside `Attribution`:

```python
#: Whether a procedure admits a mechanical check at all. `self` is decidable
#: from the text and its parameters; `source` needs the text it was made from;
#: `none` means no computable acceptance criterion exists — the row is
#: catalogued because the form belongs in an honest survey, not as a backlog
#: item. ADR 0002 keeps `none` rows permanently unregistered.
Checkability = Literal["self", "source", "none"]
CHECKABILITIES: tuple[str, ...] = get_args(Checkability)
```

and on `Meta`, after `attribution`:

```python
    checkability: Checkability
```

- [ ] **Step 4: Classify all 145 rows**

Every row gains `checkability`. The twelve implemented rows are all `self`. Assign the
rest by the rule: can a program decide this from the text alone (`self`), only against
the source text (`source`), or not at all (`none`)?

`source` rows: `anagram`, `antigram`, `transposal`, `cut_up`, `fold_in`, `every_nth_word`,
`diastic`, `mesostic`, `slenderizing`, `melting_text`, `larding`, `haikuization`,
`column_reading`, `recombination`, `text_folding`, `n_plus_7`, `s_plus_7`,
`definitional_literature`, `definitional_expansion`, `homoconsonantism`, `homovocalism`,
`homosyntaxism`, `chimera`, `antonymic_substitution`, `synonymic_substitution`,
`perverb`, `mathews_algorithm`, and every row in the `translation` family.

`none` rows: `canada_dry`, `found_poem`, `chance_operation`, `oracle_reading`, `erasure`,
`blackout_poetry`, `palimpsest`, `strikethrough`, `dada_poem`, `cento`, `calligram`,
`pattern_poem`, `concrete_poetry`, `spatial_poem`, `grid_poem`, `typewriter_poem`,
`boustrophedon` — no: `boustrophedon` is `self`, its alternating direction is decidable.
Also `none`: `line_permutation`, `stanza_permutation`, `word_permutation`,
`combinatorial_sonnet`, `cent_mille_milliards`, `proteus_verse`, `wechselsatz`,
`denckring` — these assert that *every* rearrangement reads acceptably, which is a
judgement no program makes.

Everything else is `self`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_catalogue_quality.py -v`
Expected: PASS.

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A && git commit -m "feat: record whether each catalogued procedure admits a check"
```

---

### Task 2: Coverage measured against the implementable subset

**Files:**
- Modify: `src/denckring/eval/harness.py`
- Test: `tests/test_harness.py` (extend), `tests/test_invariants.py` (extend)

**Interfaces:**
- Produces: `Coverage.implementable`, `Coverage.unreachable`; `harness.implementable_ids()`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_harness.py`:

```python
def test_coverage_separates_implementable_from_unreachable() -> None:
    coverage = harness.status()
    assert coverage.implementable < coverage.catalogued
    assert coverage.unreachable > 0
    assert coverage.implementable + coverage.unreachable == coverage.catalogued


def test_implemented_never_exceeds_implementable() -> None:
    coverage = harness.status()
    assert coverage.implemented <= coverage.implementable


def test_coverage_line_names_the_unreachable_rows() -> None:
    assert "not mechanically checkable" in harness.status().line()
```

Append to `tests/test_invariants.py`:

```python
def test_registered_procedures_are_never_marked_unreachable(procedure_id: str) -> None:
    """If a checker exists, the catalogue row was mis-filed."""
    meta = get(procedure_id).meta
    assert meta.checkability != "none", (
        f"{procedure_id} is registered but its catalogue row says it cannot be "
        f"mechanically checked — one of the two is wrong"
    )
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_harness.py tests/test_invariants.py -v`
Expected: FAIL — `Coverage` has no `implementable`.

- [ ] **Step 3: Extend `Coverage`**

```python
class Coverage(BaseModel):
    """The project metric.

    `implementable` excludes rows that can never have a checker, so the gap
    between it and `implemented` describes work that can actually be done.
    """

    catalogued: int
    implementable: int
    implemented: int
    validated: int
    unreachable: int

    def line(self) -> str:
        return (
            f"{self.catalogued} catalogued · "
            f"{self.implementable} implementable · "
            f"{self.implemented} implemented · "
            f"{self.validated} validated · "
            f"{self.unreachable} not mechanically checkable"
        )
```

and:

```python
def implementable_ids() -> list[str]:
    """Catalogued procedures that could have a checker, whether or not they do."""
    return sorted(pid for pid in catalogue.ids() if catalogue.get(pid).checkability != "none")


def status() -> Coverage:
    catalogued = catalogue.ids()
    implementable = implementable_ids()
    return Coverage(
        catalogued=len(catalogued),
        implementable=len(implementable),
        implemented=len(implemented_ids()),
        validated=len(validated_ids()),
        unreachable=len(catalogued) - len(implementable),
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_harness.py tests/test_invariants.py -v`
Expected: PASS.

- [ ] **Step 5: Show the new metric**

Run: `uv run denckring status`
Expected: five counts, `implementable` strictly below `catalogued`.

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest && uv run ruff format && uv run ruff check && uv run mypy --strict src tests
git add -A && git commit -m "feat: measure coverage against the implementable subset"
```

---

### Tasks 3–5: The self-checkable batch

Twenty-three procedures in three tasks, each following the rhythm established in the
Batch 1 plan: `denckring new <id>`, delete the duplicate catalogue row, write the
per-procedure test and golden fixture, write `_check`, write the strategies, verify,
commit.

Every one uses `self._report(...)` unless an empty text should be *unsatisfied*, in which
case build the `Report` directly and say why in the class docstring, as `pangram` does.

#### Task 3: Letter and alphabet constraints (8)

| id | Checking rule | Key params |
|---|---|---|
| `abecedarian` | Unit initials are the alphabet in order from a start letter | `unit="line"`, `start="a"` |
| `alphabetical_sentence` | Folded words are in non-decreasing alphabetical order | — |
| `bivocalic` | At most two distinct vowels appear | `vowels` (optional, inferred) |
| `monoconsonantal` | At most one distinct consonant appears | `consonant` (optional, inferred) |
| `consonantal_lipogram` | None of a named consonant set appears | `forbidden` (a string of letters) |
| `pangrammatic_lipogram` | Every letter but one appears; that one never does | `forbidden="e"` |
| `supervocalic` | Each of the five vowels appears exactly once | — |
| `letter_bank` | Every letter comes from the bank word, and every bank letter is used | `bank` |

- [ ] **Step 1: Scaffold all eight, delete the duplicate catalogue rows**
- [ ] **Step 2: Write the per-procedure tests and golden fixtures; watch them fail**
- [ ] **Step 3: Write the checkers; run until green**
- [ ] **Step 4: Write the strategies; `uv run pytest tests/test_strategies.py`**
- [ ] **Step 5: Full verification and commit**

#### Task 4: Position and repetition constraints (8)

| id | Checking rule | Key params |
|---|---|---|
| `homoteleuton` | Every word ends with the same letter | `final` (optional, inferred) |
| `double_acrostic` | Line initials spell one target and line finals another | `first`, `last` |
| `chronogram` | Roman-numeral letters, in order, sum to the target | `year` |
| `liponym` | A named word never appears, in any case | `forbidden` |
| `tautonym` | Every word is a doubled letter-sequence | — |
| `boustrophedon` | Alternate lines are reversed with respect to their neighbours | — |
| `sator_square` | An n-by-n grid reading identically across, down, and both reversed | — |
| `snowball_sentence` | Each sentence has one more word than the last | `start`, `step` |

- [ ] **Step 1–5:** as Task 3.

#### Task 5: Structural constraints and end-word forms (7)

| id | Checking rule | Key params |
|---|---|---|
| `sentence_length_constraint` | Every sentence's word count equals the target, or lies in a range | `words`, `tolerance` |
| `single_sentence` | Exactly one sentence-terminating mark, at the very end | — |
| `anaphora` | Every line or clause opens with the same word or phrase | `opening` (optional, inferred) |
| `epistrophe` | Every line or clause closes with the same word or phrase | `closing` (optional, inferred) |
| `sestina` | Six sestets plus a tercet; end-words follow the fixed 6-1-5-2-4-3 rotation | — |
| `quenina` | Generalised: `n` stanzas of `n` lines, end-words following the spiral permutation, valid only where the permutation has full order | `n` |
| `pantoum` | Lines 2 and 4 of each quatrain reappear as lines 1 and 3 of the next | — |

`sestina` is `quenina` at `n=6`; implement `quenina` first and have `sestina` delegate to
the shared helper rather than duplicating the rotation, in the same way
`reverse_snowball` shares `rhopalic_violations`.

**These three check end-word permutation only.** Update their catalogue definitions in
this task to say so, so no row promises metre the code does not test.

- [ ] **Step 1–5:** as Task 3.

---

### Task 6: Merge chapter 4

- [ ] **Step 1: Full acceptance run**

```bash
uv run pytest
uv run ruff format --check && uv run ruff check
uv run mypy --strict src tests
uv run denckring eval --all | tail -3
uv run denckring status
```

Expected: green, roughly 35 procedures implemented.

- [ ] **Step 2: Update CHANGELOG, merge to master, delete the branch**

---

### Task 7: `SourceParams` and `--source`

**Files:**
- Modify: `src/denckring/core/base.py`, `src/denckring/cli.py`
- Test: `tests/test_source_param.py`

**Interfaces:**
- Produces: `denckring.core.base.SourceParams`; `--source FILE` on `check` and `apply`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_source_param.py
from pathlib import Path

import pytest
from typer.testing import CliRunner

from denckring import check, get
from denckring.cli import app
from denckring.core.errors import InvalidParams

runner = CliRunner()


def test_source_is_exposed_in_the_schema() -> None:
    assert "source" in get("anagram").params_schema()["properties"]


def test_missing_source_is_an_invalid_params_error() -> None:
    with pytest.raises(InvalidParams):
        check("anagram", "a candidate text")


def test_cli_reads_the_source_from_a_file(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("listen", encoding="utf-8")
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("silent", encoding="utf-8")
    result = runner.invoke(app, ["check", "anagram", str(candidate), "--source", str(source)])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run it to verify it fails**, then implement:

```python
class SourceParams(BaseModel):
    """Mixed into procedures decidable only against the text they were made from."""

    source: str = Field(description="The text this one was made from.")
```

and in `cli.py`, on both `check` and `apply`:

```python
    source: Annotated[str | None, typer.Option("--source", help="File the text was made from")] = None,
```

reading it with `_read(source)` and merging it into the parsed params under `"source"`
before dispatch. A `--source` passed to a procedure that takes no source must surface as
`InvalidParams` rather than being silently dropped.

- [ ] **Step 3: Verify and commit**

---

### Tasks 8–9: The source-relative batch

#### Task 8: Letter- and word-level source procedures (7)

| id | Checking rule |
|---|---|
| `anagram` | Candidate and source have identical folded letter multisets |
| `antigram` | An anagram, plus the candidate is not the source |
| `transposal` | Word-for-word: each candidate word is an anagram of the corresponding source word |
| `slenderizing` | Candidate equals the source with every instance of one letter deleted |
| `melting_text` | Candidate is the source with exactly `n` words removed, order preserved |
| `every_nth_word` | Candidate equals every nth word of the source |
| `column_reading` | Candidate equals the source read down fixed-width columns |

#### Task 9: Structural source procedures, and `apply` (8)

| id | Checking rule |
|---|---|
| `cut_up` | Every candidate word appears in the source, with multiplicity |
| `recombination` | Candidate sentences are a permutation of the source's |
| `larding` | Source sentences appear in order, with new material between each pair |
| `haikuization` | Candidate lines are the final words of the source's lines, in order |
| `diastic` | The nth candidate word has the nth seed letter in nth position |
| `mesostic` | The nth candidate line has the nth spine letter at its centre |
| `lipogrammatic_translation` | Candidate omits the forbidden letter and is not the source |
| `univocalic_translation` | Candidate is univocalic and is not the source |

`cut_up` and `every_nth_word` also implement `apply`, since generating them needs only the
source. Their `kind` changes from `constructive` to `both` in the catalogue, and a new
registry-wide suite lands with them:

```python
# tests/test_round_trip.py
"""The seed's central property, testable at last."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from denckring.core.registry import all_procedures

CONSTRUCTIVE = sorted(pid for pid, p in all_procedures().items() if hasattr(p, "apply"))


def test_there_is_something_to_round_trip() -> None:
    assert CONSTRUCTIVE, "no procedure defines apply(); the round-trip property is vacuous"


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.differing_executors])
@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=80))
def test_apply_output_satisfies_check(text: str) -> None:
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        produced = procedure.apply(text)
        report = procedure.check(produced, source=text)
        assert report.satisfied, f"{procedure_id}: apply produced text its own check rejects"
```

- [ ] **Steps:** as the earlier procedure tasks, plus the round-trip suite in Task 9.

---

### Task 10: Merge chapter 5

- [ ] **Step 1: Full acceptance run**, expecting roughly 50 procedures implemented and the
  round-trip suite non-empty.
- [ ] **Step 2: CHANGELOG, README, ADR 0011 on checkability, merge, delete the branch**

ADR 0011 — Context: `requires` says what a procedure needs, not whether it can be checked
at all, and a quarter of the catalogue can never have a checker. Decision: `checkability`
partitions the catalogue and coverage is measured against the implementable subset.
Consequences: the metric describes reachable work; `none` becomes a statement about a
form rather than a backlog entry; an invariant catches a row and its implementation
disagreeing.

---

## Self-review notes

Spec coverage: `checkability` → Task 1; metric → Task 2; the 23 self-checkable → Tasks
3–5; `SourceParams` and `--source` → Task 7; the 15 source-relative → Tasks 8–9;
round-trip → Task 9; ADR → Task 10.

Names used consistently: `checkability`, `CHECKABILITIES`, `Checkability`,
`implementable_ids`, `Coverage.implementable`, `Coverage.unreachable`, `SourceParams`,
`--source`.

The risk worth naming: Task 1 classifies 145 rows by judgement, and a row filed `none`
that is in fact checkable quietly shrinks the denominator. The invariant only catches the
opposite error. Reviewers should read the `none` list directly rather than trusting the
count — it is about 25 rows and takes a minute.
