# Calculator word Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one catalogue row, `calculator_word` — a word a seven-segment display can write, entered as digits and read by turning the machine over, so `7353` is `ESEL`.

**Architecture:** A language-free display table and two pure functions in a new `core/calculator.py`, consumed by both the procedure and the explorer's stage scene so neither imports the other's internals. The checker takes a text plus a `digits` parameter and reports four violation kinds; the generator inverts it, partitioning a digit string into `words` segments and keeping the partitions whose every segment is a real word. Follows `chronogram` for the constant table and `word_ladder` for the constructive spine.

**Tech Stack:** Python 3.12, pydantic v2, pytest, hypothesis, mypy --strict, ruff, FastAPI + Jinja2 (explorer only).

**Spec:** `docs/superpowers/specs/2026-09-04-calculator-word-design.md`

## Global Constraints

- **The gate is four commands, plus two for anything touching a procedure.** `uv run pytest -q`, `uv run mypy --strict src tests`, `uv run ruff check .`, `uv run ruff format --check .`, then `uv run denckring eval --all` and `uv run denckring status`.
- **Expected counters after this plan:** `denckring status` reads `156 catalogued · 131 implementable · 122 implemented · 122 validated · 25 not mechanically checkable`, then `0 instruments catalogued`. `eval --all` reads `122 procedures · N passed · 0 failed` where N is 513 plus the golden cases added in Task 7.
- **`apps/explorer` has its own gate and it must be run from inside the app** after any catalogue change: `cd apps/explorer && uv run ruff check && uv run ruff format --check && uv run mypy --strict src tests && uv run pytest`. Expect `344 passed` before Task 8 and more after.
- **Commit trailer is `Assisted-by: Claude:claude-opus-5[1m]`.** Never `Co-Authored-By:`, never `Signed-off-by:`, never a `Claude-Session:` trailer — 291 of those were stripped from history for putting session URLs in the repository.
- **Stage files by name.** Never `git add -A`: `undefined/queneau-seams.png` is untracked and a 68KB blob of it is already in `main`'s history from one such command.
- **Do not push.** `origin/main` is pinned at `f0ffdcb` by decision until release. Commit freely.
- **`procedure_id` is a reserved test-argument name.** `tests/conftest.py` auto-parametrises any test taking it, over every registered procedure, and also writing `@pytest.mark.parametrize("procedure_id", ...)` is a hard duplicate-parametrization error. Name the argument `pid`.
- **Comments explain why, not what, and cite ADRs by number.** A comment that has become false is treated as a defect here, not a nit.
- **Every digit string in this plan was verified by decoding it, not by hand.** Four were wrong in the first draft — `blessé`'s and `Geheiß`'s digits, the two-word German example, and the partition order in `_produce`, which read a phrase backwards. Re-verify any digit string you add rather than trusting it: `uv run python -c "from denckring.core.calculator import from_digits, to_digits; print(from_digits('7353'), to_digits('Esel'))"`.
- **Prove every non-ASCII test red before believing it.** A test using ASCII input to verify a diacritic fix cannot fail for its own reason; three such tests shipped on one branch before review caught them.

---

### Task 1: The display table and its two functions

**Files:**
- Create: `src/denckring/core/calculator.py`
- Test: `tests/test_calculator_display.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `TO_DIGIT: dict[str, str]`, `FROM_DIGIT: dict[str, str]`, `ALPHABET: frozenset[str]`, `to_digits(word: str) -> str | None`, `from_digits(digits: str) -> str`. Tasks 2, 3 and 8 all import from here.

- [ ] **Step 1: Write the failing test**

```python
"""The seven-segment display, with no language in sight."""

from denckring.core.calculator import ALPHABET, FROM_DIGIT, from_digits, to_digits


def test_the_four_attested_words_decode() -> None:
    """Verified by decoding rather than by reading them off a web page.

    `illegible` is the sharpest: the form in circulation uses `9` for the `g`,
    and this row's own generator emits `6`. Both are correct (spec D4).
    """
    assert from_digits("07734") == "hello"
    assert from_digits("5318008") == "boobies"
    assert from_digits("53177187714") == "hillbillies"
    assert from_digits("378193771") == "illegible"
    assert from_digits("378163771") == "illegible"


def test_esel_is_7353() -> None:
    assert to_digits("Esel") == "7353"
    assert from_digits("7353") == "esel"


def test_a_word_outside_the_alphabet_has_no_digits() -> None:
    assert to_digits("cat") is None
    assert to_digits("blessé") is None


def test_g_is_emitted_as_six_and_accepted_as_either() -> None:
    """`6` and `9` both rotate onto G, so `apply` is not the inverse of `check`
    for a word containing one — a third of every corpus. Spec D4 fixes the
    emitted spelling at `6`, because the practice's own name encodes g from 6."""
    assert to_digits("igel") == "7361"
    assert from_digits("7361") == "igel"
    assert from_digits("7391") == "igel"


def test_two_is_not_a_letter() -> None:
    """`2` is rotationally symmetric on a seven-segment display, so the folk
    `2 -> Z` is a pun on the printed digit rather than a property of the
    machine. Spec D2 refuses it, and `2 -> R` with it."""
    assert "2" not in FROM_DIGIT
    assert from_digits("2") == ""
    assert to_digits("zebra") is None


def test_the_alphabet_is_the_eight_letters_beghilos_names() -> None:
    assert ALPHABET == frozenset("beghilos")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_calculator_display.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'denckring.core.calculator'`

- [ ] **Step 3: Write minimal implementation**

```python
"""The seven-segment display, as a table and two functions.

Separate from the procedure because the explorer's stage scene needs the same
table, and a scene must not import a procedure's internals.

The table is a module constant rather than a pack capability, and that is a
decision (ADR 0037, D1). `prisoners_constraint` reads its forbidden set from
`pack.letter_shapes` because ascenders and descenders genuinely differ by
orthography; seven-segment geometry does not — the display is the same machine
in Nuremberg, Boston and Lyon. `chronogram.VALUES` is the shape followed here.

Rotating a seven-segment glyph by 180 degrees swaps a<->d, b<->e, c<->f and
fixes g. Under that transform `2` maps onto itself and is therefore no letter at
all, which is why the folk `2 -> Z` is refused (ADR 0037, D2), and why `6` and
`9` both land on G (D4).
"""

from __future__ import annotations

#: Digit -> the letter it shows when the machine is turned over. `6` and `9`
#: both give G: they are the rotation mirror of one another, and the display has
#: no case, so a word containing G has more than one digit spelling.
FROM_DIGIT = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "h",
    "5": "s",
    "6": "g",
    "7": "l",
    "8": "b",
    "9": "g",
}

#: Letter -> the digit this project emits for it. `g` resolves to `6` rather
#: than `9` because the practice's own name — *beghilos* — encodes g from 6.
#: `check` accepts either; only the generator is bound by this direction.
TO_DIGIT = {
    "o": "0",
    "i": "1",
    "e": "3",
    "h": "4",
    "s": "5",
    "g": "6",
    "l": "7",
    "b": "8",
}

#: The eight letters a display can write. Named for the reader who arrives at
#: `set(TO_DIGIT)` and wonders whether the order matters; it does not.
ALPHABET = frozenset(TO_DIGIT)


def to_digits(word: str) -> str | None:
    """The digits that write `word`, or `None` if the display cannot.

    Reversed, because the machine is read upside down: the last letter is
    entered first. Case is dropped — a display has none.
    """
    lowered = word.lower()
    if not lowered or any(ch not in TO_DIGIT for ch in lowered):
        return None
    return "".join(TO_DIGIT[ch] for ch in reversed(lowered))


def from_digits(digits: str) -> str:
    """The letters `digits` shows, reversed. Digits with no letter are dropped.

    Dropping rather than raising keeps this total, so a caller can decode a
    partial entry — the stage scene types one digit at a time — without
    handling an exception per keystroke. The procedure's own validator is what
    refuses a `digits` parameter containing `2`.
    """
    return "".join(FROM_DIGIT[ch] for ch in reversed(digits) if ch in FROM_DIGIT)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_calculator_display.py -q`
Expected: PASS, 6 tests.

- [ ] **Step 5: Run the type and lint gate**

Run: `uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .`
Expected: all clean.

- [ ] **Step 6: Commit**

```bash
git add src/denckring/core/calculator.py tests/test_calculator_display.py
git commit -m "feat: the seven-segment display as a table and two functions

Language-free, so the stage scene and the procedure can share it without
either importing the other. A module constant rather than a pack capability
because seven-segment geometry does not vary by orthography the way
ascenders do — ADR 0037 D1, and chronogram.VALUES is the shape followed.

2 is rotationally symmetric under the 180-degree swap of a<->d, b<->e,
c<->f, so it is no letter and the folk 2->Z is refused. 6 and 9 are each
other's mirror and both give G, so to_digits emits 6 and from_digits
accepts either.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 2: The measurement test, pinning the figures the spec argues from

**Files:**
- Create: `tests/test_calculator_corpus.py`

**Interfaces:**
- Consumes: `denckring.core.calculator.ALPHABET` from Task 1.
- Produces: nothing imported elsewhere. This task exists so the spec's tables cannot drift silently, and so D5's premise — German has no `graded_words` — is asserted rather than remembered.

- [ ] **Step 1: Write the test**

```python
"""The corpus figures ADR 0037 argues from, pinned so they cannot drift.

Every decision in the spec rests on a measured yield, and a yield moves when a
data package is rebuilt. These assert the numbers rather than trusting the
prose, and the ranges are tight enough to notice a real change while tolerating
a lexicon revision of a word or two.
"""

import pytest

from denckring.core.calculator import ALPHABET
from denckring.lang import get_pack


def _corpus(lang: str) -> list[str]:
    """The enumerable word source for a pack: graded words where it has them,
    the noun list otherwise. Mirrors what `_produce` does — see ADR 0037 D5."""
    pack = get_pack(lang)
    if "lexicon.graded_words" in pack.capabilities:
        return list(pack.graded_words())
    return list(pack.nouns())


def test_german_has_no_graded_words_which_is_why_apply_floors_on_nouns() -> None:
    """The premise D5 rests on. SCOWL is vendored into `denckring-en-data`
    alone (ADR 0028); French got its own in chapter 6; German never has. If
    this ever becomes false, D5 is free to be simplified — and this test is
    how anyone finds out."""
    assert "lexicon.graded_words" not in get_pack("de").capabilities
    assert "lexicon.graded_words" in get_pack("en").capabilities
    assert "lexicon.graded_words" in get_pack("fr").capabilities
    assert "lexicon.nouns" in get_pack("de").capabilities


@pytest.mark.parametrize(
    ("lang", "expected"),
    [("en", 304), ("de", 216), ("fr", 207)],
)
def test_the_corpus_yield_is_what_the_adr_claims(lang: str, expected: int) -> None:
    """Measured 2026-09-04. A tolerance of five absorbs a lexicon revision
    without absorbing a change to the table or to the fold default."""
    found = sum(1 for word in _corpus(lang) if word and set(word.lower()) <= ALPHABET)
    assert abs(found - expected) <= 5, f"{lang}: {found}, ADR 0037 says {expected}"


def test_refusing_the_folk_table_is_what_costs_half_the_corpus() -> None:
    """D2's stated cost. If someone adds `2 -> Z` this fails, which is the
    point: the decision is meant to be reopened deliberately, not drifted into."""
    widened = ALPHABET | {"z", "r"}
    for lang, expected in (("en", 643), ("de", 652), ("fr", 631)):
        found = sum(1 for word in _corpus(lang) if word and set(word.lower()) <= widened)
        assert abs(found - expected) <= 15, f"{lang}: {found}, ADR 0037 says {expected}"
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/test_calculator_corpus.py -q`
Expected: PASS, 5 tests. If a yield is off by more than the tolerance, **do not widen the tolerance** — find out what moved and correct the ADR, since these numbers are its argument.

- [ ] **Step 3: Commit**

```bash
git add tests/test_calculator_corpus.py
git commit -m "test: pin the corpus figures ADR 0037 argues from

Every decision in the spec rests on a measured yield. These assert the
numbers instead of trusting the prose, including the premise D5 rests on —
German declares no lexicon.graded_words, so apply floors on nouns.

The folk-table figure is pinned too, so adding 2->Z fails here rather than
quietly doubling the corpus: D2 is meant to be reopened deliberately.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 3: The checker

**Files:**
- Create: `src/denckring/procedures/calculator_word.py`
- Modify: `src/denckring/procedures/__init__.py` (register the module the way its siblings are)
- Test: `tests/test_calculator_word.py`

**Interfaces:**
- Consumes: `to_digits`, `from_digits`, `ALPHABET` from Task 1.
- Produces: `CalculatorWordParams` with fields `digits: str`, `words: int = 1`, `require_words: bool = True`, `fold_diacritics: bool = False`; class `CalculatorWord` with `id = "calculator_word"`. Task 4 adds `_produce` to this same class; Task 8 imports nothing from it.

- [ ] **Step 1: Write the failing test**

```python
"""The calculator word checker."""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_esel_satisfies_7353_in_german() -> None:
    report = check("calculator_word", "Esel", lang="de", digits="7353")
    assert report.satisfied
    assert report.score == 1.0


def test_the_wrong_digits_are_a_violation_naming_both_readings() -> None:
    report = check("calculator_word", "Esel", lang="de", digits="7354")
    assert not report.satisfied
    rules = [v.rule for v in report.violations]
    assert "wrong_digits" in rules
    wrong = next(v for v in report.violations if v.rule == "wrong_digits")
    assert wrong.found == "7353"
    assert wrong.expected == "7354"


def test_a_letter_the_display_cannot_write_is_located() -> None:
    report = check("calculator_word", "cat", lang="en", digits="743")
    assert not report.satisfied
    bad = [v for v in report.violations if v.rule == "undisplayable_letter"]
    assert [v.found for v in bad] == ["c", "a", "t"]
    assert bad[0].offset == 0


def test_a_displayable_non_word_fails_on_the_lexicon() -> None:
    report = check("calculator_word", "hlose", lang="en", digits="35074")
    assert not report.satisfied
    assert "not_a_word" in [v.rule for v in report.violations]


def test_require_words_false_checks_the_mapping_alone() -> None:
    """The "combinations" reading: the display must be able to write it, and
    the lexicon is not consulted."""
    report = check(
        "calculator_word", "hlose", lang="en", digits="35074", require_words=False
    )
    assert report.satisfied


def test_the_word_count_is_checked() -> None:
    report = check("calculator_word", "Hose Esel", lang="de", digits="73533504", words=1)
    assert not report.satisfied
    assert "wrong_word_count" in [v.rule for v in report.violations]


def test_either_digit_spelling_of_g_is_accepted() -> None:
    """`6` and `9` both rotate onto G (ADR 0037 D4), so both spellings of a
    word containing one must satisfy the same text."""
    for digits in ("7361", "7391"):
        assert check("calculator_word", "Igel", lang="de", digits=digits).satisfied


def test_an_accented_word_is_not_a_calculator_word_by_default() -> None:
    """The row's fold default is FALSE, inverting every other row (ADR 0037
    D3): a calculator cannot write `blessé`, it writes `BLESSE`."""
    report = check("calculator_word", "blessé", lang="fr", digits="355378")
    assert not report.satisfied
    assert "undisplayable_letter" in [v.rule for v in report.violations]


def test_folding_can_be_asked_for_explicitly() -> None:
    """The lenient reading stays reachable; only the default changed."""
    report = check(
        "calculator_word", "blessé", lang="fr", digits="355378", fold_diacritics=True
    )
    assert report.satisfied


def test_the_german_sharp_s_is_undisplayable_by_default() -> None:
    """`Geheiß` shows as GEHEISS. Under folding it would be accepted, which is
    false about the machine — the other half of D3."""
    assert not check("calculator_word", "Geheiß", lang="de", digits="5513436").satisfied


def test_digits_containing_two_are_refused() -> None:
    """`2` maps to no letter (D2), so a `digits` value containing one cannot
    describe any text and is malformed input rather than a failed check."""
    with pytest.raises(InvalidParams):
        check("calculator_word", "Esel", lang="de", digits="7253")


def test_digits_must_be_digits() -> None:
    with pytest.raises(InvalidParams):
        check("calculator_word", "Esel", lang="de", digits="73a3")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_calculator_word.py -q`
Expected: FAIL — `UnknownProcedure: 'calculator_word'`.

- [ ] **Step 3: Write the implementation**

```python
"""Calculator word — a word a seven-segment display can write, read upside down.

`7353`, entered on a pocket calculator and turned over, is `ESEL`. The digits
are entered in reverse because the machine is read from the other end.

**This row's `fold_diacritics` defaults to `False`, and every other row in the
catalogue defaults to `True`.** That inversion is ADR 0037 D3 and is deliberate:
the display is the artefact, and a calculator cannot write `Geheiß` — it writes
`GEHEISS` — nor `blessé`. Under folding both would be accepted as calculator
words, which is false about the machine. It costs de 242 -> 216 and fr 356 ->
207, measured; the parameter stays, so the lenient "displayable up to accents"
reading remains reachable for a caller who wants it.

The table lives in `core/calculator.py` rather than here, because the explorer's
stage scene needs it too and a scene must not import a procedure's internals.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.calculator import FROM_DIGIT, to_digits
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import fold_letter, word_spans


class CalculatorWordParams(DiacriticParams):
    digits: str = Field(
        default="7353",
        description="The digits entered on the display, read upside down.",
    )
    words: int = Field(
        default=1,
        ge=1,
        description="How many words the digits must spell.",
    )
    require_words: bool = Field(
        default=True,
        description=(
            "Whether each word must be one the language knows. False checks the "
            "display mapping alone, admitting any letter combination it can write."
        ),
    )
    #: ADR 0037 D3. The default is inverted from every other row on purpose;
    #: the field is redeclared rather than left inherited so a reader of this
    #: model sees the value without going to `DiacriticParams` for it.
    fold_diacritics: bool = Field(
        default=False,
        description=(
            "Whether an accented letter counts as its base letter. False by "
            "default here alone: the display cannot write the accent."
        ),
    )

    @field_validator("digits")
    @classmethod
    def _displayable_digits(cls, value: str) -> str:
        if not value or not value.isdigit():
            raise ValueError("digits must be a non-empty string of digits")
        # `2` is rotationally symmetric on a seven-segment display and shows no
        # letter at all (ADR 0037 D2), so a `digits` value carrying one cannot
        # describe any text. Malformed input, not a failed check.
        unreadable = sorted({ch for ch in value if ch not in FROM_DIGIT})
        if unreadable:
            raise ValueError(
                f"digits {''.join(unreadable)} show no letter on a seven-segment display"
            )
        return value


@register
class CalculatorWord(BaseProcedure[CalculatorWordParams]):
    """A word spelled by turning a calculator over."""

    id = "calculator_word"

    @classmethod
    def params_model(cls) -> type[CalculatorWordParams]:
        return CalculatorWordParams

    def _check(self, text: str, pack: LanguagePack, params: CalculatorWordParams) -> Report:
        words = word_spans(text, pack)
        violations: list[Violation] = []

        if len(words) != params.words:
            violations.append(
                Violation(
                    rule="wrong_word_count",
                    offset=None,
                    found=str(len(words)),
                    expected=str(params.words),
                )
            )

        # Folded per-letter the way `letter_spans` folds text, so the parameter
        # side and the text side agree (ADR 0035). With the default `False` this
        # is the identity, and an accented letter stays undisplayable.
        readable: list[str] = []
        for offset, word in words:
            folded = "".join(
                fold_letter(ch, pack, fold=params.fold_diacritics) for ch in word
            )
            readable.append(folded)
            for index, ch in enumerate(folded):
                if ch.lower() not in FROM_DIGIT.values():
                    violations.append(
                        Violation(
                            rule="undisplayable_letter",
                            offset=offset + index,
                            found=ch,
                            expected="a letter a seven-segment display can write",
                        )
                    )

        spelled = "".join(to_digits(word) or "" for word in reversed(readable))
        if not violations or all(v.rule == "not_a_word" for v in violations):
            if spelled != params.digits and not _same_reading(spelled, params.digits):
                violations.append(
                    Violation(
                        rule="wrong_digits",
                        offset=None,
                        found=spelled,
                        expected=params.digits,
                    )
                )

        if params.require_words:
            for offset, word in words:
                # Membership is asked on the word as written, never on a folded
                # form: ADR 0036's `kangaroo_word` fix, where `is_word("ecole")`
                # is False and `is_word("école")` is True.
                if not pack.is_word(word):
                    violations.append(
                        Violation(
                            rule="not_a_word",
                            offset=offset,
                            found=word,
                            expected="a word the language knows",
                        )
                    )

        total = max(len(words), 1)
        return self._report(
            good=total - min(len(violations), total),
            total=total,
            violations=violations,
            metrics={"words": float(len(words)), "digits": float(len(params.digits))},
        )


def _same_reading(left: str, right: str) -> bool:
    """Whether two digit strings show the same letters.

    `6` and `9` both rotate onto G (ADR 0037 D4), so a word containing one has
    two spellings and the checker must accept both. Comparing the decoded
    letters rather than normalising the digits keeps the one place that knows
    about the ambiguity inside `core/calculator`.
    """
    from denckring.core.calculator import from_digits

    return len(left) == len(right) and from_digits(left) == from_digits(right)
```

Register it beside its siblings in `src/denckring/procedures/__init__.py`. Open that file, find how the existing modules are listed (an import list or `__all__`), and add `calculator_word` in the same style and in the same alphabetical position.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_calculator_word.py -q`
Expected: PASS, 12 tests. If `wrong_digits` fires alongside `undisplayable_letter` on the `cat` case, the guard around the comparison is wrong — a text with an unwritable letter has no digit reading to compare, and reporting both would name two faults for one cause.

- [ ] **Step 5: Prove the fold cases red against a folding default**

Temporarily change `fold_diacritics`'s default in `CalculatorWordParams` to `True`, run `uv run pytest tests/test_calculator_word.py -q`, and confirm `test_an_accented_word_is_not_a_calculator_word_by_default` and `test_the_german_sharp_s_is_undisplayable_by_default` **fail**. Then change it back and confirm they pass. A test using ASCII input cannot fail for its own reason, and this is how you know these two do not.

- [ ] **Step 6: Run the gate**

Run: `uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .`
Expected: all clean. `denckring status` will still read 155 catalogued — the row is registered but not catalogued until Task 5.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/procedures/calculator_word.py src/denckring/procedures/__init__.py tests/test_calculator_word.py
git commit -m "feat: the calculator word checker

check(text, digits) verifies that the text, mapped through the display and
reversed, is those digits — and separately that each word is real.
require_words=False is the combinations reading, where the mapping must hold
and the lexicon is not consulted.

fold_diacritics defaults to FALSE here and to True on every other row. ADR
0037 D3: the display is the artefact, and a calculator cannot write Geheiss
or blesse with their accents. Proved red by flipping the default.

A digits value containing 2 raises InvalidParams rather than failing the
check: 2 shows no letter, so such a value describes no text at all.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 4: The generator

**Files:**
- Modify: `src/denckring/procedures/calculator_word.py`
- Test: `tests/test_calculator_word.py` (append)

**Interfaces:**
- Consumes: `CalculatorWordParams`, `CalculatorWord` from Task 3.
- Produces: `CalculatorWordApplyParams(CalculatorWordParams, ApplyParams)`; `CalculatorWord` becomes a `ConstructiveProcedure[CalculatorWordParams, CalculatorWordApplyParams]`. Task 5's catalogue row declares `apply_requires: [lexicon.nouns]` to match.

- [ ] **Step 1: Write the failing test**

```python
def test_apply_decodes_the_digits_to_a_word() -> None:
    from denckring import apply

    assert apply("calculator_word", "7353", lang="de").lower() == "esel"


def test_produce_partitions_into_the_requested_number_of_words() -> None:
    from denckring import produce

    production = produce("calculator_word", "73533504", lang="de", words=2)
    for text in production.texts:
        assert len(text.split()) == 2
    assert production.texts


def test_a_partition_that_cannot_be_made_raises_rather_than_returning_junk() -> None:
    from denckring.core.errors import NoCandidateWord
    from denckring import produce

    with pytest.raises(NoCandidateWord):
        produce("calculator_word", "73533504", lang="de", words=1)


def test_what_the_generator_makes_satisfies_its_own_checker() -> None:
    """The project's thesis, on this row, in all three languages."""
    from denckring import apply, check

    for lang, digits in (("en", "07734"), ("de", "7353"), ("fr", "713705")):
        text = apply("calculator_word", digits, lang=lang)
        assert check("calculator_word", text, lang=lang, digits=digits).satisfied


def test_the_generator_emits_six_for_g_not_nine() -> None:
    """ADR 0037 D4, and the asymmetry it creates. The attested ILLEGIBLE is
    378193771; this generator's own spelling of the same word is 378163771.
    Both decode correctly, and a reader who assumes one canonical spelling
    will read the other as a bug."""
    from denckring import apply
    from denckring.core.calculator import to_digits

    assert to_digits("illegible") == "378163771"
    assert apply("calculator_word", "378193771", lang="en").lower() == "illegible"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_calculator_word.py -q`
Expected: FAIL — `calculator_word` has no `apply`.

- [ ] **Step 3: Write the implementation**

Change the class declaration and add the generator:

```python
from denckring.core.base import ApplyParams, ConstructiveProcedure, DiacriticParams
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import Candidate, Produced


class CalculatorWordApplyParams(CalculatorWordParams, ApplyParams):
    pass


@register
class CalculatorWord(ConstructiveProcedure[CalculatorWordParams, CalculatorWordApplyParams]):
    ...

    @classmethod
    def apply_params_model(cls) -> type[CalculatorWordApplyParams]:
        return CalculatorWordApplyParams

    def _produce(
        self, text: str, pack: LanguagePack, params: CalculatorWordApplyParams
    ) -> Produced:
        """Partition `text` — the digit string — into `words` segments that
        each decode to a real word.

        Decode first, then ask the lexicon. The alternative is to scan the word
        list for candidates of each length, which costs the size of the lexicon
        per segment; decoding costs the length of the digit string and asks
        `is_word` once per candidate. The digit string is short and the lexicon
        is not, so the direction matters.

        The corpus for ranking is `graded_words` where the pack has it and the
        noun list otherwise, which is ADR 0037 D5: German declares no
        `graded_words` at all, so a row demanding it could not generate in the
        language of this row's own example. `apply_requires` names
        `lexicon.nouns`, the floor every pack meets, and this method uses the
        better source where it exists rather than refusing.
        """
        digits = text.strip() or params.digits
        if not digits.isdigit():
            raise InvalidParams(self.id, "the text to apply must be a string of digits")

        grades = pack.graded_words() if "lexicon.graded_words" in pack.capabilities else {}
        found: list[tuple[int, str]] = []
        for parts in _partitions(digits, params.words):
            # Reversed: the machine is read from the other end, so the LAST
            # segment of the digit string is the FIRST word of the phrase.
            # Entering to_digits("esel") + to_digits("hose") and turning the
            # display over reads "hose esel", not "esel hose".
            words = [from_digits(part) for part in reversed(parts)]
            if any(not word or not pack.is_word(word) for word in words):
                continue
            rank = sum(grades.get(word, 50) for word in words)
            found.append((rank, " ".join(words)))

        if not found:
            raise NoCandidateWord(
                f"no {params.words}-word reading of {digits!r} is a word in {pack.lang!r}"
            )
        found.sort(key=lambda pair: (pair[0], pair[1]))
        limited = found[: params.max_results]
        return Produced(
            candidates=[
                Candidate(text=word, metrics={"rank": float(rank)}) for rank, word in limited
            ],
            truncated=len(found) > len(limited),
        )


def _partitions(digits: str, parts: int) -> list[list[str]]:
    """Every way of cutting `digits` into exactly `parts` non-empty runs.

    Written as an explicit walk rather than with `itertools.combinations` over
    cut points so the empty-segment case is impossible by construction: a
    segment of no digits decodes to the empty string, which `is_word` would be
    asked about and might even answer.
    """
    if parts == 1:
        return [[digits]] if digits else []
    out: list[list[str]] = []
    for cut in range(1, len(digits) - parts + 2):
        for rest in _partitions(digits[cut:], parts - 1):
            out.append([digits[:cut], *rest])
    return out
```

Add `from denckring.core.calculator import FROM_DIGIT, from_digits, to_digits` and `from denckring.core.errors import InvalidParams, NoCandidateWord` to the imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_calculator_word.py -q`
Expected: PASS, 17 tests.

- [ ] **Step 5: Run the round-trip net**

Run: `uv run pytest tests/test_round_trip.py -q`
Expected: PASS. If `test_the_named_coverage_gap_is_the_whole_coverage_gap` fails, a row became unreachable — find the cause; `PARAMETER_GATED` is not a knob. If this row needs gating because the harness cannot supply a `digits` value that decodes, add it **with the reason written down**, and note that ADR 0035's guard then requires a golden case in a second language, which Task 7 supplies.

- [ ] **Step 6: Commit**

```bash
git add src/denckring/procedures/calculator_word.py tests/test_calculator_word.py
git commit -m "feat: the calculator word generator

produce(digits, words=n) partitions the digit string into n segments and
keeps the partitions whose every segment decodes to a real word. Decode
first, then ask the lexicon: the digit string is short and the lexicon is
not.

The corpus is graded_words where a pack has it and the noun list otherwise
— ADR 0037 D5. German declares no graded_words, so a row demanding it could
not generate in the language of this row's own example. apply_requires
names lexicon.nouns, the floor every pack meets.

apply emits 6 for G where the attested forms often use 9, so apply is not
the byte-for-byte inverse of check for a third of every corpus. Pinned by a
test on ILLEGIBLE, which is 378193771 in circulation and 378163771 here.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 5: The catalogue row

**Files:**
- Modify: `src/denckring/data/catalogue.yaml`

**Interfaces:**
- Consumes: the registered `calculator_word` from Tasks 3 and 4.
- Produces: the row that makes `denckring status` read 156.

- [ ] **Step 1: Add the row**

Insert in the `letter` family, keeping the file's existing ordering convention (find where `chronogram` sits and follow the surrounding pattern):

```yaml
  - id: calculator_word
    names: { en: Calculator word, de: Taschenrechnerwort, fr: Mot de calculatrice }
    definitions:
      en: >-
        A word a seven-segment display can write, entered as digits and read by
        turning the machine over: 7353 is ESEL. The checker compares the letters
        the display shows, so an accented letter is not displayable unless
        fold_diacritics is asked for.
      de: >-
        Ein Wort, das eine Siebensegmentanzeige schreiben kann: als Ziffern
        eingegeben und auf dem Kopf gelesen, ergibt 7353 ESEL. Verglichen wird,
        was die Anzeige zeigt — ein Buchstabe mit Akzent oder ein ß gilt
        deshalb nicht als darstellbar.
      fr: >-
        Un mot qu'un afficheur à sept segments peut écrire, saisi en chiffres et
        lu en retournant la machine : 7353 donne ESEL. Le vérificateur compare
        ce que l'afficheur montre, si bien qu'une lettre accentuée n'est pas
        affichable.
    source: >-
      Michael Quinion, World Wide Words, "Beghilos" (2009); the practice dates to
      pocket LED calculators of the 1970s
    family: letter
    attribution: reference
    checkability: self
    attested: codified
    kind: both
    languages: [en, de, fr]
    requires: [tokens, lexicon.words, fold_diacritics]
    apply_requires: [lexicon.nouns]
    deterministic: true
    prompt_hints:
      en: >-
        Write a word using only the letters B, E, G, H, I, L, O and S, then give
        the digits that spell it upside down on a calculator.
      de: >-
        Schreibe ein Wort nur aus den Buchstaben B, E, G, H, I, L, O und S und
        gib die Ziffern an, die es auf dem Kopf ergeben.
      fr: >-
        Écris un mot n'utilisant que les lettres B, E, G, H, I, L, O et S, puis
        donne les chiffres qui l'affichent à l'envers.
    notes: >-
      The digit table is a module constant in `core/calculator.py`, not a pack
      capability: seven-segment geometry does not vary by orthography the way the
      ascenders `prisoners_constraint` reads from `letter_shapes` do (ADR 0037
      D1). `6` and `9` both rotate onto G, so a word containing one has two digit
      spellings; `check` accepts either and `apply` emits `6` (D4). `apply` draws
      from `lexicon.graded_words` where a pack declares it and from the noun list
      otherwise, so its corpus differs by language — German declares no graded
      words at all (ADR 0028), which is why `apply_requires` names the noun list
      rather than the richer source (D5).
```

- [ ] **Step 2: Verify the counters moved**

Run: `uv run denckring status`
Expected: `156 catalogued · 131 implementable · 122 implemented · 122 validated · 25 not mechanically checkable`, then `0 instruments catalogued`.

- [ ] **Step 3: Run the catalogue's own tests**

Run: `uv run pytest tests/test_catalogue_corrections.py tests/test_disclosure.py tests/test_provenance.py -q` (skip any of those that do not exist; run `uv run pytest -q -k catalogue` as well).
Expected: PASS. The provenance test enforces that `author-stated` cites a source with a year — this row is `reference`, so that rule does not bind it, but the source string must still be real. It is: Quinion 2009 is verified.

- [ ] **Step 4: Commit**

```bash
git add src/denckring/data/catalogue.yaml
git commit -m "feat: catalogue the calculator word

155 -> 156 rows, and the first row whose constraint is a property of a
machine rather than of an orthography or a lexicon.

Provenance is what was verified and nothing more: Quinion (2009) and the
1970s dating. A Word Ways article, 'The Word Calculator', exists in Butler's
archive and returned 403, so it is not cited — the rule that blocks the
Leibniz item in the backlog.

Definitions in all three languages state what the checker actually compares,
following iambic_pentameter rather than the six rows fixed on 2026-09-04.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 6: ADR 0037

**Files:**
- Create: `docs/adr/0037-the-calculator-word.md`

- [ ] **Step 1: Write the ADR**

Follow `docs/adr/0015-lexicon-capabilities.md` for tone: state a real problem, the decision, and consequences that **admit costs** rather than advertising benefits. Record D2 (the refused folk table), D3 (the inverted fold default) and D4 (G's two spellings) as the decisions, with D1, D5, D6 and D7 as consequences. Every figure comes from the spec, which measured them:

- Corpus under BEGHILOS: en 304, de 216, fr 207. Under the folk table: en 643, de 652, fr 631.
- Folding gains de 216 -> 242 and fr 207 -> 356, and every word it gains is one the machine cannot write.
- G appears in 108 of 304 English calculator words, 100 of 216 German, 58 of 207 French.
- German declares no `lexicon.graded_words`.

State plainly in Consequences that D2 forgoes roughly half the reachable corpus in every language, that D3 leaves one row in 156 whose fold default reads backwards to anyone scanning the catalogue, and that D4 means `apply` is not the inverse of `check` for about a third of every corpus.

- [ ] **Step 2: Check the ADR is reachable**

Run: `uv run pytest tests/test_published_docs.py -q` and `uv run mkdocs build --strict`
Expected: PASS and exit 0. `docs/adr/` is published, so a new file must not break the nav.

- [ ] **Step 3: Commit**

```bash
git add docs/adr/0037-the-calculator-word.md
git commit -m "docs: ADR 0037, the calculator word

Records the three decisions a reader will otherwise take for defects: the
refused folk table (2 is rotationally symmetric, so 2->Z is a pun and
refusing it costs about half the corpus in every language), the fold
default inverted for this row alone, and G's two digit spellings.

Consequences admit the costs rather than advertising the benefits, per
ADR 0015's example.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 7: Golden cases in all three languages

**Files:**
- Create: `src/denckring/eval/fixtures/golden/calculator_word.yaml`

**Interfaces:**
- Consumes: the catalogued row from Task 5.
- Produces: the cases `denckring eval --all` counts.

- [ ] **Step 1: Write the fixture**

```yaml
procedure: calculator_word
lang: en
cases:
  - name: hello
    source: >-
      attested; Michael Quinion, World Wide Words, "Beghilos" (2009). Verified by
      decoding rather than by transcription.
    text: hello
    params: { digits: "07734" }
    satisfied: true
  - name: illegible-with-nine-for-g
    source: >-
      attested; the form in circulation uses 9 for the g, where this row's
      generator emits 6. Both decode correctly — ADR 0037 D4.
    text: illegible
    params: { digits: "378193771" }
    satisfied: true
  - name: illegible-with-six-for-g
    source: constructed; the same word in the generator's own spelling
    text: illegible
    params: { digits: "378163771" }
    satisfied: true
  - name: undisplayable-letter
    source: constructed counterexample; c, a and t are not on the display
    text: cat
    params: { digits: "743" }
    satisfied: false
  - name: displayable-but-not-a-word
    source: constructed counterexample; the display can write it, English cannot
    text: hlose
    params: { digits: "35074" }
    satisfied: false
  - name: combinations-mode-admits-a-non-word
    source: constructed; require_words=false checks the mapping alone
    text: hlose
    params: { digits: "35074", require_words: false }
    satisfied: true

  - name: esel
    lang: de
    source: >-
      traditional German schoolyard example; the canonical demonstration of the
      practice in German
    text: Esel
    params: { digits: "7353" }
    satisfied: true
  - name: igel-either-spelling-of-g
    lang: de
    source: constructed; 6 and 9 both rotate onto G — ADR 0037 D4
    text: Igel
    params: { digits: "7391" }
    satisfied: true
  - name: sharp-s-is-not-displayable
    lang: de
    source: >-
      constructed counterexample; the display shows GEHEISS where German spells
      Geheiß, so this is not a calculator word under the row's default — ADR 0037 D3
    text: Geheiß
    params: { digits: "5513436" }
    satisfied: false
  - name: wrong-digits
    lang: de
    source: constructed counterexample; Esel is 7353, not 7354
    text: Esel
    params: { digits: "7354" }
    satisfied: false

  - name: soleil
    lang: fr
    source: constructed example; verified by decoding, 713705 reads SOLEIL
    text: soleil
    params: { digits: "713705" }
    satisfied: true
  - name: accented-word-is-not-displayable
    lang: fr
    source: >-
      constructed counterexample; the display shows BLESSE where French spells
      blessé — ADR 0037 D3, and the row's fold default is false
    text: blessé
    params: { digits: "355378" }
    satisfied: false
  - name: accented-word-under-explicit-folding
    lang: fr
    source: >-
      constructed; the lenient reading stays reachable, only the default changed
    text: blessé
    params: { digits: "355378", fold_diacritics: true }
    satisfied: true
```

- [ ] **Step 2: Verify each digit string by decoding, not by reading**

Run:

```bash
uv run python -c "
from denckring.core.calculator import from_digits, to_digits
for w, d in [('hello','07734'),('illegible','378193771'),('cat','743'),('hlose','35074'),
             ('esel','7353'),('igel','7391'),('soleil','713705')]:
    print(f'{w:11} {d:11} decodes to {from_digits(d)!r}  emits {to_digits(w)}')
"
```

Expected: every `decodes to` matches the word. **If one does not, fix the fixture, not the code** — a hand-computed digit string is exactly the kind of plausible value that reaches a maintainer unchecked. The `soleil` entry in an early draft of the spec was `7137105`, which decodes to `soileil`.

- [ ] **Step 3: Check the negatives fail for their own reason**

Run:

```bash
uv run python -c "
from denckring import check
for text, params, expect in [
    ('cat', {'digits':'743'}, 'undisplayable_letter'),
    ('hlose', {'digits':'35074'}, 'not_a_word'),
]:
    r = check('calculator_word', text, lang='en', **params)
    print(text, [v.rule for v in r.violations], 'want', expect)
"
```

Expected: each violation list contains the rule the case name claims. Per the chapter 6 trap, a verify-first loop that checks only `satisfied` will accept a case that fails for the wrong rule.

- [ ] **Step 4: Run eval**

Run: `uv run denckring eval --all`
Expected: `122 procedures · 526 passed · 0 failed` (513 + 13 new cases). If the count differs, count the cases in the fixture rather than adjusting the expectation.

- [ ] **Step 5: Commit**

```bash
git add src/denckring/eval/fixtures/golden/calculator_word.yaml
git commit -m "test: golden cases for the calculator word in all three languages

Thirteen cases. Two are attested and were verified by decoding rather than
transcription — the ILLEGIBLE pair pins ADR 0037 D4 from both sides, since
the circulating form uses 9 for the g and this generator emits 6.

The German sharp-s and French accented cases are the fold default (D3) and
use genuinely non-ASCII input, so they can fail for their own reason. The
negatives were checked against their violation lists, not just against
satisfied — the chapter 6 trap.

ADR 0035's guard requires a fold_diacritics row to carry a golden case in a
second language; this carries them in two.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 8: The stage scene

**Files:**
- Modify: `apps/explorer/src/explorer/stage.py`
- Modify: `apps/explorer/src/explorer/app.py`
- Create: `apps/explorer/src/explorer/templates/stage_calculator_word.html`
- Create: `apps/explorer/src/explorer/templates/_stage_display.html`
- Test: `apps/explorer/tests/test_stage_calculator_word.py`

**Interfaces:**
- Consumes: `denckring.core.calculator.from_digits`, `to_digits`; the catalogued row.
- Produces: `stage.CALCULATOR_WORD_DEFAULT` and `stage.calculator_word(digits, lang)`; a ninth entry in `stage.SCENES` with `slug="calculator_word"`.

- [ ] **Step 1: Write the failing test**

```python
"""The calculator word scene."""

from explorer import stage


def test_the_scene_is_registered() -> None:
    scene = stage.scene("calculator_word")
    assert scene.procedure_id == "calculator_word"
    assert scene.title


def test_the_default_reading_is_a_word_and_a_verdict() -> None:
    reading = stage.calculator_word(stage.CALCULATOR_WORD_DEFAULT, "de")
    assert reading.word.lower() == "esel"
    assert reading.problem is None


def test_a_digit_string_that_spells_nothing_reports_a_problem_not_a_crash() -> None:
    reading = stage.calculator_word("2222", "de")
    assert reading.problem is not None


def test_the_page_renders(client) -> None:  # noqa: ANN001
    response = client.get("/stage/calculator_word")
    assert response.status_code == 200
```

Match the existing app tests' fixture style — read `apps/explorer/tests/` for how `client` is provided and follow it exactly rather than inventing a fixture.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/explorer && uv run pytest tests/test_stage_calculator_word.py -q`
Expected: FAIL — `KeyError: 'calculator_word'`.

- [ ] **Step 3: Implement the scene preparation**

In `stage.py`, add a frozen dataclass `CalculatorReading` carrying `digits: str`, `word: str`, `problem: str | None`, and a `calculator_word(digits, lang)` function that decodes with `from_digits`, asks `pack.is_word`, and returns a problem string rather than raising — the same shape `word_ladder` uses, and for the same reason: a scene sits beside a verdict and a bad entry should not take the page down. Add the ninth `Scene` to `SCENES`:

```python
    Scene(
        slug="calculator_word",
        title="Taschenrechnerwort",
        procedure_id="calculator_word",
        caption="Type the digits, turn the machine over: 7353 is ESEL.",
    ),
```

In `app.py`, add a `GET /stage/calculator_word` route and a `POST /stage/calculator_word/act` route following `stage_word_ladder` and `stage_word_ladder_act` exactly — prepare in `stage.py`, check independently with `denckring_check`, render the partial from the POST.

The template shows a seven-segment display. Render each digit as an SVG with seven `<polygon>` segments, and rotate the whole display 180 degrees under a CSS class the button toggles, so the flip is the machine turning over rather than a text substitution.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/explorer && uv run pytest tests/test_stage_calculator_word.py -q`
Expected: PASS, 4 tests.

- [ ] **Step 5: Run the explorer's whole gate**

Run: `cd apps/explorer && uv run ruff check && uv run ruff format --check && uv run mypy --strict src tests && uv run pytest`
Expected: all clean, `348 passed`. If a test that pins a catalogued count went red, it is reporting the library's new row as a fault in the app — fix it to assert against the line the board computes, as was done on 2026-08-31.

- [ ] **Step 6: Commit**

```bash
git add apps/explorer/src/explorer/stage.py apps/explorer/src/explorer/app.py apps/explorer/src/explorer/templates/stage_calculator_word.html apps/explorer/src/explorer/templates/_stage_display.html apps/explorer/tests/test_stage_calculator_word.py
git commit -m "feat: the calculator word joins the stage

Ninth scene. Type the digits, turn the machine over. The display is seven
real segments per digit rotated 180 degrees, so the flip is the machine
turning rather than a text substitution.

The scene reads core/calculator.py directly, which is why that table is not
inside the procedure module: a scene must not import a procedure's
internals.

Assisted-by: Claude:claude-opus-5[1m]"
```

---

### Task 9: Close out

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `CLAUDE.md` (untracked; edit, do not commit)

- [ ] **Step 1: Add the changelog entry** under `[Unreleased]`, in the existing style. Check there is exactly one `### Added` section — the release rehearsal found two `### Fixed` sections once.

- [ ] **Step 2: Run the whole gate one final time**

```bash
uv run pytest -q
uv run mypy --strict src tests
uv run ruff check .
uv run ruff format --check .
uv run denckring eval --all      # expect 122 procedures · 526 passed · 0 failed
uv run denckring status          # expect 156 · 131 · 122 · 122 · 25, then 0 instruments
cd apps/explorer && uv run ruff check && uv run ruff format --check \
  && uv run mypy --strict src tests && uv run pytest    # expect 348 passed
```

- [ ] **Step 3: Type-check the workspace packages**, which the four-command gate does not cover and CI does:

```bash
uv run mypy --strict src tests packages/denckring-en-data/src \
  packages/denckring-de-data/src packages/denckring-de-wiktionary/src
```

- [ ] **Step 4: Update `CLAUDE.md`** — move `calculator_word` from "specced, not implemented" to done, with the counters and the three decisions a reader will otherwise take for defects. Do not commit it; it is excluded from git via `.git/info/exclude`.

- [ ] **Step 5: Commit the changelog**

```bash
git add CHANGELOG.md
git commit -m "docs: changelog for the calculator word

Assisted-by: Claude:claude-opus-5[1m]"
```
