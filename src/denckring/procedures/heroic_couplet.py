"""Heroic couplet — Rhyming pairs of iambic pentameter."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report


def _line_count(text: str) -> int:
    from denckring.core.text import line_spans

    return len(line_spans(text))


def _terza_scheme(lines: int) -> str:
    """ABA BCB CDC …, with the last line taking the previous tercet's middle rhyme."""
    letters = []
    for index in range(lines):
        tercet, position = divmod(index, 3)
        letters.append(chr(65 + tercet + (1 if position == 1 else 0)))
    return "".join(letters)


class HeroicCoupletParams(RhymeParams):
    pass


@register
class HeroicCouplet(BaseProcedure[HeroicCoupletParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "heroic_couplet"

    @classmethod
    def params_model(cls) -> type[HeroicCoupletParams]:
        return HeroicCoupletParams

    def _check(self, text: str, pack: LanguagePack, params: HeroicCoupletParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme="".join(chr(65 + i // 2) for i in range(_line_count(text))),
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
