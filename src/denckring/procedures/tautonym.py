"""Tautonym — every word is one letter-sequence written twice."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans

HALVES = 2


class TautonymParams(DiacriticParams):
    pass


@register
class Tautonym(BaseProcedure[TautonymParams]):
    """Words like couscous, whose two halves are identical."""

    id = "tautonym"

    @classmethod
    def params_model(cls) -> type[TautonymParams]:
        return TautonymParams

    def _check(self, text: str, pack: LanguagePack, params: TautonymParams) -> Report:
        words = word_spans(text, pack)
        violations: list[Violation] = []
        for offset, word in words:
            letters = "".join(ch for _, ch in letter_spans(word, pack, fold=params.fold_diacritics))
            half, remainder = divmod(len(letters), HALVES)
            doubled = remainder == 0 and half > 0 and letters[:half] == letters[half:]
            if not doubled:
                violations.append(
                    Violation(
                        rule="not_doubled",
                        offset=offset,
                        found=word,
                        expected="a letter-sequence written twice",
                    )
                )
        return self._report(
            good=len(words) - len(violations),
            total=len(words),
            violations=violations,
            metrics={"words": float(len(words)), "not_doubled": float(len(violations))},
        )
