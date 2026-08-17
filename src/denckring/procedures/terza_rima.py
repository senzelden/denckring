"""Terza rima — Interlocking tercets rhyming ABA BCB CDC."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
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


class TerzaRimaParams(BaseModel):
    pass


@register
class TerzaRima(BaseProcedure[TerzaRimaParams]):
    """Assembled from the shared rhyme, metre and refrain checks."""

    id = "terza_rima"

    @classmethod
    def params_model(cls) -> type[TerzaRimaParams]:
        return TerzaRimaParams

    def _check(self, text: str, pack: LanguagePack, params: TerzaRimaParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme=_terza_scheme(_line_count(text)),
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
