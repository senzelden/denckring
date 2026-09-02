"""Supervocalic — each of the five vowels exactly once."""

from __future__ import annotations

from collections import Counter

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class SupervocalicParams(DiacriticParams):
    pass


@register
class Supervocalic(BaseProcedure[SupervocalicParams]):
    """Every vowel once and once only, so an empty text supplies none of them.

    Reads `vowel_inventory()` rather than `vowels()`: the latter carries the
    accented forms, which folded text can never contain, so this row was
    unsatisfiable in German and French (ADR 0035, D1).
    """

    id = "supervocalic"

    @classmethod
    def params_model(cls) -> type[SupervocalicParams]:
        return SupervocalicParams

    def _check(self, text: str, pack: LanguagePack, params: SupervocalicParams) -> Report:
        vowel_set = pack.vowel_inventory()
        counts = Counter(
            ch for _, ch in letter_spans(text, pack, fold=params.fold_diacritics) if ch in vowel_set
        )
        required = sorted(vowel_set)
        missing = [ch for ch in required if counts[ch] == 0]
        repeated = [ch for ch in required if counts[ch] > 1]
        violations = [
            Violation(rule="missing_vowel", offset=None, found="", expected=ch) for ch in missing
        ]
        violations += [
            Violation(rule="repeated_vowel", offset=None, found=ch, expected=f"{ch} once")
            for ch in repeated
        ]
        excess = sum(counts[ch] - 1 for ch in repeated)
        coverage = (len(required) - len(missing)) / len(required)
        score = coverage * len(required) / (len(required) + excess)
        return Report(
            procedure=self.id,
            satisfied=score == 1.0,
            score=score,
            violations=violations,
            metrics={"coverage": coverage, "excess": float(excess)},
        )
