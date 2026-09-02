# Letter classification and the folding seam — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the six rows that misbehave under default parameters in German and French, by folding the parameter side of every letter comparison and splitting the three jobs `pack.vowels()` does at once.

**Architecture:** `fold_diacritics` defaults to `true`; `letter_spans` folds the text and nothing folds the parameter. One helper in `core/text.py` closes that seam at every site. Separately, `pack.vowels()` answers three different questions — which characters are vowel-shaped (`word_ladder`), which base vowels a text must contain one of (`supervocalic`), and which letters in a text function as vowels (`spoonerism`). The first keeps the name, the second becomes `vowel_inventory()`, the third becomes `letter_classes()` and is licensed only for rows declaring `phonemes`.

**Tech Stack:** Python 3.12+, pydantic v2, pytest, hypothesis, mypy --strict, ruff.

**Spec:** `docs/superpowers/specs/2026-09-02-letter-classification-design.md`

## Global Constraints

- **The gate is four commands, all of which must pass before every commit:**
  `uv run pytest -q` · `uv run mypy --strict src tests` · `uv run ruff check .` · `uv run ruff format --check .`
- **For any task touching a procedure, also:** `uv run denckring eval --all` (expect `121 procedures · 487 passed · 0 failed`, plus the cases this plan adds) and `uv run denckring status` (expect `155 · 130 · 121 · 121 · 25`, then `0 instruments catalogued` — **these six numbers must not change**).
- **Commit author is `senzelden <sunless@gmx.net>`.** The trailer is `Assisted-by: Claude:claude-opus-5[1m]`. Never `Co-Authored-By:`, never `Signed-off-by:`, never `Claude-Session:`.
- **Do not push.** `origin/main` is pinned at `f0ffdcb` by decision; commit freely, push nothing.
- **House style:** comments explain *why*, not what, and cite ADRs by number. A comment that has become false is a defect, not a nit.
- **No editorial `languages` value changes in this plan**, and no catalogue `definitions` changes. `runs_in` is computed and moves on its own or not at all.
- **`procedure_id` is a reserved test-argument name** — `tests/conftest.py` auto-parametrises any test taking it. Name the argument `pid`.
- Golden fixture cases require a `source:` field naming provenance. Constructed examples say so.

---

### Task 1: The folding helpers

**Files:**
- Modify: `src/denckring/core/text.py` (add after `letter_spans`, line 22)
- Test: `tests/test_text_helpers.py` (create)

**Interfaces:**
- Consumes: `LanguagePack.fold_diacritics`, `denckring.core.errors.InvalidParams`
- Produces:
  - `fold_letter(ch: str, pack: LanguagePack, *, fold: bool) -> str` — one source character to the letters it contributes. Multi-character for `ß` under folding.
  - `single_letter(value: str, pack: LanguagePack, *, fold: bool, procedure_id: str, field: str) -> str` — the one folded letter a single-letter parameter denotes, or `InvalidParams`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_text_helpers.py`:

```python
"""The parameter side of the diacritic fold.

`letter_spans` folds the text; until these helpers existed nothing folded the
parameter compared against it, so `vowel="ä"` was unsatisfiable in German and
`deleted="s"` never removed a `ß`. See ADR 0035 and the 2026-09-02 sweep,
Finding 1.
"""

import pytest

from denckring.core.errors import InvalidParams
from denckring.core.text import fold_letter, single_letter
from denckring.lang import get_pack


def test_folding_a_plain_letter_lowercases_it() -> None:
    assert fold_letter("A", get_pack("en"), fold=True) == "a"


def test_folding_an_umlaut_strips_the_mark() -> None:
    assert fold_letter("Ä", get_pack("de"), fold=True) == "a"


def test_not_folding_keeps_the_mark_and_only_lowercases() -> None:
    assert fold_letter("Ä", get_pack("de"), fold=False) == "ä"


def test_eszett_folds_to_two_letters() -> None:
    """`ß` casefolds to `ss`, so one character contributes two letters — the
    fact `slenderizing` and `acrostic` both got wrong."""
    assert fold_letter("ß", get_pack("de"), fold=True) == "ss"


def test_the_french_ligature_folds_to_two_letters() -> None:
    assert fold_letter("œ", get_pack("fr"), fold=True) == "oe"


def test_a_single_letter_parameter_folds_to_one_letter() -> None:
    assert single_letter(
        "ä", get_pack("de"), fold=True, procedure_id="univocalic", field="vowel"
    ) == "a"


def test_a_single_letter_parameter_is_lowercased_when_not_folding() -> None:
    assert single_letter(
        "Ä", get_pack("de"), fold=False, procedure_id="univocalic", field="vowel"
    ) == "ä"


def test_a_parameter_folding_to_two_letters_is_refused_by_name() -> None:
    """`degenerate_output` advising `allow_identity` was the old answer, and it
    named the wrong cause entirely — see the spec's D4."""
    with pytest.raises(InvalidParams) as caught:
        single_letter(
            "ß", get_pack("de"), fold=True, procedure_id="slenderizing", field="deleted"
        )
    message = str(caught.value)
    assert "deleted" in message
    assert "ss" in message
    assert "fold_diacritics" in message


def test_the_refusal_names_the_procedure() -> None:
    with pytest.raises(InvalidParams) as caught:
        single_letter(
            "œ", get_pack("fr"), fold=True, procedure_id="univocalic", field="vowel"
        )
    assert caught.value.procedure_id == "univocalic"


def test_a_letter_that_folds_to_two_is_usable_with_folding_off() -> None:
    """The refusal must name a way out that actually works."""
    assert single_letter(
        "ß", get_pack("de"), fold=False, procedure_id="slenderizing", field="deleted"
    ) == "ß"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_text_helpers.py -q`
Expected: FAIL — `ImportError: cannot import name 'fold_letter' from 'denckring.core.text'`

- [ ] **Step 3: Implement the helpers**

In `src/denckring/core/text.py`, add the `InvalidParams` import at the top:

```python
from denckring.core.errors import InvalidParams
```

and add both functions immediately after `letter_spans`:

```python
def fold_letter(ch: str, pack: LanguagePack, *, fold: bool) -> str:
    """One source character as the letters it contributes to a folded text.

    The parameter-side twin of `letter_spans`: that folds the text, and until
    this existed nothing folded the value compared against it, so `vowel="ä"`
    was unsatisfiable in German (ADR 0035). Multi-character under folding —
    `ß` gives `ss` — which is why `single_letter` exists beside it.
    """
    return pack.fold_diacritics(ch) if fold else ch.lower()


def single_letter(
    value: str, pack: LanguagePack, *, fold: bool, procedure_id: str, field: str
) -> str:
    """The one folded letter a single-letter parameter denotes.

    Refused when the fold yields more than one letter, because these callers
    compare letter against letter and a two-letter `expected` against a
    one-character `got` is not a comparison the violation can report honestly.
    The message names `fold_diacritics: false` because that genuinely works —
    the old `degenerate_output`/`allow_identity` advice named neither the cause
    nor a remedy (ADR 0035, D4).
    """
    folded = fold_letter(value, pack, fold=fold)
    if len(folded) != 1:
        raise InvalidParams(
            procedure_id,
            f"{field}={value!r} folds to {folded!r} under fold_diacritics; "
            f"pass fold_diacritics=false to use it as a single letter",
        )
    return folded
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_text_helpers.py -q`
Expected: PASS, 10 passed

- [ ] **Step 5: Run the full gate**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
```
Expected: all four clean. `core/text.py` importing `core/errors` is not a cycle — `errors.py` imports nothing from `core.text`.

- [ ] **Step 6: Commit**

```bash
git add src/denckring/core/text.py tests/test_text_helpers.py
git commit -m "feat: fold the parameter side of a letter comparison

letter_spans folds the text and nothing folded the value compared
against it, so vowel=\"ä\" was unsatisfiable in German and deleted=\"s\"
never removed a ß. fold_letter is the parameter-side twin; single_letter
refuses a parameter whose fold yields two letters and names
fold_diacritics: false, which is a remedy that works — unlike the
degenerate_output/allow_identity advice it replaces.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 2: `slenderizing` — the generator that fails its own checker

**Files:**
- Modify: `src/denckring/procedures/slenderizing.py:44-51` (`_check`), `:85-97` (`_produce`)
- Modify: `src/denckring/eval/fixtures/golden/slenderizing.yaml`
- Test: `tests/test_slenderizing.py`, `tests/test_round_trip.py` (add the structural guard)

**Interfaces:**
- Consumes: `fold_letter`, `single_letter` from Task 1
- Produces: nothing later tasks depend on

This is the row that breaks the project's thesis, and it is fixed early because closing
the net around it is the spec's L0.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_slenderizing.py`:

```python
def test_apply_output_satisfies_its_own_checker_in_german() -> None:
    """The thesis, in the language that broke it.

    `_produce` kept a character when `fold_diacritics(ch).lower() != deleted`;
    `ß` folds to `ss`, which never equals one letter, so `ß` always survived —
    while `_check` expanded it into two `s` and dropped both. Measured before
    the fix: apply gave 'Die traße war groß.' and its own check scored 0.412
    with seven violations. See ADR 0035, D6.
    """
    procedure = get("slenderizing")
    assert isinstance(procedure, Constructive)
    source = "Die Straße war groß."
    produced = procedure.apply(source, lang="de", deleted="s")
    assert check("slenderizing", produced, lang="de", source=source, deleted="s").satisfied


def test_the_eszett_is_removed_as_two_esses() -> None:
    """Folding says `ß` is `ss`, so deleting `s` must take the `ß` with it."""
    produced = get("slenderizing").apply("Die Straße war groß.", lang="de", deleted="s")
    assert produced == "Die trae war gro."


def test_a_deleted_letter_that_folds_to_two_is_refused_by_name() -> None:
    """`deleted="ß"` used to raise `degenerate_output` advising
    `allow_identity=true`, which would have returned the untouched text as a
    slenderizing. D4 names the real cause instead.
    """
    with pytest.raises(InvalidParams) as caught:
        get("slenderizing").apply("Die Straße war groß.", lang="de", deleted="ß")
    assert "fold_diacritics" in str(caught.value)


def test_the_eszett_can_be_deleted_with_folding_off() -> None:
    produced = get("slenderizing").apply(
        "Die Straße war groß.", lang="de", deleted="ß", fold_diacritics=False
    )
    assert "ß" not in produced
```

with these imports at the top of the file:

```python
import pytest

from denckring import check
from denckring.core.errors import InvalidParams
from denckring.core.protocol import Constructive
from denckring.core.registry import get
```

Append the structural guard to `tests/test_round_trip.py`:

```python
def test_every_gated_folding_row_has_a_non_default_language_case() -> None:
    """A `PARAMETER_GATED` row is invisible to the property above, so its golden
    file is the only net it has — and a golden file pinning one language is not a
    net at all for a row whose defect is language-shaped.

    `slenderizing` was gated *and* fixtured `lang: en` at file level with two
    ASCII cases, so the row excluded from the safety net was the row that broke,
    and the gate stayed green. Narrowed to rows declaring `fold_diacritics`,
    because that is what makes a row language-shaped: `pasigraphy` is gated too
    and requires only `tokens`, its whole mechanism being a caller-supplied
    table, so a German case there would assert nothing.
    """
    import yaml

    for pid in sorted(PARAMETER_GATED):
        if "fold_diacritics" not in all_procedures()[pid].meta.requires:
            continue
        path = FIXTURES / "golden" / f"{pid}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        default = data.get("lang", "en")
        languages = {case.get("lang", default) for case in data["cases"]}
        assert languages != {default}, (
            f"{pid} is parameter-gated out of the round-trip property and its golden "
            f"file only exercises {default!r}; the property cannot see it and neither "
            f"can the fixtures"
        )
```

Add near the top of `tests/test_round_trip.py`, beside the existing imports:

```python
from pathlib import Path

import denckring.eval as _eval

FIXTURES = Path(_eval.__file__).parent / "fixtures"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_slenderizing.py tests/test_round_trip.py::test_every_gated_folding_row_has_a_non_default_language_case -q`
Expected: FAIL — four failures. The round-trip guard fails with "slenderizing is parameter-gated ... only exercises 'en'"; `test_apply_output_satisfies_its_own_checker_in_german` fails on `assert False`; `test_the_eszett_is_removed_as_two_esses` fails comparing `'Die traße war groß.'` to `'Die trae war gro.'`; the refusal test fails with `DID NOT RAISE`.

- [ ] **Step 3: Fix `_check` and `_produce`**

In `src/denckring/procedures/slenderizing.py`, change the import line:

```python
from denckring.core.text import letter_spans, single_letter
```

Replace the body of `_check` up to and including the `expected`/`actual` bindings:

```python
    def _check(self, text: str, pack: LanguagePack, params: SlenderizingParams) -> Report:
        fold = params.fold_diacritics
        deleted = single_letter(
            params.deleted, pack, fold=fold, procedure_id=self.id, field="deleted"
        )
        expected = [ch for _, ch in letter_spans(params.source, pack, fold=fold) if ch != deleted]
        actual = [ch for _, ch in letter_spans(text, pack, fold=fold)]
```

Replace `_produce` entirely:

```python
    def _produce(self, text: str, pack: LanguagePack, params: SlenderizingApplyParams) -> Produced:
        """Strike the letter out of `text` and let the rest close up.

        Goes through the same letter model as `_check` — `letter_spans`, and the
        same folded `deleted` — because comparing a folded character against an
        unfolded parameter is what let `ß` survive a deletion the checker then
        required, breaking the round trip in German under default parameters
        (ADR 0035, D6). A character is dropped when *any* letter it folds to is
        the deleted one, which is what makes `ß` go with `s`.

        No seed: there is exactly one slenderizing of a text for a given letter,
        which is why this generator takes no choices at all.
        """
        fold = params.fold_diacritics
        deleted = single_letter(
            params.deleted, pack, fold=fold, procedure_id=self.id, field="deleted"
        )
        return plain(
            [
                "".join(
                    ch
                    for ch in text
                    if not ch.isalpha() or deleted not in fold_letter(ch, pack, fold=fold)
                )
            ]
        )
```

and extend the import to carry `fold_letter`:

```python
from denckring.core.text import fold_letter, letter_spans, single_letter
```

- [ ] **Step 4: Add the German golden cases**

Append to `src/denckring/eval/fixtures/golden/slenderizing.yaml`, under `cases:`:

```yaml
  - name: eszett-goes-with-the-s
    lang: de
    source: >-
      constructed example; ß casefolds to ss, so a text deleting s must lose the
      ß too — the disagreement between apply and check that ADR 0035 D6 fixed
    text: Die trae war gro.
    params: { source: Die Straße war groß., deleted: s }
    satisfied: true
  - name: eszett-kept-while-deleting-s
    lang: de
    source: constructed counterexample; this is exactly what apply used to produce
    text: Die traße war groß.
    params: { source: Die Straße war groß., deleted: s }
    satisfied: false
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_slenderizing.py tests/test_round_trip.py -q`
Expected: PASS

Run: `uv run denckring eval --all`
Expected: `121 procedures · 489 passed · 0 failed` — two more than the 487 baseline, because this task adds two golden cases.

- [ ] **Step 6: Run the full gate**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check . && uv run denckring status
```
Expected: all clean; `status` still `155 · 130 · 121 · 121 · 25` then `0 instruments catalogued`.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/procedures/slenderizing.py \
        src/denckring/eval/fixtures/golden/slenderizing.yaml \
        tests/test_slenderizing.py tests/test_round_trip.py
git commit -m "fix: slenderizing's generator satisfies its own checker in German

_produce kept a character when fold_diacritics(ch).lower() != deleted;
ß folds to ss, which never equals one letter, so ß always survived —
while _check expanded it into two s and dropped both. Measured: apply
gave 'Die traße war groß.' and its own check scored 0.412 with seven
violations, under default parameters, which is the project's thesis
broken in the one row the safety net could not reach.

The row was in PARAMETER_GATED and fixtured lang: en at file level, so
neither net could see it. A structural guard now holds those two facts
together for every gated row that declares fold_diacritics — which
excludes pasigraphy, gated but requiring only tokens.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 3: `univocalic`, `bivocalic`, `monoconsonantal`

**Files:**
- Modify: `src/denckring/procedures/univocalic.py:39-46`, `src/denckring/procedures/bivocalic.py:41-49`, `src/denckring/procedures/monoconsonantal.py:39-46`
- Modify: `src/denckring/eval/fixtures/golden/univocalic.yaml`, `bivocalic.yaml`, `monoconsonantal.yaml`
- Test: `tests/test_folding_seam.py` (create)

**Interfaces:**
- Consumes: `single_letter` from Task 1
- Produces: nothing later tasks depend on

These three keep the flat `pack.vowels()` reading. They are `family: letter`, require
`[tokens, alphabet, fold_diacritics]` and no `phonemes`, so no contextual rule may enter
them — that is the spec's D2, and Task 7 pins the boundary.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_folding_seam.py`:

```python
"""One cause, several rows: a parameter compared against folded text.

`fold_diacritics` defaults to true, the text side folds, and the parameter side
did not — so an accented parameter was unsatisfiable and the violation mixed a
folded `found` with an unfolded `expected`. ADR 0035, and the 2026-09-02 MCP
sweep, Finding 1.
"""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_a_german_umlaut_vowel_is_satisfiable() -> None:
    """`vowel="ä"` reported found "a" against expected "ä" — the seam exactly."""
    assert check("univocalic", "Bäh", lang="de", vowel="ä").satisfied


def test_the_umlaut_vowel_still_rejects_a_foreign_vowel() -> None:
    report = check("univocalic", "Bähe", lang="de", vowel="ä")
    assert not report.satisfied
    assert [v.found for v in report.violations] == ["e"]


def test_an_unfolded_umlaut_vowel_is_distinct_from_its_base() -> None:
    """With folding off, `ä` and `a` are different letters and must stay so."""
    assert not check("univocalic", "Bah", lang="de", vowel="ä", fold_diacritics=False).satisfied
    assert check("univocalic", "Bäh", lang="de", vowel="ä", fold_diacritics=False).satisfied


def test_two_umlaut_vowels_are_satisfiable() -> None:
    assert check("bivocalic", "Bähö", lang="de", vowels="äö").satisfied


def test_an_eszett_consonant_is_refused_by_name() -> None:
    """`consonant="ß"` was unsatisfiable and reported a two-letter `expected`
    against a one-character `got`. D4 refuses it and names the way out."""
    with pytest.raises(InvalidParams) as caught:
        check("monoconsonantal", "Straße", lang="de", consonant="ß")
    assert "fold_diacritics" in str(caught.value)


def test_an_eszett_consonant_works_with_folding_off() -> None:
    assert check(
        "monoconsonantal", "ßeiß", lang="de", consonant="ß", fold_diacritics=False
    ).satisfied


def test_english_is_unchanged_by_the_parameter_fold() -> None:
    """The seam is invisible in ASCII, which is why English never saw it."""
    assert check("univocalic", "Persever, ye perfect men", lang="en", vowel="e").satisfied
    assert check("monoconsonantal", "nine no one", lang="en", consonant="n").satisfied
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_folding_seam.py -q`
Expected: FAIL — `test_a_german_umlaut_vowel_is_satisfiable`, `test_the_umlaut_vowel_still_rejects_a_foreign_vowel`, `test_two_umlaut_vowels_are_satisfiable` and `test_an_eszett_consonant_is_refused_by_name` all fail. The last fails with `DID NOT RAISE`.

- [ ] **Step 3: Fold the parameter in all three**

In `src/denckring/procedures/univocalic.py`, change the import and the two lines that
read the parameter:

```python
from denckring.core.text import letter_spans, single_letter
```

```python
    def _check(self, text: str, pack: LanguagePack, params: UnivocalicParams) -> Report:
        vowel_set = pack.vowels()
        found = [
            (offset, ch)
            for offset, ch in letter_spans(text, pack, fold=params.fold_diacritics)
            if ch in vowel_set
        ]
        # Folded the same way the text was, or `vowel="ä"` is unsatisfiable in
        # German: the text side folds `ä` to `a` and the comparison never met.
        # ADR 0035, D3.
        permitted = (
            None
            if params.vowel is None
            else single_letter(
                params.vowel,
                pack,
                fold=params.fold_diacritics,
                procedure_id=self.id,
                field="vowel",
            )
        )
        if permitted is None and found:
            permitted = Counter(ch for _, ch in found).most_common(1)[0][0]
```

In `src/denckring/procedures/bivocalic.py`, the same import change, and:

```python
        # Each of the two folded as the text was — ADR 0035, D3. `vowels="äö"`
        # was unsatisfiable in German for want of this.
        if params.vowels is not None:
            permitted = {
                single_letter(
                    ch,
                    pack,
                    fold=params.fold_diacritics,
                    procedure_id=self.id,
                    field="vowels",
                )
                for ch in params.vowels
            }
        else:
            permitted = {ch for ch, _ in Counter(ch for _, ch in found).most_common(PERMITTED)}
```

In `src/denckring/procedures/monoconsonantal.py`, the same import change, and:

```python
        # ADR 0035, D3. `consonant="ß"` is refused rather than silently
        # unsatisfiable, because ß folds to two letters and this row compares
        # letter against letter.
        permitted = (
            None
            if params.consonant is None
            else single_letter(
                params.consonant,
                pack,
                fold=params.fold_diacritics,
                procedure_id=self.id,
                field="consonant",
            )
        )
        if permitted is None and found:
            permitted = Counter(ch for _, ch in found).most_common(1)[0][0]
```

- [ ] **Step 4: Add the German golden cases**

Append to `src/denckring/eval/fixtures/golden/univocalic.yaml` under `cases:`:

```yaml
  - name: umlaut-vowel-under-folding
    lang: de
    source: >-
      constructed example; the text side folded ä to a and the parameter did
      not, so vowel "ä" could not be satisfied at all (ADR 0035)
    text: Bäh
    params: { vowel: "ä" }
    satisfied: true
```

Append to `src/denckring/eval/fixtures/golden/bivocalic.yaml`:

```yaml
  - name: two-umlaut-vowels-under-folding
    lang: de
    source: constructed example; the same seam as univocalic's umlaut case
    text: Bähö
    params: { vowels: "äö" }
    satisfied: true
```

Append to `src/denckring/eval/fixtures/golden/monoconsonantal.yaml`:

```yaml
  - name: eszett-consonant-with-folding-off
    lang: de
    source: >-
      constructed example; under folding ß is two letters and the parameter is
      refused by name, so this is the configuration in which it means something
    text: ßeiß
    params: { consonant: "ß", fold_diacritics: false }
    satisfied: true
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_folding_seam.py -q`
Expected: PASS, 7 passed

Run: `uv run denckring eval --all`
Expected: `121 procedures · 492 passed · 0 failed` (489 after Task 2, plus three).

- [ ] **Step 6: Run the full gate**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check . && uv run denckring status
```
Expected: all clean, `status` unchanged.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/procedures/univocalic.py src/denckring/procedures/bivocalic.py \
        src/denckring/procedures/monoconsonantal.py \
        src/denckring/eval/fixtures/golden/univocalic.yaml \
        src/denckring/eval/fixtures/golden/bivocalic.yaml \
        src/denckring/eval/fixtures/golden/monoconsonantal.yaml \
        tests/test_folding_seam.py
git commit -m "fix: fold the vowel and consonant parameters as the text is folded

vowel=\"ä\", vowels=\"äö\" and consonant=\"ß\" were all unsatisfiable in
German under default parameters, and the violations mixed a folded found
with an unfolded expected. These three rows keep the flat vowels()
reading: they are family: letter and require no phonemes, so no
contextual rule enters them (ADR 0035, D2).

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 4: The acrostic family

**Files:**
- Modify: `src/denckring/procedures/acrostic.py:47-52`
- Modify: `src/denckring/procedures/double_acrostic.py` (the `wanted_first`/`wanted_last` bindings)
- Modify: `src/denckring/eval/fixtures/golden/acrostic.yaml`
- Test: `tests/test_folding_seam.py` (append)

**Interfaces:**
- Consumes: `fold_letter` from Task 1
- Produces: nothing later tasks depend on

`target` is a *phrase*, not a single letter, so D4's refusal does not apply here — D3
does. A `ß` in a target flattens to two letters and therefore claims two units, which is
what `letter_spans` already does to a `ß` in the text. `telestich` subclasses `Acrostic`
and is carried for free; `double_acrostic` has its own copy of the expression and is not.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_folding_seam.py`:

```python
def test_an_eszett_in_an_acrostic_target_claims_two_units() -> None:
    """`expected` was a two-character "ss" compared against a one-character
    `got` — a "letter" that no unit could ever match. Flattened, ß claims the
    two units its two letters need. ADR 0035, D3.
    """
    assert check(
        "acrostic", "Sonne\nsehr\ntanzt", lang="de", target="ßt", unit="line"
    ).satisfied


def test_the_flattened_target_still_reports_a_wrong_letter() -> None:
    report = check("acrostic", "Sonne\nmehr\ntanzt", lang="de", target="ßt", unit="line")
    assert not report.satisfied
    assert [(v.rule, v.found, v.expected) for v in report.violations] == [
        ("wrong_letter", "m", "s")
    ]


def test_telestich_inherits_the_flattened_target() -> None:
    """`telestich` subclasses `Acrostic` and reads the last letter of each unit."""
    assert check(
        "telestich", "das\nes\nvot", lang="de", target="ßt", unit="line"
    ).satisfied


def test_a_double_acrostic_target_flattens_on_both_edges() -> None:
    assert check(
        "double_acrostic",
        "sonnes\nsehrs\ntanzt",
        lang="de",
        first="ßt",
        last="sst",
    ).satisfied
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_folding_seam.py -q -k "acrostic or telestich"`
Expected: FAIL. Before running, confirm `double_acrostic`'s real parameter names with
`uv run denckring describe double_acrostic` and correct `first`/`last` in the test above
to match — the plan asserts the behaviour, not the spelling of a field it did not read.

- [ ] **Step 3: Flatten the target in both files**

In `src/denckring/procedures/acrostic.py`, change the import:

```python
from denckring.core.text import fold_letter, letter_spans, line_spans, word_spans
```

and replace the `expected` binding:

```python
        # Flattened, not one entry per source character: `ß` folds to two
        # letters and the text side already spends two units on it, so a
        # per-character expectation compared a two-letter "ss" against a
        # one-character got. ADR 0035, D3.
        expected = [
            letter
            for ch in params.target
            if ch.isalpha()
            for letter in fold_letter(ch, pack, fold=params.fold_diacritics)
        ]
```

Apply the identical change to each target binding in
`src/denckring/procedures/double_acrostic.py`, carrying the same comment by reference
("the same flattening as `acrostic`, ADR 0035 D3") rather than repeating it in full.

- [ ] **Step 4: Add the German golden case**

Append to `src/denckring/eval/fixtures/golden/acrostic.yaml` under `cases:`:

```yaml
  - name: eszett-target-claims-two-units
    lang: de
    source: >-
      constructed example; ß folds to ss and the text side already spends two
      units on it, so the target must too (ADR 0035)
    text: "Sonne\nsehr\ntanzt"
    params: { target: "ßt", unit: line }
    satisfied: true
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_folding_seam.py -q`
Expected: PASS, 11 passed

Run: `uv run denckring eval --all`
Expected: `121 procedures · 493 passed · 0 failed`

- [ ] **Step 6: Run the full gate**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check . && uv run denckring status
```

- [ ] **Step 7: Commit**

```bash
git add src/denckring/procedures/acrostic.py src/denckring/procedures/double_acrostic.py \
        src/denckring/eval/fixtures/golden/acrostic.yaml tests/test_folding_seam.py
git commit -m "fix: an acrostic target flattens the way the text does

A ß in the target produced a two-character expected \"ss\" compared
against a one-character got, so no unit could match it. target is a
phrase rather than a single letter, so D4's refusal does not apply and
D3's flattening does: ß claims the two units its two letters need.

telestich subclasses Acrostic and is carried; double_acrostic keeps its
own copy of the expression and is not, which is why the sweep's two rows
are three.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 5: `vowel_inventory()` and `supervocalic`

**Files:**
- Modify: `src/denckring/core/protocol.py:246` (add to the `LanguagePack` protocol)
- Modify: `src/denckring/lang/base.py:63` (add the default beside `vowels`)
- Modify: `src/denckring/procedures/supervocalic.py:28-31`
- Modify: `src/denckring/eval/fixtures/golden/supervocalic.yaml`
- Test: `tests/test_vowel_inventory.py` (create)

**Interfaces:**
- Consumes: `LanguagePack.vowels`, `LanguagePack.fold_diacritics`
- Produces: `LanguagePack.vowel_inventory() -> frozenset[str]` — the base vowel letters a
  supervocalic must contain one of each. `frozenset({"a","e","i","o","u"})` in all three
  packs, none overriding.

`vowels()` is untouched: `word_ladder:93` widens an alphabet with it and asks no question
about vowelhood, and Task 3's three rows read it flat.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_vowel_inventory.py`:

```python
"""The inventory reading of `vowels()`, split out.

`pack.vowels()` answered three questions at once. `supervocalic` wants the base
letters to require one of each; `monoconsonantal` wants which letters in a text
are vowels; `word_ladder` wants the character set to widen an alphabet with.
English was correct only because its three readings coincide. ADR 0035, D1.
"""

from denckring import check
from denckring.lang import get_pack


def test_every_pack_names_the_same_five() -> None:
    """The definition published for `supervocalic` says five, in every language."""
    for lang in ("en", "de", "fr"):
        assert get_pack(lang).vowel_inventory() == frozenset("aeiou")


def test_the_default_folds_before_removing_the_ambiguous_letters() -> None:
    """Measured: removing `y` without folding first answers eight for German and
    nineteen for French. The order is the whole of the default.
    """
    assert len(get_pack("de").vowels()) == 8
    assert len(get_pack("fr").vowels()) == 21
    assert len(get_pack("de").vowel_inventory()) == 5
    assert len(get_pack("fr").vowel_inventory()) == 5


def test_a_german_supervocalic_is_satisfiable() -> None:
    """No German text could satisfy this row: folded text can never contain
    `ä ö ü`, so they were permanently missing while inflating `a o u` into
    repeated. Here `ä` supplies the `a` and `ß` folds to two consonants."""
    assert check("supervocalic", "Rätsel bloß im Duft", lang="de").satisfied


def test_a_german_supervocalic_still_fails_on_a_repeat() -> None:
    report = check("supervocalic", "Faust bewegt hier Idole.", lang="de")
    assert not report.satisfied
    assert {v.found for v in report.violations if v.rule == "repeated_vowel"} == {"e", "i"}
    assert not [v for v in report.violations if v.rule == "missing_vowel"]


def test_french_does_not_require_y() -> None:
    """French `vowels()` has 21 members including `à â ä ÿ`, so the row demanded
    each of them exactly once in text that had folded them all away. `y` is a
    French vowel letter but the published definition says five."""
    assert check("supervocalic", "Le mot du jardin", lang="fr").satisfied


def test_french_permits_y_without_requiring_it() -> None:
    assert check("supervocalic", "Le stylo du jardin", lang="fr").satisfied


def test_english_is_unchanged() -> None:
    assert check("supervocalic", "facetious", lang="en").satisfied
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_vowel_inventory.py -q`
Expected: FAIL — `AttributeError: 'EnglishPack' object has no attribute 'vowel_inventory'`,
and the three `check` tests fail on `assert False`.

- [ ] **Step 3: Add the protocol method, the default, and rewire `supervocalic`**

In `src/denckring/core/protocol.py`, after the `vowels` line (246):

```python
    def vowel_inventory(self) -> frozenset[str]: ...
```

In `src/denckring/lang/base.py`, immediately after `vowels`:

```python
    def vowel_inventory(self) -> frozenset[str]:
        """The base vowel letters, one of each of which a supervocalic needs.

        Distinct from `vowels()`, which answers which characters are written as
        vowels and therefore carries the accented forms — the reading
        `word_ladder` needs to widen an alphabet. `supervocalic` publishes "each
        of the five vowels exactly once" and folded text can never contain an
        umlaut, so requiring the accented forms made the row unsatisfiable in
        German and French (ADR 0035, D1).

        Folds *before* removing the ambiguous letters, and the order is
        load-bearing: measured, removing `y` without folding first answers eight
        for German and nineteen for French. All three packs inherit `aeiou` and
        none overrides.
        """
        return frozenset(
            {folded for ch in self.vowels() for folded in self.fold_diacritics(ch)}
        ) - _AMBIGUOUS
```

and at module level in the same file, above `BasePack`:

```python
#: Letters that are vowels in some positions and consonants in others, so they
#: belong to no inventory: `y` in all three languages, and French's `ÿ` which
#: folds to it. `supervocalic` publishes "each of the five vowels", and `y` is
#: not one of the five in any of them — French lists it among its vowels but
#: writes `yeux` with it as /j/. ADR 0035, D1.
#:
#: Deliberately NOT the same set as a pack's glide inventory, which is wider
#: (English `y w u i o`): removing those from the inventory would leave English
#: requiring `a` and `e` alone.
_AMBIGUOUS = frozenset("yÿ")
```

In `src/denckring/procedures/supervocalic.py`, change one line:

```python
        vowel_set = pack.vowel_inventory()
```

and update the class docstring to name why:

```python
    """Every vowel once and once only, so an empty text supplies none of them.

    Reads `vowel_inventory()` rather than `vowels()`: the latter carries the
    accented forms, which folded text can never contain, so this row was
    unsatisfiable in German and French (ADR 0035, D1).
    """
```

- [ ] **Step 4: Add the golden cases**

Append to `src/denckring/eval/fixtures/golden/supervocalic.yaml` under `cases:`:

```yaml
  - name: german-umlaut-supplies-the-a
    lang: de
    source: >-
      constructed example; the row required ä ö ü, which folded text can never
      contain, so no German text could satisfy it at all (ADR 0035)
    text: Rätsel bloß im Duft
    params: {}
    satisfied: true
  - name: french-does-not-require-y
    lang: fr
    source: >-
      constructed example; French vowels() has 21 members and the published
      definition says five
    text: Le mot du jardin
    params: {}
    satisfied: true
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_vowel_inventory.py -q`
Expected: PASS, 7 passed

Run: `uv run denckring eval --all`
Expected: `121 procedures · 495 passed · 0 failed`

- [ ] **Step 6: Run the longer typecheck CI uses**

```bash
uv run mypy --strict src tests packages/denckring-en-data/src \
  packages/denckring-de-data/src packages/denckring-de-wiktionary/src
```
Expected: clean. This task changes `LanguagePack`, and the data packages implement it —
the four-command gate does not cover them.

- [ ] **Step 7: Run the full gate and the explorer's**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check . && uv run denckring status
cd apps/explorer && uv run ruff check && uv run ruff format --check && uv run mypy --strict src tests && uv run pytest
```
Expected: library gate clean, `status` unchanged; explorer `344 passed`.

- [ ] **Step 8: Commit**

```bash
git add src/denckring/core/protocol.py src/denckring/lang/base.py \
        src/denckring/procedures/supervocalic.py \
        src/denckring/eval/fixtures/golden/supervocalic.yaml \
        tests/test_vowel_inventory.py
git commit -m "feat: vowel_inventory(), the reading supervocalic actually wants

vowels() carries the accented forms, which folded text can never
contain, so supervocalic required ä ö ü in German and all 21 French
vowel letters — unsatisfiable in both, against a published definition
that says five.

The default folds before removing the ambiguous letters and the order is
load-bearing: measured, removing y without folding first answers eight
for German and nineteen for French. All three packs inherit aeiou.

vowels() is untouched: word_ladder widens an alphabet with it and asks
no question about vowelhood.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 6: `letter_classes()` and `spoonerism` — DEFERRED, DO NOT IMPLEMENT

> **Deferred on 2026-09-02 during pre-flight, before any dispatch.** Implemented exactly
> as written below, this task's rule disagrees with 4 of its own 18 expectations —
> including `fr yoyo`, the case the feature exists for. It gives `CCCV`, not `CVCV`,
> because French `vowels()` contains `y`, so the second `o`'s lookahead sees a vowel;
> and `de Quelle` gives `CVVCCV` against an expected `CCVCCV`, because the German glide
> set excludes `u` while the comment justifying that exclusion argues `qu` is /kv/ — that
> is, that `u` *is* a consonant there. The `ou` digraph pulls against the fix `yoyo`
> needs, so the rule wants another design pass rather than an implementer.
>
> Nothing waits on it: it fixes no row in the Purpose table, and Task 7's
> `test_spoonerism_is_the_licensed_row` reads the catalogue's `requires` only. The text
> below is kept verbatim as the starting point for that design pass — **its expectations
> are known wrong and must be re-derived by measurement, not reused.**

**Files:**
- Modify: `src/denckring/core/protocol.py` (add beside `vowel_inventory`)
- Modify: `src/denckring/lang/base.py` (the default rule), `src/denckring/lang/en.py`, `src/denckring/lang/de.py`, `src/denckring/lang/fr.py` (the glide inventories)
- Modify: `src/denckring/procedures/spoonerism.py:65-81` (`_letter_onset`)
- Test: `tests/test_letter_classes.py` (create)

**Interfaces:**
- Consumes: `LanguagePack.vowels`
- Produces: `LanguagePack.letter_classes(word: str) -> list[LetterRole]` where
  `LetterRole = Literal["vowel", "consonant"]`, one entry per alphabetic character of the
  **unfolded** word.

**This task is independent of Tasks 1–5 and fixes no row in the defect table.** It
improves an approximation `spoonerism` already labels as one. If it slips, nothing else
waits on it.

Name the alias `LetterRole`, not `LetterClass` — `core/source_compare.py:31` already has
`LetterClass = Literal["consonants", "vowels"]`, which is a different question (which
class to *keep*, plural) and must not be confused with this one.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_letter_classes.py`:

```python
"""A letter's class depends on where it sits, and only `spoonerism` may ask.

Every one of the three languages has vowel letters doing consonant work: en
`y w u i o`, de `y i`, fr `y i u ou`. The rule — a vowel letter before another
vowel letter is a glide — measured 30 of 34 on hand-checked cases.

It is licensed here and nowhere else. `univocalic` and its neighbours are
`family: letter`, require no `phonemes`, and applying this to them makes
`onion`, `quick`, `million`, `oui`, `huit` and `nuit` into univocalics, which no
Word Ways editor accepts. ADR 0035, D2; the boundary is pinned in
`tests/test_reading_boundary.py`.
"""

from denckring.lang import get_pack
from denckring.procedures.spoonerism import _letter_onset


def classes(word: str, lang: str) -> str:
    return "".join(
        "V" if role == "vowel" else "C" for role in get_pack(lang).letter_classes(word)
    )


def test_english_y_is_a_consonant_before_a_vowel() -> None:
    assert classes("yes", "en") == "CVC"


def test_english_y_is_a_vowel_elsewhere() -> None:
    assert classes("myth", "en") == "CVCC"
    assert classes("gym", "en") == "CVC"
    assert classes("happy", "en") == "CVCCV"


def test_english_w_is_the_second_case() -> None:
    assert classes("wet", "en") == "CVC"
    assert classes("cwm", "en") == "CVC"


def test_english_u_after_q_is_a_glide() -> None:
    assert classes("quick", "en") == "CCVCC"


def test_english_i_is_a_glide_before_a_vowel() -> None:
    assert classes("onion", "en") == "VCVCC"


def test_french_carries_the_whole_glide_set() -> None:
    assert classes("yoyo", "fr") == "CVCV"
    assert classes("stylo", "fr") == "CCVCV"
    assert classes("pied", "fr") == "CCVC"
    assert classes("huit", "fr") == "CCVC"
    assert classes("oui", "fr") == "CCV"


def test_german_has_essentially_only_y_and_i() -> None:
    assert classes("Yacht", "de") == "CVCCC"
    assert classes("Physik", "de") == "CCVCVC"
    assert classes("Nation", "de") == "CVCVCC"


def test_german_u_after_q_is_not_a_glide() -> None:
    """`qu` is /kv/ in German, not /kw/ — the one measured miss of the general
    rule, so `GermanPack` excludes it explicitly rather than by rule."""
    assert classes("Quelle", "de") == "CCVCCV"


def test_a_word_with_eszett_gets_one_role_per_character() -> None:
    """`ß` casefolds to two characters. Roles are indexed against the source
    word's alphabetic characters, so a whole-string casefold would desynchronise
    them and `_letter_onset` would index the wrong letter — measured, "Straße"
    is 6 alphabetic characters and 7 casefolded.
    """
    assert len(get_pack("de").letter_classes("Straße")) == 6
    assert classes("Straße", "de") == "CCCVCV"


def test_the_spoonerism_onset_improves() -> None:
    """`_letter_onset` split on flat `vowels()` membership, so French `yoyo` had
    an empty onset and English `myth` was entirely onset."""
    assert _letter_onset("yoyo", get_pack("fr")) == ("y", "oyo")
    assert _letter_onset("myth", get_pack("en")) == ("m", "yth")
    assert _letter_onset("yes", get_pack("en")) == ("y", "es")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_letter_classes.py -q`
Expected: FAIL — `AttributeError: ... has no attribute 'letter_classes'`.

Before implementing, run this to record what the current onsets are, so the improvement is
measured rather than assumed:

```bash
uv run python -c "
from denckring.lang import get_pack
from denckring.procedures.spoonerism import _letter_onset
for w, lg in [('yoyo','fr'),('yeux','fr'),('huit','fr'),('oui','fr'),('Yacht','de'),('yes','en'),('myth','en')]:
    print(lg, w, _letter_onset(w, get_pack(lg)))
"
```
Expected (measured on the branch point): `fr yoyo ('', 'yoyo')`, `fr yeux ('', 'yeux')`,
`fr huit ('h', 'uit')`, `fr oui ('', 'oui')`, `de Yacht ('Y', 'acht')`, `en yes ('y', 'es')`,
`en myth ('myth', '')`.

- [ ] **Step 3: Add `LetterRole`, the protocol method and the default rule**

In `src/denckring/core/protocol.py`, beside the other aliases:

```python
#: What a letter is *doing* in a word, which is not what it is in the alphabet.
#: Distinct from `source_compare.LetterClass`, which names a class to keep.
LetterRole = Literal["vowel", "consonant"]
```

and in the `LanguagePack` protocol, after `vowel_inventory`:

```python
    def letter_classes(self, word: str) -> list[LetterRole]: ...
```

In `src/denckring/lang/base.py`, extend the protocol import — `ClassVar` is already
imported, `LetterRole` is not:

```python
from denckring.core.protocol import Lang, LetterRole
```

then, in `BasePack`:

```python
    #: Vowel letters that carry a consonantal glide before another vowel. Per
    #: pack because the inventories genuinely differ: English adds `w`, French
    #: is the richest, German has essentially only `y`. ADR 0035, D2.
    glides: ClassVar[frozenset[str]] = frozenset()

    def letter_classes(self, word: str) -> list[LetterRole]:
        """What each letter is *doing*, one entry per alphabetic character.

        Licensed only for rows declaring `phonemes`. The letter-play rows are
        `family: letter` and require `alphabet` alone; applying this to them
        makes `onion`, `quick`, `oui` and `huit` into univocalics, which is a
        row taking a pronunciation judgement it never advertised — the defect
        class ADR 0030 fixed twice. ADR 0035, D2.

        The rule: a letter in `glides` before another vowel letter is a
        consonant, and a vowel otherwise. Runs on the **unfolded** word,
        because the context is orthographic — `ß` is a consonant whether or not
        it has become `ss`.
        """
        vowels = self.vowels()
        # Lower-cased per character, never `word.casefold()` over the whole
        # string: `ß` casefolds to two characters, so a whole-string fold breaks
        # the one-role-per-character correspondence `_letter_onset` indexes by.
        # Measured: "Straße" is 6 alphabetic characters and 7 casefolded.
        letters = [ch.lower() for ch in word if ch.isalpha()]
        roles: list[LetterRole] = []
        for index, ch in enumerate(letters):
            following = letters[index + 1] if index + 1 < len(letters) else ""
            if ch in self.glides:
                roles.append("consonant" if following in vowels else "vowel")
            else:
                roles.append("vowel" if ch in vowels else "consonant")
        return roles
```

- [ ] **Step 4: Declare each pack's glide inventory**

`src/denckring/lang/en.py`, in `EnglishPack`:

```python
    #: `w` is the genuine second case beside `y` — a consonant in `wet`, a vowel
    #: in the Welsh loans `cwm` and `crwth`. `u` carries /w/ after `q` and `g`
    #: (`quick`, `language`), `i` carries /j/ in `onion`, `o` in `one`.
    glides: ClassVar[frozenset[str]] = frozenset("ywuio")
```

`src/denckring/lang/de.py`, in `GermanPack`:

```python
    #: German has almost none. `y` is confined to loanwords (`Yacht` against
    #: `Physik`); `i` before a vowel is the one native-ish case (`Familie`,
    #: `Nation`). `u` is deliberately absent: `qu` is /kv/, not /kw/, which is
    #: the one measured miss of the general rule.
    glides: ClassVar[frozenset[str]] = frozenset("yi")
```

`src/denckring/lang/fr.py`, in `FrenchPack`:

```python
    #: The richest of the three: French has no separate consonant letters for
    #: its glides, so the vowel letters carry them. `i` is /j/ in `hier`, `u`
    #: is /ɥ/ in `huit`, `ou` is /w/ in `oui`, `y` is /j/ in `yeux`.
    glides: ClassVar[frozenset[str]] = frozenset("yiuo")
```

French's `ou` is a digraph and this per-character rule marks **both** letters consonant in
`oui` — an approximation, acceptable because the sole consumer wants a boundary rather
than a count (spec D5). Add that as a comment on the French line.

- [ ] **Step 5: Rewire `_letter_onset`**

In `src/denckring/procedures/spoonerism.py`, replace the body of `_letter_onset`, keeping
its existing docstring and adding one paragraph:

```python
    roles = pack.letter_classes(word)
    letters = [index for index, ch in enumerate(word) if ch.isalpha()]
    for role, index in zip(roles, letters, strict=True):
        if role == "vowel":
            return word[:index], word[index:]
    return word, ""
```

Add to the docstring:

```
    Asks `pack.letter_classes` rather than flat `vowels()` membership, because a
    letter's class depends on where it sits: French `yoyo` is /jojo/ and had an
    empty onset, English `myth` was entirely onset. This is licensed here and
    nowhere else — this row declares `phonemes`, and `_produce` verifies the
    guess against them before returning, so a better guess can only reduce
    `NoCandidateWord` refusals. ADR 0035, D2.
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_letter_classes.py tests/test_spoonerism.py -q`
Expected: PASS. If any `test_spoonerism.py` case fails, that is a real regression — the
onset guess changed — and must be understood, not renumbered.

- [ ] **Step 7: Run the full gate, the longer typecheck and the explorer's**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src tests packages/denckring-en-data/src \
  packages/denckring-de-data/src packages/denckring-de-wiktionary/src
uv run denckring eval --all && uv run denckring status
```
Expected: all clean; `eval` still `495 passed`, `status` unchanged.

- [ ] **Step 8: Commit**

```bash
git add src/denckring/core/protocol.py src/denckring/lang/base.py \
        src/denckring/lang/en.py src/denckring/lang/de.py src/denckring/lang/fr.py \
        src/denckring/procedures/spoonerism.py tests/test_letter_classes.py
git commit -m "feat: letter_classes(), licensed by phonemes and used only by spoonerism

A letter's class depends on where it sits, and all three languages have
vowel letters doing consonant work: en y w u i o, de y i, fr y i u ou.
_letter_onset split on flat vowels() membership, so French yoyo had an
empty onset and English myth was entirely onset.

Licensed here and nowhere else. spoonerism declares phonemes and
_produce verifies the written guess against them before returning, so a
better guess can only reduce NoCandidateWord refusals.

German excludes u explicitly: qu is /kv/, the one measured miss of the
general rule.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 7: The reading boundary, the ADR, and the changelog

**Files:**
- Create: `tests/test_reading_boundary.py`
- Create: `docs/adr/0035-orthographic-and-phonetic-readings.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: everything above
- Produces: nothing

- [ ] **Step 1: Write the fold-symmetry property**

This is the spec's Testing section: the invariant the seam violated, stated once rather
than per row. Create `tests/test_fold_symmetry.py`:

```python
"""Folding the text and folding the parameter must reach the same verdict.

The seam was that `fold_diacritics: true` folded the text and left the parameter
alone. The invariant that catches every instance of it at once: checking folded
input with folding *on* must agree with checking pre-folded input with folding
*off* and the parameter folded by hand. ADR 0035, D3.
"""

import pytest

from denckring import check
from denckring.lang import get_pack

#: `(procedure, lang, text, letter_params, text_params)`. The two parameter
#: groups fold differently — a letter parameter folds per character and a text
#: parameter folds like any other text — which is precisely the distinction the
#: seam collapsed.
CASES = [
    ("univocalic", "de", "Bäh", {"vowel": "ä"}, {}),
    ("bivocalic", "de", "Bähö", {"vowels": "äö"}, {}),
    ("monoconsonantal", "de", "Mäßig", {"consonant": "m"}, {}),
    ("acrostic", "de", "Sonne\nsehr\ntanzt", {"target": "sst"}, {}),
    ("slenderizing", "de", "Die trae war gro.", {"deleted": "s"},
     {"source": "Die Straße war groß."}),
    ("univocalic", "fr", "Cœur", {"vowel": "o"}, {}),
]


def prefold(text: str, lang: str) -> str:
    pack = get_pack(lang)
    return "".join(pack.fold_diacritics(ch) if ch.isalpha() else ch for ch in text)


@pytest.mark.parametrize(("pid", "lang", "text", "letter_params", "text_params"), CASES)
def test_folding_the_text_agrees_with_folding_the_parameter(
    pid: str, lang: str, text: str, letter_params: dict[str, str], text_params: dict[str, str]
) -> None:
    folded_on = check(pid, text, lang=lang, **letter_params, **text_params)
    folded_off = check(
        pid,
        prefold(text, lang),
        lang=lang,
        fold_diacritics=False,
        **{key: prefold(value, lang) for key, value in letter_params.items()},
        **{key: prefold(value, lang) for key, value in text_params.items()},
    )
    assert folded_on.satisfied == folded_off.satisfied, (
        f"{pid} in {lang}: folding on gives {folded_on.satisfied}, "
        f"pre-folded with folding off gives {folded_off.satisfied}"
    )
```

Note the argument name is `pid`, not `procedure_id` — `tests/conftest.py` auto-parametrises
any test taking `procedure_id`, and combining that with `@pytest.mark.parametrize` is a
hard "duplicate parametrization" error rather than a warning.

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/test_fold_symmetry.py -q`
Expected: PASS, 6 passed. Every one of these fails on the branch point; they pass because
Tasks 1–5 landed, which is what makes this a regression guard rather than a red-green
cycle.

- [ ] **Step 3: Write the boundary test**

Create `tests/test_reading_boundary.py`:

```python
"""The rows defined on letters must never take a pronunciation judgement.

`univocalic` and its neighbours are `family: letter`, sourced to Bombaugh (1867)
and Word Ways, and declare `requires: [tokens, alphabet, fold_diacritics]` with
no `phonemes`. A glide-aware reading — `y w u i o` in English, `y i u ou` in
French — is measurably correct linguistically and measurably wrong here: it
makes each of the words below a univocalic, which no Word Ways editor accepts.

This is the test that fails if such a rule is ever wired into these rows. It
guards a boundary rather than an implementation, so it holds whether or not the
phonetic reading has been built yet. ADR 0035, D2.
"""

import yaml

from denckring import check
from denckring.core.registry import all_procedures

#: Each of these has exactly one *phonetic* vowel and more than one vowel
#: *letter*, so a glide-aware reading would call it univocalic.
GLIDE_WORDS = ["onion", "quick", "million", "oui", "huit", "nuit", "lui"]

#: The rows whose reading is orthographic, by their own `requires`.
ORTHOGRAPHIC = ("univocalic", "bivocalic", "monoconsonantal", "supervocalic")


def test_no_glide_word_is_a_univocalic() -> None:
    for word in GLIDE_WORDS:
        for lang in ("en", "fr"):
            assert not check("univocalic", word, lang=lang).satisfied, (
                f"{word!r} became a univocalic in {lang}: the phonetic reading has "
                f"leaked into a row that declares no phonemes"
            )


def test_the_orthographic_rows_declare_no_phonemes() -> None:
    """The premise of the test above, asserted rather than assumed — if a row
    ever gains `phonemes` this test says so before the one above starts lying.
    """
    for pid in ORTHOGRAPHIC:
        requires = all_procedures()[pid].meta.requires
        assert "phonemes" not in requires, (
            f"{pid} now declares phonemes; D2's licensing argument has to be revisited "
            f"before it may read letter_classes"
        )


def test_spoonerism_is_the_licensed_row() -> None:
    assert "phonemes" in all_procedures()["spoonerism"].meta.requires
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_reading_boundary.py -q`
Expected: PASS, 3 passed. It passes on first write — it is a regression guard, not a
red-green cycle, and it would have failed on any of the rejected designs.

Verify that claim by temporarily adding `"i"` to English's `vowel_inventory` removal set
and confirming `test_no_glide_word_is_a_univocalic` goes red, then revert.

- [ ] **Step 5: Write the ADR**

Create `docs/adr/0035-orthographic-and-phonetic-readings.md`, following the house
structure — a real problem, a decision, and consequences that admit costs. It records
three decisions:

- **D1** — `vowels()` split three ways: the character set (`word_ladder`), the inventory
  (`supervocalic`), the contextual roles (`spoonerism`).
- **D2** — a row's `requires` list licenses which reading of a letter it may take.
  Consequences must carry: French `monoconsonantal("yoyo")` keeps reporting
  `consonants: 0`; English and French answer differently for the same text; the glide rule
  measured correct in all three languages and flipped zero golden cases, and was still
  refused for the orthographic rows.
- **D4** — a single-letter parameter folding to several characters is refused by name.

Cite the measurements: `de vowels()` is 8 and folds to `aeiou`; `fr` is 21 and folds to
`aeiouy`; the glide rule scored 30/34; `onion`, `quick`, `million`, `oui`, `huit`, `lui`
and `nuit` become univocalics under it; `slenderizing` scored 0.412 against its own output.

- [ ] **Step 6: Update the changelog**

Add to the `### Fixed` section under `[Unreleased]` in `CHANGELOG.md`:

```markdown
- The diacritic fold applied to the text but not to the parameter compared against it, so
  `vowel="ä"`, `vowels="äö"` and a `ß` acrostic target were unsatisfiable in German, and
  `slenderizing`'s generated output failed its own checker under default parameters.
- `supervocalic` required every accented vowel letter its pack names — eight in German,
  twenty-one in French — against a published definition that says five. `vowel_inventory()`
  is the reading it wanted.
- `spoonerism`'s written onset guess split on flat vowel membership, so French `yoyo` had
  an empty onset and English `myth` was entirely onset.
```

Add to `### Added`:

```markdown
- `LanguagePack.vowel_inventory()` and `LanguagePack.letter_classes()`, splitting the
  three questions `vowels()` was answering at once (ADR 0035).
```

Check first that `[Unreleased]` has exactly one `### Fixed` section — a duplicate was
merged in `d8bc3ae` and a second one must not reappear.

- [ ] **Step 7: Run the whole gate one last time**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src tests packages/denckring-en-data/src \
  packages/denckring-de-data/src packages/denckring-de-wiktionary/src
uv run denckring eval --all && uv run denckring status
cd apps/explorer && uv run ruff check && uv run ruff format --check && uv run mypy --strict src tests && uv run pytest
```
Expected: library gate clean; `eval` `121 procedures · 495 passed · 0 failed`; `status`
`155 · 130 · 121 · 121 · 25` then `0 instruments catalogued`; explorer `344 passed`.

- [ ] **Step 8: Commit**

```bash
git add tests/test_fold_symmetry.py tests/test_reading_boundary.py \
        docs/adr/0035-orthographic-and-phonetic-readings.md CHANGELOG.md
git commit -m "docs: ADR 0035, and the test that keeps the two readings apart

A row's requires list licenses which reading of a letter it may take.
The glide rule measured correct in all three languages and flipped zero
golden cases, and is still refused for the rows declaring alphabet
alone — it would make onion, quick, million, oui, huit, lui and nuit
into univocalics.

The boundary test names those seven words, so the leak fails loudly
rather than quietly changing what a univocalic is.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

## Notes for the executor

**Two things this plan deliberately does not do.**

`slenderizing` stays in `PARAMETER_GATED`. Removing it needs the round-trip harness to
supply row-specific parameters, which `tests/test_round_trip.py` already calls out as its
own piece of work with its own review surface. Task 2 closes the gap the other way the
file already names — a row-level test plus a golden case in a second language — and adds
the structural guard so the shape cannot recur silently.

`kangaroo_word` is untouched. The sweep files it under Finding 1 and it belongs to
Finding 3, French elision, with `s_plus_7` and `n_plus_7`.

**The golden case counts are cumulative and each task states its own expected total:**
487 at the branch point, 489 after Task 2, 492 after Task 3, 493 after Task 4, 495 after
Task 5. If a count does not match, stop — a fixture was added twice or a case was lost.
