"""Limerick — Five lines rhyming AABBA."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.fields import param
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


class LimerickParams(RhymeParams):
    # Lear closes most of his limericks on the first line's word, which strict
    # practice counts a fault; False reports it as `identical_rhyme`, as every
    # other fixed form here does, and True is the reading his own text asks for.
    allow_identical: bool = Field(
        default=False,
        description=(
            "Permit a word to rhyme with itself, as Lear's limericks do; "
            "False reports a repeated end word as identical_rhyme."
        ),
        json_schema_extra=param("leniency"),
    )


@register
class Limerick(BaseProcedure[LimerickParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "limerick"
    checker_version = 2
    rules = (
        "does_not_rhyme",
        "identical_rhyme",
        "rhyme_undecidable",
        "unknown_rhyme",
        "unwanted_rhyme",
        "wrong_line_count",
    )

    @classmethod
    def params_model(cls) -> type[LimerickParams]:
        return LimerickParams

    def _check(self, text: str, pack: LanguagePack, params: LimerickParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme="AABBA",
            allow_identical=params.allow_identical,
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
