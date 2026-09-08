"""Dactylic hexameter — six feet, each a dactyl or a spondee."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import feet, line_metre
from denckring.core.protocol import Evidence, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans

#: A dactyl, or the spondee that may stand in for it.
DACTYL = ("100", "11")

#: Feet 1-4 substitute freely. The fifth is fixed as a dactyl: a spondaic fifth
#: exists but is rare enough that accepting it would cost more in false
#: positives than it buys. The sixth is a spondee or, by brevis in longo, a
#: trochee.
HEXAMETER = [DACTYL, DACTYL, DACTYL, DACTYL, ("100",), ("11", "10")]

PATTERNS = feet(HEXAMETER)


class DactylicHexameterParams(BaseModel):
    pass


@register
class DactylicHexameter(BaseProcedure[DactylicHexameterParams]):
    """Scans every line against the thirty-two readings of the hexameter.

    This is the English accentual reading of a quantitative measure: classical
    quantity is vowel length, which English does not have, so stress stands in
    for it as it has since the Renaissance. The caesura is not checked.
    """

    id = "dactylic_hexameter"

    @classmethod
    def params_model(cls) -> type[DactylicHexameterParams]:
        return DactylicHexameterParams

    def _check(self, text: str, pack: LanguagePack, params: DactylicHexameterParams) -> Report:
        lines = line_spans(text)
        if not lines:
            return self._report(
                good=0,
                total=1,
                violations=[
                    Violation(
                        rule="wrong_line_count", offset=None, found="0 lines", expected="1 line"
                    )
                ],
                metrics={"lines": 0.0, "estimated_words": 0.0},
            )

        violations: list[Violation] = []
        good = 0
        total = 0
        estimated = 0
        evidence: list[Evidence] = []
        for offset, line in lines:
            result = line_metre(line, pack, PATTERNS, offset)
            violations += result.violations
            good += result.good
            total += result.total
            estimated += result.estimated
            evidence += result.evidence
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            evidence=evidence,
            metrics={"lines": float(len(lines)), "estimated_words": float(estimated)},
        )
