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


@register
class Chronogram(BaseProcedure[ChronogramParams]):
    """A phrase whose hidden numerals add up to a year."""

    id = "chronogram"

    @classmethod
    def params_model(cls) -> type[ChronogramParams]:
        return ChronogramParams

    def _check(self, text: str, pack: LanguagePack, params: ChronogramParams) -> Report:
        numerals = [
            (offset, ch)
            for offset, ch in letter_spans(text, pack, fold=params.fold_diacritics)
            if ch in VALUES
        ]
        total = sum(VALUES[ch] for _, ch in numerals)
        if total == params.year:
            return Report(
                procedure=self.id,
                satisfied=True,
                score=1.0,
                violations=[],
                metrics={"total": float(total), "numerals": float(len(numerals))},
            )
        score = (
            min(total, params.year) / max(total, params.year) if max(total, params.year) else 0.0
        )
        return Report(
            procedure=self.id,
            satisfied=False,
            score=score,
            violations=[
                Violation(
                    rule="wrong_total",
                    offset=None,
                    found=str(total),
                    expected=str(params.year),
                )
            ],
            metrics={"total": float(total), "numerals": float(len(numerals))},
        )
