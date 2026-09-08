"""Sonnet — fourteen lines in a fixed metre and rhyme scheme.

Generic where `petrarchan_sonnet` and `shakespearean_sonnet` are specific: those
hard-code their scheme, this one is told it. What it adds is the line count, which
is the one property every sonnet shares.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.rhyme_scheme import form_report

LINES = 14


class SonnetParams(RhymeParams):
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
        result = form_report(
            text,
            pack,
            scheme=params.scheme,
            metre=params.metre,
            lines=LINES,
        )
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            evidence=list(result.evidence),
            metrics={
                "lines": float(len(line_spans(text))),
                "estimated_words": float(result.estimated),
            },
        )
