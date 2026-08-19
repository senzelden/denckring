# Dictionary Glosses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the English data pack dictionary definitions, build the three rows that can honestly use what exists, and correct the four catalogue rows whose stated needs are wrong.

**Architecture:** One new capability (`lexicon.glosses`) behind the existing `denckring-en-data` distribution, produced by a committed build script the package has never had. The English lexicon migrates to Open English WordNet 2024 in the same move, which regenerates the vendored noun list and therefore changes `n_plus_7` and `s_plus_7` output deliberately. Three rows follow: `kangaroo_word`, which needs no new capability at all, and the two `definitional_*` rows the glosses unblock.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, Hypothesis, ruff, mypy --strict, uv. `wn` as a build-only dependency.

**Spec:** `docs/superpowers/specs/2026-08-19-glosses-design.md`

## Global Constraints

- Python 3.11+; `uv run mypy --strict src tests`, `uv run ruff check src tests`, `uv run ruff format --check src tests` all clean.
- **Baseline is 3339 tests passing** at branch point `fdea945`. Every task ends green.
- Run the suite as `uv run pytest -q` with an **explicit `timeout: 900000`** on the Bash call. Never background it; if the tool auto-backgrounds anyway, run it in slices that each finish inside two minutes and say which slices you ran. **Ending your turn means you are parked, not running.**
- `tests/conftest.py` auto-parametrizes any test taking a `procedure_id` or `golden_case` argument. **Never write your own `@pytest.mark.parametrize` for those names** — it raises `duplicate parametrization` at collection.
- Every procedure subclasses `BaseProcedure[P]`, is `@register`ed, defines `id`/`params_model()`/`_check()`, and builds its Report via `self._report(...)`. Never construct `Report` directly.
- **Never a bare `BaseModel` as a `params_model`** — Pydantic 2 cannot instantiate it. Use a named subclass.
- **No parameter may be named `seed` or `lang`** — both collide with `apply`'s reserved keyword arguments and are silently discarded, producing wrong output with no error.
- Capability constants live in `src/denckring/lang/base.py` (`NOUNS = "lexicon.nouns"`, `WORDS = "lexicon.words"`). `BasePack` methods raise `MissingCapability(DIRECT_CALL, self.lang, <CONSTANT>)`.
- **Declare only capabilities a row actually reaches.** `tests/test_requires_honesty.py` enforces this in both directions and will fail a row that declares what it never uses.
- Data files are **vendored, not downloaded**. The network is touched only by a deliberate `build_lexicon.py` run, never by installation or use (ADR 0013).
- Gzip writes use `mtime=0` so two runs over identical content produce identical bytes and `git diff` stays clean.
- Commit message bodies end with:
```
Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01ByjmNebwmJDvbcxhsA6fcr
```

---

## File Structure

| File | Responsibility |
|---|---|
| `src/denckring/data/catalogue.yaml` (modify) | Four corrections: `kangaroo_word`, `chimera`, `synonymic_substitution`, `definitional_translation`. |
| `src/denckring/lang/base.py` (modify) | `GLOSSES` constant; `BasePack.glosses()` raising. |
| `src/denckring/core/protocol.py` (modify) | `glosses()` on the `LanguagePack` protocol. |
| `packages/denckring-en-data/scripts/build_lexicon.py` (create) | Regenerates `nouns.txt`, `glosses.txt.gz` and `metadata.json` from OEWN 2024. |
| `packages/denckring-en-data/src/denckring_en_data/__init__.py` (modify) | Gloss loader, resolution, `glosses()`, capability declaration. |
| `packages/denckring-en-data/LICENSE-WORDNET` (modify) | Princeton 3.1 licence replaced by OEWN's CC BY 4.0. |
| `packages/denckring-en-data/README.md` (modify) | Data section naming both sources. |
| `src/denckring/procedures/kangaroo_word.py` (create) | Needs only `lexicon.words`. |
| `src/denckring/procedures/definitional_expansion.py` (create) | One iteration; owns the gloss comparison. |
| `src/denckring/procedures/definitional_literature.py` (create) | The repeated form, on the comparison extracted from the row above. |
| `tests/test_lang_en_data.py` (create) | Mirrors `tests/test_lang_de_data.py`, including the metadata-count guard. |
| `CHANGELOG.md` (modify) | The entry. |

---

### Task 1: The four catalogue corrections

Do this first: `kangaroo_word` cannot be built until its `requires` stops naming a
capability that will never exist, and the guard test in Task 2 reads the corrected row.

**Files:**
- Modify: `src/denckring/data/catalogue.yaml`
- Test: `tests/test_gloss_catalogue_corrections.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `kangaroo_word` declaring `[tokens, fold_diacritics, lexicon.words]`; `chimera` declaring `[tokens, pos]`; `definitional_translation` declaring `[tokens, lexicon.glosses.bilingual]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_gloss_catalogue_corrections.py`:

```python
"""Four rows asked for the wrong thing.

Measuring what WordNet can do showed that `lexicon.synonyms` has no honest
consumer: one row needs a parameter, one needs part-of-speech tagging, and one
cannot be satisfied by ordinary text at all.
"""

import pytest

from denckring.core import catalogue


def test_kangaroo_word_needs_the_word_list_not_a_thesaurus() -> None:
    """Whether two words are synonyms is the writer's claim; that they are words
    and that the letters appear in order is what a program can check."""
    requires = catalogue.get("kangaroo_word").requires
    assert "lexicon.words" in requires
    assert "lexicon.synonyms" not in requires


def test_chimera_substitutes_by_part_of_speech_not_by_meaning() -> None:
    requires = catalogue.get("chimera").requires
    assert "pos" in requires
    assert "lexicon.synonyms" not in requires


def test_definitional_translation_needs_glosses_in_the_target_language() -> None:
    requires = catalogue.get("definitional_translation").requires
    assert "lexicon.glosses.bilingual" in requires


@pytest.mark.parametrize(
    "row", ["synonymic_substitution", "antonymic_substitution", "antonymic_translation"]
)
def test_the_unsatisfiable_rows_record_why_they_wait(row: str) -> None:
    """Blocked for a stated reason beats blocked for an unbuilt one."""
    assert catalogue.get(row).notes
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/test_gloss_catalogue_corrections.py -q
```

Expected: failures on all four tests.

- [ ] **Step 3: Correct `kangaroo_word` and `chimera`**

In `src/denckring/data/catalogue.yaml`:

- `kangaroo_word`: `requires: [tokens, fold_diacritics, lexicon.words]`
- `chimera`: `requires: [tokens, pos]`, and add a `notes`:

```yaml
    notes: >-
      Blocked on the same `pos` capability as `homosyntaxism` and `verbless_prose`.
      This row empties a text of its nouns, verbs and adjectives and refills each
      class from a different source, which is a part-of-speech operation; it was
      previously filed under `lexicon.synonyms`, which it never needed.
```

- [ ] **Step 4: Correct `definitional_translation`**

`requires: [tokens, lexicon.glosses.bilingual]`, with a `notes`:

```yaml
    notes: >-
      Blocked: replacing each word by its definition *in the target language*
      needs glosses in two languages. English glosses do not serve it, and no
      pack ships non-English ones. Named alongside `homophonic_translation`'s
      `phonemes.bilingual` for the same reason.
```

- [ ] **Step 5: Record why the three unsatisfiable rows wait**

Add a `notes` to `synonymic_substitution` recording the measurement, and to
`antonymic_substitution` and `antonymic_translation` if they lack one:

```yaml
    notes: >-
      Blocked, and a larger thesaurus will not unblock it. WordNet synonymy is
      synset co-membership: of twelve substitutions a writer would naturally
      make, five are co-members, and only four of eleven content words in plain
      prose have any synonym at all. "Every substantive word replaced by a
      synonym" is not satisfiable by ordinary text.
```

For the antonym rows the measured figures are 6,633 lemmas with any antonym, and
2 content words in 11 in plain prose.

- [ ] **Step 6: Run the tests and the suite**

```bash
uv run pytest tests/test_gloss_catalogue_corrections.py -q
uv run pytest -q
```

Both green. If a catalogue-shape test elsewhere fails, fix that test — these
corrections are deliberate.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/data/catalogue.yaml tests/test_gloss_catalogue_corrections.py
git commit -m "fix: four rows named capabilities they do not need"
```

---

### Task 2: `kangaroo_word`

**Files:**
- Create: `src/denckring/procedures/kangaroo_word.py`
- Create: `src/denckring/eval/fixtures/golden/kangaroo_word.yaml`
- Create: `tests/strategies/kangaroo_word.py`
- Test: `tests/test_kangaroo_word.py` (create)

**Interfaces:**
- Consumes: `kangaroo_word`'s corrected `requires` from Task 1; `pack.is_word`.
- Produces: nothing later tasks use.

*A word containing the letters of a synonym of itself, in order but not necessarily
adjacent* — *encourage* hides *urge*.

**The synonym is a parameter, and this is the whole point of the row's design.** A
WordNet-driven version rejects `encourage`/`urge`, because they are near-synonyms rather
than synset co-members, while accepting `abcs`/`abc`. So the caller names the synonym;
`check` verifies it is a real word and that its letters appear in order in the host word.
Whether it is *genuinely* a synonym is the writer's claim, and the docstring must say so
plainly — the treatment `univocalic_translation` gives its undecidable translation half.

- [ ] **Step 1: Write the failing test**

Create `tests/test_kangaroo_word.py`:

```python
"""The synonym is the caller's claim; the letters are the program's business."""

from denckring import check


def test_a_hidden_synonym_in_order_is_accepted() -> None:
    """encourage hides u-r-g-e, scattered but ordered."""
    assert check("kangaroo_word", "encourage", synonym="urge").satisfied is True


def test_letters_out_of_order_are_rejected() -> None:
    report = check("kangaroo_word", "encourage", synonym="rug")
    assert report.satisfied is False
    violation = next(v for v in report.violations if v.rule == "synonym_not_in_order")
    assert violation.found == "rug"


def test_a_synonym_the_lexicon_does_not_know_is_rejected() -> None:
    report = check("kangaroo_word", "encourage", synonym="urg")
    assert report.satisfied is False
    assert any(v.rule == "not_a_word" for v in report.violations)


def test_the_word_may_not_be_its_own_synonym() -> None:
    """Every word trivially contains itself; that is not a kangaroo word."""
    assert check("kangaroo_word", "encourage", synonym="encourage").satisfied is False
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/test_kangaroo_word.py -q
```

Expected: FAIL — `UnknownProcedure: No procedure with id 'kangaroo_word'`.

- [ ] **Step 3: Implement**

Create `src/denckring/procedures/kangaroo_word.py`:

```python
"""Kangaroo word — a word carrying a synonym of itself in its own letters.

*Encourage* hides *urge*; *masculine* hides *male*. The letters must appear in
order, though not adjacently — that scattering is the form.

**Whether the two words are synonyms is the writer's claim, not this checker's
finding.** A thesaurus cannot settle it: WordNet's synonymy is synset
co-membership, which rejects *encourage*/*urge* and *masculine*/*male* while
accepting spelling variants like *abcs*/*abc*. So the synonym is a parameter,
and what this row verifies is the decidable half — that the claimed synonym is a
real word, that it is not the word itself, and that its letters appear in order.
`univocalic_translation` treats its own undecidable half the same way.
"""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register


class KangarooWordParams(DiacriticParams):
    synonym: str = Field(description="The synonym the word is claimed to carry.")


def _in_order(needle: str, haystack: str) -> bool:
    letters = iter(haystack)
    return all(character in letters for character in needle)


@register
class KangarooWord(BaseProcedure[KangarooWordParams]):
    """The decidable half of the form: a real word, hidden in order, not itself."""

    id = "kangaroo_word"

    @classmethod
    def params_model(cls) -> type[KangarooWordParams]:
        return KangarooWordParams

    def _check(self, text: str, pack: LanguagePack, params: KangarooWordParams) -> Report:
        host = "".join(ch for ch in text.casefold() if ch.isalpha())
        synonym = "".join(ch for ch in params.synonym.casefold() if ch.isalpha())
        violations: list[Violation] = []
        good = 0
        total = 3

        if pack.is_word(synonym):
            good += 1
        else:
            violations.append(
                Violation(
                    rule="not_a_word",
                    offset=None,
                    found=params.synonym,
                    expected="a word the lexicon knows",
                )
            )

        if synonym and synonym != host:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="synonym_is_the_word",
                    offset=None,
                    found=params.synonym,
                    expected="a different word",
                )
            )

        if _in_order(synonym, host):
            good += 1
        else:
            violations.append(
                Violation(
                    rule="synonym_not_in_order",
                    offset=0,
                    found=params.synonym,
                    expected=f"letters appearing in order within {text!r}",
                )
            )

        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={"hidden_letters": float(len(synonym))},
        )
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/test_kangaroo_word.py -q
```

Expected: PASS. Verify by hand that `encourage`/`urge` really is accepted — that case is
the reason this row is designed this way, and if it fails the design is wrong rather than
the test.

- [ ] **Step 5: Add the golden fixture**

Create `src/denckring/eval/fixtures/golden/kangaroo_word.yaml`:

```yaml
procedure: kangaroo_word
lang: en
cases:
  - name: encourage-urge
    source: the form's most cited example
    text: encourage
    params: { synonym: urge }
    satisfied: true
  - name: letters-out-of-order
    source: constructed counterexample
    text: encourage
    params: { synonym: rug }
    satisfied: false
```

- [ ] **Step 6: Add the Hypothesis strategy**

Create `tests/strategies/kangaroo_word.py`:

```python
"""Generators for kangaroo_word.

The satisfying case cannot be generated blind — a real hidden synonym has to be
known in advance — so this samples verified pairs, as `rhyme_royal` does.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

PAIRS = [("encourage", "urge"), ("chocolate", "cocoa"), ("rapscallion", "rascal")]


def satisfying() -> CaseStrategy:
    return st.sampled_from(PAIRS).map(lambda pair: (pair[0], {"synonym": pair[1]}))


def violating() -> CaseStrategy:
    return st.just(("encourage", {"synonym": "rug"}))
```

- [ ] **Step 7: Update the counts, run everything, commit**

`tests/test_describe.py` carries hardcoded implemented-counts (114) and a core-only
runnable count. Move the implemented counts to 115 and work out the third yourself:
`kangaroo_word` needs `lexicon.words`, which the core `EnglishPack` lacks.

```bash
uv run pytest -q && uv run denckring eval
git add src/denckring/procedures/kangaroo_word.py src/denckring/eval/fixtures/golden/kangaroo_word.yaml tests/strategies/kangaroo_word.py tests/test_kangaroo_word.py tests/test_describe.py
git commit -m "feat: implement kangaroo_word, which needed no thesaurus"
```

---

### Task 3: The build script and the OEWN migration

The riskiest task in the plan. It regenerates a list a shipped procedure walks in order,
so `n_plus_7` and `s_plus_7` output changes.

**Files:**
- Create: `packages/denckring-en-data/scripts/build_lexicon.py`
- Modify: `packages/denckring-en-data/src/denckring_en_data/data/nouns.txt`
- Create: `packages/denckring-en-data/src/denckring_en_data/data/glosses.txt.gz`
- Create: `packages/denckring-en-data/src/denckring_en_data/data/metadata.json`
- Modify: `packages/denckring-en-data/LICENSE-WORDNET`, `packages/denckring-en-data/README.md`, `pyproject.toml`
- Modify: `src/denckring/eval/fixtures/golden/{n_plus_7,s_plus_7}.yaml`
- Test: `tests/test_lang_en_data.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `glosses.txt.gz` as `lemma\tgloss | gloss | gloss` lines; `metadata.json` with `generated`, `source` and `counts` keys; a regenerated `nouns.txt`.

- [ ] **Step 1: Add `wn` as a build-only dependency**

In the root `pyproject.toml`, add to the PEP 735 dependency groups:

```toml
[dependency-groups]
lexicon = ["wn>=1.1"]
```

It is never imported at runtime and never installed by `pip install denckring[en]`.
Verify that by grepping: `wn` must appear in no file under `src/` or
`packages/*/src/`.

- [ ] **Step 2: Write the failing test**

Create `tests/test_lang_en_data.py`, mirroring `tests/test_lang_de_data.py`:

```python
"""The English data files are now reproducible, as the German ones already were."""

import gzip
import json
from pathlib import Path

import pytest

en_data = pytest.importorskip("denckring_en_data", reason="needs denckring[en]")

DATA = Path(en_data.__file__).parent / "data"


def _read_gz(path: Path) -> list[str]:
    return gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()


def test_shipped_files_match_the_recorded_metadata_counts() -> None:
    """`nouns.txt` was hand-extracted and committed with no script, so nothing
    could tell whether it had drifted. `metadata.json` records the counts beside
    the data, and a truncated download or bad regeneration fails here loudly."""
    metadata = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))
    nouns = (DATA / "nouns.txt").read_text(encoding="utf-8").split()
    glosses = _read_gz(DATA / "glosses.txt.gz")
    assert len(nouns) == metadata["counts"]["nouns.txt"]
    assert len(glosses) == metadata["counts"]["glosses.txt.gz"]


def test_the_metadata_names_the_wordnet_version_it_came_from() -> None:
    """The previous list recorded nothing, which is why establishing its
    provenance took a licence file and a guess."""
    metadata = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))
    assert "oewn" in metadata["source"].lower()
    assert "2024" in metadata["source"]
```

- [ ] **Step 3: Run it and watch it fail**

```bash
uv run pytest tests/test_lang_en_data.py -q
```

Expected: FAIL — no `metadata.json`, no `glosses.txt.gz`.

- [ ] **Step 4: Write the build script**

Create `packages/denckring-en-data/scripts/build_lexicon.py`. Read
`packages/denckring-de-data/scripts/build_lexicon.py` first and follow its shape: a
docstring stating why it is committed, `write()` using `gzip.compress(payload, mtime=0)`
so rebuilds are byte-identical, and `write_metadata()` recording counts.

It must:

1. Load OEWN 2024 via `wn` (`wn.download("oewn:2024")`, then `wn.Wordnet("oewn:2024")`).
2. Write `nouns.txt` — every alphabetic single-word noun lemma, lowercased,
   deduplicated, sorted. This matches what the vendored list contained.
3. Write `glosses.txt.gz` — one line per lemma, `lemma\tgloss | gloss`, every sense,
   sorted by lemma. Lemmas are lowercased and restricted to alphabetic single words.
4. Write `metadata.json` with `generated`, a `source` string naming **OEWN 2024** and
   its CC BY 4.0 licence, and `counts` for both files.

Expected output, which the tests above pin: **78,866 gloss lines** and **134,298
glosses** in total. The noun count will be close to but not identical to the previous
55,239 — record whatever it actually is.

- [ ] **Step 5: Run the script and inspect the diff before trusting it**

```bash
uv run --group lexicon python packages/denckring-en-data/scripts/build_lexicon.py
git diff --stat packages/denckring-en-data/src/denckring_en_data/data/
```

Then check the noun-list change is what the spec predicts — roughly 1,247 additions and
18 removals against the old list, case-folded. If it differs by an order of magnitude,
stop and report: the extraction is selecting the wrong thing.

- [ ] **Step 6: Replace the licence and correct the README**

`packages/denckring-en-data/LICENSE-WORDNET` currently carries Princeton WordNet 3.1's
licence and states it covers `nouns.txt`. No Princeton data remains, so replace it with
Open English WordNet's CC BY 4.0 licence and attribution string, and say it covers
`nouns.txt` and `glosses.txt.gz`.

`packages/denckring-en-data/README.md`'s Data section names only CMUdict, though the
package has shipped WordNet-derived nouns since it was created. Correct it to name both
sources with their licences.

- [ ] **Step 7: Regenerate the N+7 and S+7 fixtures**

Both walk the ordered noun list, so their output has changed. For each case in
`src/denckring/eval/fixtures/golden/{n_plus_7,s_plus_7}.yaml`, run the procedure's
`apply` against the new list and record what it now produces.

**Derive each new value; never edit a fixture until it passes.** The distinction matters:
one records what the procedure does, the other records what makes the test quiet.

- [ ] **Step 8: Run everything and commit**

```bash
uv run pytest -q && uv run denckring eval
git add packages/denckring-en-data src/denckring/eval/fixtures/golden/n_plus_7.yaml src/denckring/eval/fixtures/golden/s_plus_7.yaml tests/test_lang_en_data.py pyproject.toml
git commit -m "feat: build the English lexicon from Open English WordNet, reproducibly"
```

---

### Task 4: The `lexicon.glosses` capability

**Files:**
- Modify: `src/denckring/lang/base.py`, `src/denckring/core/protocol.py`
- Modify: `packages/denckring-en-data/src/denckring_en_data/__init__.py`
- Test: `tests/test_glosses.py` (create)

**Interfaces:**
- Consumes: `glosses.txt.gz` from Task 3.
- Produces: `LanguagePack.glosses(word) -> Sequence[str]`, returning every sense's definition, or an empty sequence for a word it cannot resolve. Gated on `GLOSSES = "lexicon.glosses"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_glosses.py`:

```python
"""Definitions, and an honest answer when there are none."""

import pytest

from denckring.core.errors import MissingCapability
from denckring.lang import get_pack
from denckring.lang.en import EnglishPack


def test_a_pack_without_the_capability_raises() -> None:
    with pytest.raises(MissingCapability):
        EnglishPack().glosses("bank")


def test_every_sense_is_returned_not_just_the_first() -> None:
    """A writer replacing `bank` with the riverbank sense is doing the procedure
    correctly, so a checker accepting only the first sense rejects correct work."""
    found = get_pack("en").glosses("bank")
    assert len(found) > 1


def test_an_inflected_form_resolves_through_the_fallback() -> None:
    assert get_pack("en").glosses("birds")


def test_an_unresolvable_word_returns_nothing_rather_than_guessing() -> None:
    """`went` needs irregular morphology, which is out of reach. The rows that
    consume this count such words and disclose them; none of them guess."""
    assert get_pack("en").glosses("flurbish") == ()
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/test_glosses.py -q
```

Expected: FAIL — `EnglishPack` has no `glosses`.

- [ ] **Step 3: Add the capability constant and the base method**

In `src/denckring/lang/base.py`, beside `NOUNS` and `WORDS`:

```python
GLOSSES = "lexicon.glosses"
```

and on `BasePack`, beside `is_word` and `nouns`:

```python
    def glosses(self, word: str) -> Sequence[str]:
        """Every definition the lexicon carries for this word.

        Every sense, not the first: which sense a writer meant is not knowable
        from the text, so a caller that accepts any of them is the honest reader.
        An empty sequence means the lexicon could not resolve the word at all.
        """
        raise MissingCapability(DIRECT_CALL, self.lang, GLOSSES)
```

Add the same signature to the `LanguagePack` protocol in
`src/denckring/core/protocol.py`, beside `is_word` and `nouns`.

- [ ] **Step 4: Implement it in the data pack**

In `packages/denckring-en-data/src/denckring_en_data/__init__.py`:

- Add `GLOSSES_PATH = Path(str(files("denckring_en_data") / "data" / "glosses.txt.gz"))`.
- Add an `@lru_cache(maxsize=1)` loader `gloss_table() -> dict[str, tuple[str, ...]]`
  reading the gzip and splitting each line on `\t` then on `" | "`.
- Add `GLOSSES` to the `capabilities` frozenset.
- Implement resolution, trying in order: the word as given, `self._lemma(word)`, then a
  plain-inflection fallback stripping a trailing `s`, `es`, `ed` or `ing`:

```python
    def glosses(self, word: str) -> tuple[str, ...]:
        table = gloss_table()
        lemma = self._lemma(word)
        for candidate in (lemma, *_inflections(lemma)):
            found = table.get(candidate)
            if found:
                return found
        return ()
```

with a module-level helper:

```python
def _inflections(lemma: str) -> tuple[str, ...]:
    """Plain English inflections only. Irregulars — `went` for `go` — are out of
    reach, and a word this cannot resolve returns nothing rather than a guess."""
    candidates = []
    for suffix in ("s", "es", "ed", "ing"):
        if lemma.endswith(suffix) and len(lemma) > len(suffix) + 2:
            candidates.append(lemma[: -len(suffix)])
    return tuple(candidates)
```

- [ ] **Step 5: Run the tests, the suite, and commit**

```bash
uv run pytest tests/test_glosses.py -q
uv run pytest -q && uv run mypy --strict src tests
git add src/denckring/lang/base.py src/denckring/core/protocol.py packages/denckring-en-data tests/test_glosses.py
git commit -m "feat: lexicon.glosses, every sense or nothing"
```

---

### Task 5: `definitional_expansion`

**Files:**
- Create: `src/denckring/procedures/definitional_expansion.py`
- Create: fixture and strategy
- Test: `tests/test_definitional.py` (create)

**Interfaces:**
- Consumes: `pack.glosses` from Task 4; `SourceParams`.
- Produces: `_replaced_by_gloss(source, text, pack) -> tuple[list[Violation], int, int, int]` returning violations, good, total and the count of unresolved words — Task 6 uses it.

*Each substantive word replaced once by its dictionary definition.*

**Test the comparison against real text first, not last.** Gloss text is third-party
prose carrying parentheses, semicolons and quotes. Too strict a match makes this row
unsatisfiable in the way synonyms already proved possible. Decide the comparison by
running it, and record what you chose in the docstring.

- [ ] **Step 1: Write the failing test**

Create `tests/test_definitional.py`:

```python
"""Replacing a word with what the dictionary says it means."""

from denckring import check

SOURCE = "the cat sat"


def test_a_word_replaced_by_one_of_its_definitions_is_accepted() -> None:
    gloss = "feline mammal usually having thick soft fur"
    assert check("definitional_expansion", f"the {gloss} sat", source=SOURCE).satisfied is True


def test_a_word_left_unexpanded_is_reported() -> None:
    report = check("definitional_expansion", SOURCE, source=SOURCE)
    assert report.satisfied is False
    assert any(v.rule == "not_expanded" for v in report.violations)


def test_words_the_lexicon_cannot_resolve_are_disclosed_not_failed() -> None:
    """`went` needs irregular morphology. A report drawn from partial knowledge
    must say so rather than quietly scoring over fewer words."""
    report = check("definitional_expansion", "he went", source="he went")
    assert report.metrics["estimated_words"] >= 1.0
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/test_definitional.py -q
```

Expected: FAIL — the procedure does not exist.

- [ ] **Step 3: Find the comparison that works, before writing the row**

Run this and read the output:

```bash
uv run python -c "
from denckring.lang import get_pack
p = get_pack('en')
for w in ['cat','sat','garden','evening']:
    print(w, '->', p.glosses(w)[:2])
"
```

Decide from what you see how a gloss is matched inside the result — the whole gloss
verbatim, or its content words in order. Whichever you choose, **state it in the module
docstring** and make the test above pass with a gloss taken verbatim from
`pack.glosses("cat")` rather than one you wrote by hand.

- [ ] **Step 4: Implement, run, fixture, strategy, commit**

The row mixes in `SourceParams`, walks the source's words, and for each word that
resolves to at least one gloss requires that one of them appears in the result. Words
resolving to nothing are counted into an `estimated_words` metric and neither pass nor
fail — the contract the syllable, stress and rhyme paths share.

Ships `check` only. It is `kind: both`; record the deferral in the docstring citing
ADR 0002.

```bash
uv run pytest -q && uv run denckring eval
git add src/denckring/procedures/definitional_expansion.py src/denckring/eval/fixtures/golden/definitional_expansion.yaml tests/strategies/definitional_expansion.py tests/test_definitional.py tests/test_describe.py
git commit -m "feat: implement definitional_expansion"
```

---

### Task 6: `definitional_literature`

**Files:**
- Create: `src/denckring/procedures/definitional_literature.py`
- Create: fixture and strategy
- Test: extend `tests/test_definitional.py`

**Interfaces:**
- Consumes: `_replaced_by_gloss` from Task 5.
- Produces: nothing later tasks use.

*Replace each substantive word by its dictionary definition, and repeat.*

The same comparison as Task 5, applied repeatedly. Accept a text reachable from the
source by one **or more** iterations, and report how many were found in an `iterations`
metric. Extract the shared comparison out of `definitional_expansion` now that a second
caller needs it — not before.

- [ ] **Steps:** failing test first (a two-iteration example accepted, a text reachable by
  no number of iterations rejected), then the row, then fixture and strategy, then the
  suite, then commit as `feat: implement definitional_literature`.

Bound the iteration count so a pathological input cannot loop: stop after a small fixed
number of rounds — read `MAX_COMBINATIONS` in `src/denckring/core/prosody.py` for the
codebase's precedent on caps — and say in the docstring what the bound is and why.

---

### Task 7: CHANGELOG and final verification

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read the established format**

```bash
git show 68bbf40 -- CHANGELOG.md
git show 40566bf -- CHANGELOG.md
```

Prose in bullets, explaining why rather than listing what.

- [ ] **Step 2: Write the entry**

Cover: `lexicon.glosses` and what it returns; the build script and that `nouns.txt` was
previously an opaque hand-extracted blob; the OEWN migration; **the N+7 and S+7 output
change, called out in bold as a behaviour change** in the style of
`prisoners_constraint`'s folding correction; the licence replacement; `kangaroo_word`,
`definitional_expansion` and `definitional_literature`; and the four catalogue
corrections — including that `lexicon.synonyms` and `lexicon.antonyms` were measured and
deliberately not built, with the figures.

- [ ] **Step 3: Verify the whole branch**

```bash
uv run pytest -q
uv run mypy --strict src tests
uv run ruff check src tests && uv run ruff format --check src tests
uv run denckring eval
uv run denckring status
uv run python scripts/build_docs.py && uv run mkdocs build --strict
```

`status` must read `152 catalogued · 126 implementable · 117 implemented · 117 validated · 26 not mechanically checkable`.

**`mkdocs build --strict` is a CI job and is easy to forget.** It regenerates the gallery
from the catalogue, and this branch changes four rows and adds three.

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: record the glosses batch"
```

---

## Self-Review

**Spec coverage.** The capability is Task 4; the build script and migration Task 3; the
licence and README Task 3 Step 6; the four corrections Task 1; `kangaroo_word` Task 2;
the two `definitional_*` rows Tasks 5 and 6; the scoreboard assertion Task 7. The spec's
`lexicon.synonyms`/`lexicon.antonyms` non-goals are covered by Task 1 Step 5, which
records the measurements in the catalogue rather than merely omitting the capabilities.

**Known softness, stated rather than hidden.** Tasks 5 and 6 give full failing tests and
interface contracts but leave the gloss-comparison rule to be decided by running it
against real gloss text. That is deliberate: the spec names it as the one thing that must
be tested early, and a comparison chosen from a plan author's imagination is exactly how
`synonymic_substitution` would have been built before anyone measured it. Task 5 Step 3
is that measurement, and it gates the implementation.

**Type consistency.** `glosses()` returns `Sequence[str]` on the protocol and
`tuple[str, ...]` in the data pack, which satisfies it. `_replaced_by_gloss` is defined in
Task 5 and consumed in Task 6 under the same name. `GLOSSES = "lexicon.glosses"` matches
the `lexicon.`-prefixed constants already in `lang/base.py`.
