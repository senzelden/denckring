"""Villanelle — Nineteen lines, two rhymes, two alternating refrains."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class VillanelleParams(RhymeParams):
    pass


@register
class Villanelle(BaseProcedure[VillanelleParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "villanelle"

    @classmethod
    def params_model(cls) -> type[VillanelleParams]:
        return VillanelleParams

    def _check(self, text: str, pack: LanguagePack, params: VillanelleParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme="ABA ABA ABA ABA ABA ABAA",
            allow_identical=True,  # the refrains are the same line repeated
            refrains=[(0, 5), (0, 11), (0, 17), (2, 8), (2, 14), (2, 18)],
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
