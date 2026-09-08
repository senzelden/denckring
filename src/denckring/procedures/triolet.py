"""Triolet — Eight lines on two rhymes with two refrains."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class TrioletParams(RhymeParams):
    pass


@register
class Triolet(BaseProcedure[TrioletParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "triolet"

    @classmethod
    def params_model(cls) -> type[TrioletParams]:
        return TrioletParams

    def _check(self, text: str, pack: LanguagePack, params: TrioletParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme="ABAAABAB",
            allow_identical=True,  # the refrains are the same line repeated
            refrains=[(0, 3), (0, 6), (1, 7)],
        )

        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            evidence=list(result.evidence),
            metrics={
                "checks": float(result.total),
                "estimated_words": float(result.estimated),
            },
        )
