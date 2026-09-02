"""Acrostic — the initial letters of the units spell a target."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import fold_letter, letter_spans, line_spans, word_spans


class AcrosticParams(DiacriticParams):
    target: str = Field(description="The word or phrase the unit letters must spell.")
    unit: Literal["line", "word"] = Field(default="line", description="What carries a letter.")

    @field_validator("target")
    @classmethod
    def _at_least_one_letter(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("target must contain at least one letter")
        return value


@register
class Acrostic(BaseProcedure[AcrosticParams]):
    """Carroll's form: read the initials downward and the name appears.

    Satisfaction requires the unit count to equal the target length exactly —
    extra lines would spell something longer than the target.
    """

    id = "acrostic"

    #: Which letter of each unit carries the target. Telestich uses -1.
    letter_index: ClassVar[int] = 0

    @classmethod
    def params_model(cls) -> type[AcrosticParams]:
        return AcrosticParams

    def _units(self, text: str, pack: LanguagePack, unit: str) -> list[tuple[int, str]]:
        return line_spans(text) if unit == "line" else word_spans(text, pack)

    def _check(self, text: str, pack: LanguagePack, params: AcrosticParams) -> Report:
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
        actual: list[tuple[int, str]] = []
        for offset, unit_text in self._units(text, pack, params.unit):
            letters = letter_spans(unit_text, pack, fold=params.fold_diacritics)
            if letters:
                local_offset, letter = letters[self.letter_index]
                actual.append((offset + local_offset, letter))

        violations: list[Violation] = []
        matches = 0
        for index, want in enumerate(expected):
            if index >= len(actual):
                violations.append(
                    Violation(rule="missing_unit", offset=None, found="", expected=want)
                )
                continue
            offset, got = actual[index]
            if got == want:
                matches += 1
            else:
                violations.append(
                    Violation(rule="wrong_letter", offset=offset, found=got, expected=want)
                )
        violations += [
            Violation(rule="extra_unit", offset=offset, found=got, expected="")
            for offset, got in actual[len(expected) :]
        ]

        return self._report(
            good=matches,
            total=max(len(expected), len(actual)),
            violations=violations,
            metrics={
                "target_length": float(len(expected)),
                "units": float(len(actual)),
                "matches": float(matches),
            },
        )
