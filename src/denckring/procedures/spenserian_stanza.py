"""Spenserian stanza — ABABBCBCC, eight pentameters and a closing alexandrine.

The last line is the form. A ninth pentameter is the error this checks for, so the
metre is per-line and `stanza_violations` does the scanning rather than `form_report`,
whose single `metre=` string cannot say "all but the last".
"""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import repeat_to, scheme_violations, stanza_violations
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register

SCHEME = "ABABBCBCC"
PENTAMETER = repeat_to("01", 5)
ALEXANDRINE = repeat_to("01", 6)
PATTERNS = [[PENTAMETER]] * 8 + [[ALEXANDRINE]]


class SpenserianStanzaParams(BaseModel):
    pass


@register
class SpenserianStanza(BaseProcedure[SpenserianStanzaParams]):
    """Nine lines, the ninth one foot longer than the rest."""

    id = "spenserian_stanza"

    @classmethod
    def params_model(cls) -> type[SpenserianStanzaParams]:
        return SpenserianStanzaParams

    def _check(self, text: str, pack: LanguagePack, params: SpenserianStanzaParams) -> Report:
        metre = stanza_violations(text, pack, PATTERNS)
        found, matched, checks = scheme_violations(text, pack, SCHEME, allow_identical=False)
        return self._report(
            good=metre.good + matched,
            total=metre.total + checks,
            violations=metre.violations + found,
            metrics={
                "checks": float(metre.total + checks),
                "estimated_words": float(metre.estimated),
            },
        )
