"""Elegiac couplet — a dactylic hexameter answered by a pentameter."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import feet, line_metre
from denckring.core.protocol import Evidence, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.dactylic_hexameter import DACTYL
from denckring.procedures.dactylic_hexameter import PATTERNS as HEXAMETER_PATTERNS

#: The pentameter is two hemiepes. The first admits the spondee; the second
#: never does, and that asymmetry is the form rather than an oversight.
PENTAMETER = [DACTYL, DACTYL, ("1",), ("100",), ("100",), ("1",)]

PENTAMETER_PATTERNS = feet(PENTAMETER)


class ElegiacCoupletParams(BaseModel):
    pass


@register
class ElegiacCouplet(BaseProcedure[ElegiacCoupletParams]):
    """Odd lines scan as hexameters, even lines as pentameters.

    That the pair forms one unit of sense is the form's point and is not
    checked — sense is not a property this or any checker can read.
    """

    id = "elegiac_couplet"

    @classmethod
    def params_model(cls) -> type[ElegiacCoupletParams]:
        return ElegiacCoupletParams

    def _check(self, text: str, pack: LanguagePack, params: ElegiacCoupletParams) -> Report:
        lines = line_spans(text)
        violations: list[Violation] = []
        if not lines or len(lines) % 2:
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected="an even number of lines, at least two",
                )
            )
        if not lines:
            return self._report(
                good=0,
                total=1,
                violations=violations,
                metrics={"lines": 0.0, "estimated_words": 0.0},
            )

        good = 0
        total = 0
        estimated = 0
        evidence: list[Evidence] = []
        for index, (offset, line) in enumerate(lines):
            options = HEXAMETER_PATTERNS if index % 2 == 0 else PENTAMETER_PATTERNS
            result = line_metre(line, pack, options, offset)
            violations += result.violations
            good += result.good
            total += result.total
            estimated += result.estimated
            evidence += result.evidence
        return self._report(
            good=good,
            total=max(total, 1) + (1 if len(lines) % 2 else 0),
            violations=violations,
            metrics={"lines": float(len(lines)), "estimated_words": float(estimated)},
            evidence=evidence,
        )
