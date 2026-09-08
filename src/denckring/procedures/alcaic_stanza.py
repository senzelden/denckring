"""Alcaic stanza — two hendecasyllables, an enneasyllable, a decasyllable."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import stanza_violations
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.core.text import line_spans

HENDECASYLLABLE = "?1011100101"
ENNEASYLLABLE = "?101?1011"
DECASYLLABLE = "100100101?"

PATTERNS = [[HENDECASYLLABLE], [HENDECASYLLABLE], [ENNEASYLLABLE], [DECASYLLABLE]]


class AlcaicStanzaParams(BaseModel):
    pass


@register
class AlcaicStanza(BaseProcedure[AlcaicStanzaParams]):
    """Four lines of 11, 11, 9 and 10 syllables in a fixed stress pattern.

    The English accentual reading of a quantitative measure, as for the
    sapphic stanza.
    """

    id = "alcaic_stanza"

    @classmethod
    def params_model(cls) -> type[AlcaicStanzaParams]:
        return AlcaicStanzaParams

    def _check(self, text: str, pack: LanguagePack, params: AlcaicStanzaParams) -> Report:
        result = stanza_violations(text, pack, PATTERNS)
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            evidence=list(result.evidence),
            metrics={
                "lines": float(len(line_spans(text))),
                "estimated_words": float(result.estimated),
            },
        )
