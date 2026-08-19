"""Limerick — Five lines rhyming AABBA."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class LimerickParams(RhymeParams):
    pass


@register
class Limerick(BaseProcedure[LimerickParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "limerick"

    @classmethod
    def params_model(cls) -> type[LimerickParams]:
        return LimerickParams

    def _check(self, text: str, pack: LanguagePack, params: LimerickParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme="AABBA",
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
