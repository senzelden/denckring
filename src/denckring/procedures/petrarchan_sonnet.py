"""Petrarchan sonnet — An octave rhyming ABBAABBA and a sestet."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class PetrarchanSonnetParams(RhymeParams):
    pass


@register
class PetrarchanSonnet(BaseProcedure[PetrarchanSonnetParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "petrarchan_sonnet"

    @classmethod
    def params_model(cls) -> type[PetrarchanSonnetParams]:
        return PetrarchanSonnetParams

    def _check(self, text: str, pack: LanguagePack, params: PetrarchanSonnetParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme="ABBAABBACDECDE",
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
