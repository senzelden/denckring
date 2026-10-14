"""Iambic pentameter — Five iambic feet to the line."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, ScansionParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class IambicPentameterParams(ScansionParams):
    pass


@register
class IambicPentameter(BaseProcedure[IambicPentameterParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "iambic_pentameter"

    checker_version = 2
    rules = ("wrong_line_length", "wrong_stress")
    local_scope = "line"

    @classmethod
    def params_model(cls) -> type[IambicPentameterParams]:
        return IambicPentameterParams

    def _check(self, text: str, pack: LanguagePack, params: IambicPentameterParams) -> Report:
        result = form_report(
            text,
            pack,
            metre="01" * 5,
            feminine_ending=params.feminine_ending,
            licences=params.licences(),
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
