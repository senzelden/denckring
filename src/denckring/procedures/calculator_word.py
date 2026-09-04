"""Calculator word — a word a seven-segment display can write, read upside down.

`7353`, entered on a pocket calculator and turned over, is `ESEL`. The digits go
in backwards because the machine is read from the other end.

**This row's `fold_diacritics` defaults to `False`, where every other row in the
catalogue defaults to `True`.** That inversion is ADR 0037 D3 and is the point of
the row rather than an oversight: the display is the artefact, and a calculator
cannot write `Geheiß` — it writes `GEHEISS` — nor `blessé`. Under folding both
would count as calculator words, which is false about the machine. It costs
de 242 -> 216 and fr 356 -> 207, measured. The parameter stays, so the lenient
"displayable up to accents" reading remains reachable for a caller who wants it.

The digit table lives in `core/calculator.py`, not here, because the explorer's
stage scene needs the same table and a scene must not import a procedure's
internals.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.calculator import ALPHABET, FROM_DIGIT, from_digits, to_digits
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import fold_letter, word_spans


class CalculatorWordParams(DiacriticParams):
    digits: str = Field(
        default="7353",
        description="The digits entered on the display, read by turning it over.",
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
    #: Redeclared rather than inherited so a reader of this model sees the value
    #: without going to `DiacriticParams` for it — this is the one row in the
    #: catalogue where it is `False`, and a reader who assumes the house default
    #: will misread every verdict. ADR 0037 D3.
    fold_diacritics: bool = Field(
        default=False,
        description=(
            "Whether an accented letter counts as its base letter. False by "
            "default on this row alone: the display cannot write the accent."
        ),
    )

    @field_validator("digits")
    @classmethod
    def _readable_digits(cls, value: str) -> str:
        if not value or not value.isdigit():
            raise ValueError("digits must be a non-empty string of digits")
        # `2` is rotationally symmetric on a seven-segment display and shows no
        # letter at all (ADR 0037 D2), so a `digits` value carrying one cannot
        # describe any text. That is malformed input, not a failed check.
        unreadable = sorted({ch for ch in value if ch not in FROM_DIGIT})
        if unreadable:
            raise ValueError(
                f"the digit(s) {''.join(unreadable)} show no letter on a seven-segment display"
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
        faulty: set[int] = set()
        # A fault of the whole text rather than of one word — the word count and
        # the digit reading are both properties of the entry as a whole. Tracked
        # separately from `faulty` because marking "every word" marks nothing
        # when there are no words: an empty text scored 1.0 while carrying two
        # violations, which is vacuous satisfaction of exactly the kind ADR 0035
        # fixed in `lipogram`.
        text_fault = False

        if len(words) != params.words:
            text_fault = True
            violations.append(
                Violation(
                    rule="wrong_word_count",
                    offset=None,
                    found=str(len(words)),
                    expected=str(params.words),
                )
            )

        shown: list[str] = []
        undisplayable = False
        for position, (offset, word) in enumerate(words):
            # Offsets come from the *source* characters, and folding is applied
            # one character at a time, because a fold can be multi-character
            # (`ß` gives `ss`) and folding the word first would drift every
            # offset after it.
            letters = ""
            for index, ch in enumerate(word):
                folded = fold_letter(ch, pack, fold=params.fold_diacritics)
                letters += folded
                if not folded or any(c not in ALPHABET for c in folded):
                    undisplayable = True
                    faulty.add(position)
                    violations.append(
                        Violation(
                            rule="undisplayable_letter",
                            offset=offset + index,
                            found=ch,
                            expected="a letter a seven-segment display can write",
                        )
                    )
            shown.append(letters)

        # Only when every letter is writable: a text the display cannot write has
        # no digit reading, so reporting `wrong_digits` as well would name two
        # faults for one fact and send the caller to fix the wrong one first.
        if not undisplayable:
            # Reversed, because the machine is read from the other end: the last
            # word's digits are entered first. `Hose Esel` is 7353 then 3504.
            spelled = "".join(to_digits(word) or "" for word in reversed(shown))
            if not _same_reading(spelled, params.digits):
                text_fault = True
                violations.append(
                    Violation(
                        rule="wrong_digits",
                        offset=None,
                        found=spelled,
                        expected=params.digits,
                    )
                )

        if params.require_words:
            for position, (offset, word) in enumerate(words):
                # Membership is asked on the word as written, never on a folded
                # form: ADR 0036's `kangaroo_word` fix, where `is_word("ecole")`
                # is False and `is_word("école")` is True.
                if not pack.is_word(word):
                    faulty.add(position)
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
            good=0 if text_fault else total - len(faulty),
            total=total,
            violations=violations,
            metrics={"words": float(len(words)), "digits": float(len(params.digits))},
        )


def _same_reading(left: str, right: str) -> bool:
    """Whether two digit strings show the same letters.

    `6` and `9` both rotate onto G (ADR 0037 D4), so a word containing one has
    two digit spellings and the checker must accept either. Comparing the
    decoded letters rather than normalising the digits keeps the one place that
    knows about the ambiguity inside `core/calculator`.
    """
    return len(left) == len(right) and from_digits(left) == from_digits(right)
