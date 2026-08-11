"""Pangram — the text contains every letter of the alphabet."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class PangramParams(BaseModel):
    perfect: bool = Field(default=False, description="Require each letter exactly once.")


@register
class Pangram(BaseProcedure[PangramParams]):
    """The one procedure whose empty text is unsatisfied rather than vacuous.

    Every other Batch 1 procedure forbids something, so an empty text breaks no
    rule. A pangram requires something, so an empty text supplies none of it and
    scores 0.0 — which is why this checker builds its Report directly instead of
    going through `_report`.
    """

    id = "pangram"

    @classmethod
    def params_model(cls) -> type[PangramParams]:
        return PangramParams

    def _check(self, text: str, pack: LanguagePack, params: PangramParams) -> Report:
        alphabet = pack.alphabet()
        counts = Counter(ch for _, ch in letter_spans(text, pack) if ch in alphabet)
        missing = [ch for ch in alphabet if ch not in counts]
        violations = [
            Violation(rule="missing_letter", offset=None, found="", expected=ch) for ch in missing
        ]
        coverage = (len(alphabet) - len(missing)) / len(alphabet)
        score = coverage
        if params.perfect:
            excess = sum(count - 1 for count in counts.values() if count > 1)
            violations += [
                Violation(rule="repeated_letter", offset=None, found=ch, expected=f"{ch} once")
                for ch, count in sorted(counts.items())
                if count > 1
            ]
            score = coverage * len(alphabet) / (len(alphabet) + excess)
        return Report(
            procedure=self.id,
            satisfied=score == 1.0,
            score=score,
            violations=violations,
            metrics={
                "coverage": coverage,
                "distinct_letters": float(len(counts)),
                "total_letters": float(sum(counts.values())),
            },
        )
