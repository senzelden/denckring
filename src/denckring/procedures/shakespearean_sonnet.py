"""Shakespearean sonnet — Three quatrains and a couplet in iambic pentameter."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, MetreParams, RhymeParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class ShakespeareanSonnetParams(RhymeParams, MetreParams):
    pass


@register
class ShakespeareanSonnet(BaseProcedure[ShakespeareanSonnetParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "shakespearean_sonnet"
    rules = (
        "does_not_rhyme",
        "identical_rhyme",
        "rhyme_undecidable",
        "unknown_rhyme",
        "unwanted_rhyme",
        "wrong_line_count",
        "wrong_line_length",
        "wrong_stress",
    )

    @classmethod
    def params_model(cls) -> type[ShakespeareanSonnetParams]:
        return ShakespeareanSonnetParams

    def _check(self, text: str, pack: LanguagePack, params: ShakespeareanSonnetParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme="ABABCDCDEFEFGG",
            metre="01" * 5,
            feminine_ending=params.feminine_ending,
            unknown_rhyme=params.unknown_rhyme,
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
