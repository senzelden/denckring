"""Chronogram — the Roman-numeral letters sum to a date."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.counting import Counting
from denckring.core.fields import param
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans

#: Chronograms sum their numeral letters additively, in the order they fall,
#: rather than applying the subtractive rule of ordinary Roman numerals.
VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


class ChronogramParams(DiacriticParams):
    year: int = Field(
        description="The date the numeral letters must total.", json_schema_extra=param("task")
    )
    # A9: the bare numeral `MMXXVI` passes for 2026, though the row asks for a
    # phrase. Opt-in, so a 0.3.2 caller keeps every verdict.
    min_letters: int = Field(
        default=0,
        ge=0,
        description=(
            "Fewest letters, numerals or not, the phrase must have. 0 accepts a bare numeral."
        ),
        json_schema_extra=param("switch"),
    )
    # ADR 0064: Bombaugh (1890, p. 58) prints a line whose date comes from its capitals
    # alone; Hilton (1882, p. 9) calls that reading a "pretext". Opt-in, so the default
    # stays Hilton's and every 0.5.0 call keeps its verdict.
    capitals_only: bool = Field(
        default=False,
        # Phrased as an instruction, because `prompt_hint` appends it under the template
        # when set (ADR 0050), and the template defers to it ("Unless a line below...").
        description=(
            "Only numeral letters written as capitals count: write the date's numerals as "
            "capitals; lower-case ones add nothing. Hilton calls this reading a pretext; "
            "off, every numeral letter counts."
        ),
        json_schema_extra=param("switch"),
    )


@register
class Chronogram(BaseProcedure[ChronogramParams]):
    """A phrase whose hidden numerals add up to a year."""

    id = "chronogram"
    rules = ("too_short", "wrong_total")
    #: Promised: ADR 0060 D3. Every golden report carries both.
    promised_metrics: ClassVar[dict[str, str]] = {
        "total": (
            "The numeral letters' sum, every occurrence counted, or every capital one "
            "under `capitals_only` (Reading.counting)."
        ),
        "numerals": "How many numeral letters were counted.",
    }

    #: Built from `VALUES` itself, so the published table cannot differ from the one
    #: `_check` sums (ADR 0061 D4).
    counting: ClassVar[Counting | None] = Counting(
        values={letter.upper(): value for letter, value in VALUES.items()},
        combine="sum",
        subtractive=False,
        every_occurrence=True,
        case_sensitive=False,
        case_switch="capitals_only",
        folds="fold_diacritics",
        skipped=(
            "every character that is not a letter: digits, punctuation, spaces; and every "
            "letter that is not a numeral, among them German ä, ö, ü and ß, folded or not"
        ),
    )

    @classmethod
    def params_model(cls) -> type[ChronogramParams]:
        return ChronogramParams

    def _check(self, text: str, pack: LanguagePack, params: ChronogramParams) -> Report:
        letters = letter_spans(text, pack, fold=params.fold_diacritics)
        numerals = [(offset, ch) for offset, ch in letters if ch in VALUES]
        if params.capitals_only:
            # The case is read from the caller's text, not from `letters`, which are
            # lower-cased (and folded): `Ï` counts as I only because `text` has a capital
            # there. The offset is the base character's, so a decomposed capital works too.
            # A titlecase digraph (`ǅ`, category Lt) begins with a capital, so it counts.
            numerals = [
                (offset, ch)
                for offset, ch in numerals
                if text[offset].isupper() or text[offset].istitle()
            ]
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
