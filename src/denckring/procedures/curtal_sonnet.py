"""Curtal sonnet — Hopkins's eleven-line contraction, rhyming ABCABC DBCDC."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.prosody import repeat_to
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.rhyme_scheme import form_report

SCHEME = "ABCABCDBCDC"
LINES = 11


class CurtalSonnetParams(RhymeParams):
    pass


@register
class CurtalSonnet(BaseProcedure[CurtalSonnetParams]):
    """A sonnet shrunk by a consistent fraction, not a sonnet cut short."""

    id = "curtal_sonnet"

    @classmethod
    def params_model(cls) -> type[CurtalSonnetParams]:
        return CurtalSonnetParams

    def _check(self, text: str, pack: LanguagePack, params: CurtalSonnetParams) -> Report:
        result = form_report(text, pack, scheme=SCHEME, metre=repeat_to("01", 5), lines=LINES)
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={
                "lines": float(len(line_spans(text))),
                "estimated_words": float(result.estimated),
            },
        )
