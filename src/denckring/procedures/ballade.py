"""Ballade — three ababbcbc stanzas and a bcbc envoi, every part ending on the refrain.

The refrain is the form's point: the same line closes all four parts. `form_report`
already checks refrains by line index and the line count, so this row is three
constants.
"""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import repeat_to
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.procedures.rhyme_scheme import form_report

SCHEME = "ababbcbc" * 3 + "bcbc"
LINES = 28
#: The refrain closes stanza one at index 7, and must return at 15, 23 and 27.
REFRAINS = [(7, 15), (7, 23), (7, 27)]


class BalladeParams(BaseModel):
    pass


@register
class Ballade(BaseProcedure[BalladeParams]):
    """Twenty-eight lines, four of them the same line."""

    id = "ballade"

    @classmethod
    def params_model(cls) -> type[BalladeParams]:
        return BalladeParams

    def _check(self, text: str, pack: LanguagePack, params: BalladeParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme=SCHEME,
            metre=repeat_to("01", 4),
            refrains=REFRAINS,
            lines=LINES,
            allow_identical=True,  # the refrains are the same line repeated
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
