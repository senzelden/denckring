"""Monosyllabic prose — every word of one syllable."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


class MonosyllabicProseParams(BaseModel):
    pass


@register
class MonosyllabicProse(BaseProcedure[MonosyllabicProseParams]):
    """No word longer than one syllable, from first to last."""

    id = "monosyllabic_prose"

    @classmethod
    def params_model(cls) -> type[MonosyllabicProseParams]:
        return MonosyllabicProseParams

    def _check(self, text: str, pack: LanguagePack, params: MonosyllabicProseParams) -> Report:
        words = word_spans(text, pack)
        violations: list[Violation] = []
        estimated = 0
        for offset, word in words:
            count, exact = pack.syllable_count(word)
            if not exact:
                estimated += 1
            if count > 1:
                violations.append(
                    Violation(
                        rule="polysyllabic_word",
                        offset=offset,
                        found=word,
                        expected="a word of one syllable",
                        note=None if exact else "syllable count estimated from spelling",
                    )
                )
        return self._report(
            good=len(words) - len(violations),
            total=len(words),
            violations=violations,
            metrics={"words": float(len(words)), "estimated_words": float(estimated)},
        )
