"""Ottava rima — eight hendecasyllables rhyming ABABABCC."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.prosody import repeat_to
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report

SCHEME = "ABABABCC"
LINES = 8


class OttavaRimaParams(RhymeParams):
    pass


@register
class OttavaRima(BaseProcedure[OttavaRimaParams]):
    """Assembled from the shared rhyme and metre checks."""

    id = "ottava_rima"

    @classmethod
    def params_model(cls) -> type[OttavaRimaParams]:
        return OttavaRimaParams

    def _check(self, text: str, pack: LanguagePack, params: OttavaRimaParams) -> Report:
        result = form_report(text, pack, scheme=SCHEME, metre=repeat_to("01", 5), lines=LINES)
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={
                "checks": float(result.total),
                "estimated_words": float(result.estimated),
            },
        )
