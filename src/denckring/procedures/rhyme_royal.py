"""Rhyme royal — Seven lines of iambic pentameter rhyming ABABBCC."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class RhymeRoyalParams(RhymeParams):
    pass


@register
class RhymeRoyal(BaseProcedure[RhymeRoyalParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "rhyme_royal"

    @classmethod
    def params_model(cls) -> type[RhymeRoyalParams]:
        return RhymeRoyalParams

    def _check(self, text: str, pack: LanguagePack, params: RhymeRoyalParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme="ABABBCC",
            metre="01" * 5,
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
