"""Chronogram — the Roman-numeral letters sum to a date."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans

#: Chronograms sum their numeral letters additively, in the order they fall,
#: rather than applying the subtractive rule of ordinary Roman numerals.
VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


class ChronogramParams(DiacriticParams):
    year: int = Field(description="The date the numeral letters must total.")
    # A9: the bare numeral `MMXXVI` passes for 2026, though the row asks for a
    # phrase. Opt-in, so a 0.3.2 caller keeps every verdict.
    min_letters: int = Field(
        default=0,
        ge=0,
        description=(
            "Fewest letters, numerals or not, the phrase must have. 0 accepts a bare numeral."
        ),
    )


@register
class Chronogram(BaseProcedure[ChronogramParams]):
    """A phrase whose hidden numerals add up to a year."""

    id = "chronogram"

    @classmethod
    def params_model(cls) -> type[ChronogramParams]:
        return ChronogramParams

    def _check(self, text: str, pack: LanguagePack, params: ChronogramParams) -> Report:
        letters = letter_spans(text, pack, fold=params.fold_diacritics)
        numerals = [(offset, ch) for offset, ch in letters if ch in VALUES]
        total = sum(VALUES[ch] for _, ch in numerals)
        metrics = {"total": float(total), "numerals": float(len(numerals))}
        violations: list[Violation] = []
        score = 1.0
        if total != params.year:
            score = (
                min(total, params.year) / max(total, params.year)
                if max(total, params.year)
                else 0.0
            )
            violations.append(
                Violation(
                    rule="wrong_total",
                    offset=None,
                    found=str(total),
                    expected=str(params.year),
                )
            )
        if len(letters) < params.min_letters:
            # Below 1 by construction, so a short phrase never scores as satisfied.
            score = min(score, len(letters) / params.min_letters)
            violations.append(
                Violation(
                    rule="too_short",
                    offset=None,
                    found=f"{len(letters)} letters",
                    expected=f"at least {params.min_letters} letters",
                )
            )
        return Report(
            procedure=self.id,
            satisfied=not violations,
            score=score,
            violations=violations,
            metrics=metrics,
        )
