"""Sapphic stanza — three hendecasyllables closed by an adonic."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import stanza_violations
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register

#: Trochee, trochee-with-anceps, dactyl, trochee, trochee-with-anceps.
#: The `?` marks are the classical anceps, which `_fits` honours on the
#: pattern side.
HENDECASYLLABLE = "101?100101?"

#: The adonic: dactyl, trochee-with-anceps.
ADONIC = "1001?"

PATTERNS = [[HENDECASYLLABLE], [HENDECASYLLABLE], [HENDECASYLLABLE], [ADONIC]]


class SapphicStanzaParams(BaseModel):
    pass


@register
class SapphicStanza(BaseProcedure[SapphicStanzaParams]):
    """Four lines of 11, 11, 11 and 5 syllables in a fixed stress pattern.

    The English accentual reading of a quantitative measure — stress standing
    in for vowel length, which English does not have.
    """

    id = "sapphic_stanza"

    @classmethod
    def params_model(cls) -> type[SapphicStanzaParams]:
        return SapphicStanzaParams

    def _check(self, text: str, pack: LanguagePack, params: SapphicStanzaParams) -> Report:
        result = stanza_violations(text, pack, PATTERNS)
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={"lines": float(len(PATTERNS)), "estimated_words": float(result.estimated)},
        )
