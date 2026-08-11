"""Alphabetical sentence — the words run in alphabetical order."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans


class AlphabeticalSentenceParams(DiacriticParams):
    pass


@register
class AlphabeticalSentence(BaseProcedure[AlphabeticalSentenceParams]):
    """Every word sorts at or after the word before it."""

    id = "alphabetical_sentence"

    @classmethod
    def params_model(cls) -> type[AlphabeticalSentenceParams]:
        return AlphabeticalSentenceParams

    def _check(self, text: str, pack: LanguagePack, params: AlphabeticalSentenceParams) -> Report:
        words = [
            (offset, "".join(ch for _, ch in letter_spans(word, pack, fold=params.fold_diacritics)))
            for offset, word in word_spans(text, pack)
        ]
        violations = [
            Violation(
                rule="out_of_order",
                offset=offset,
                found=word,
                expected=f"a word sorting at or after {words[index - 1][1]!r}",
            )
            for index, (offset, word) in enumerate(words)
            if index > 0 and word < words[index - 1][1]
        ]
        return self._report(
            good=len(words) - len(violations),
            total=len(words),
            violations=violations,
            metrics={"words": float(len(words)), "out_of_order": float(len(violations))},
        )
