"""Trochaic tetrameter — Four trochaic feet to the line."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class TrochaicTetrameterParams(BaseModel):
    pass


@register
class TrochaicTetrameter(BaseProcedure[TrochaicTetrameterParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "trochaic_tetrameter"

    @classmethod
    def params_model(cls) -> type[TrochaicTetrameterParams]:
        return TrochaicTetrameterParams

    def _check(self, text: str, pack: LanguagePack, params: TrochaicTetrameterParams) -> Report:
        result = form_report(
            text,
            pack,
            metre="10" * 4,
        )

        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={
                "checks": float(result.total),
                "estimated_words": float(result.estimated),
            },
        )
