"""Semordnilap — a word that spells a different word backwards."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans


class SemordnilapParams(BaseModel):
    pass


@register
class Semordnilap(BaseProcedure[SemordnilapParams]):
    """Unlike a palindrome, the reversal must be a *different* word."""

    id = "semordnilap"

    @classmethod
    def params_model(cls) -> type[SemordnilapParams]:
        return SemordnilapParams

    def _check(self, text: str, pack: LanguagePack, params: SemordnilapParams) -> Report:
        words = word_spans(text, pack)
        violations: list[Violation] = []
        for offset, word in words:
            # fold=False: the lexicon stores each language's own diacritics
            # (German umlauts included), so folding before the query would
            # make every umlaut word unfindable and could assemble a false
            # positive from pieces not actually present in the text.
            letters = "".join(ch for _, ch in letter_spans(word, pack, fold=False))
            reversed_letters = letters[::-1]
            if reversed_letters == letters:
                violations.append(
                    Violation(
                        rule="palindrome_not_semordnilap",
                        offset=offset,
                        found=word,
                        expected="a word whose reversal differs from itself",
                    )
                )
            elif not pack.is_word(reversed_letters):
                violations.append(
                    Violation(
                        rule="reversal_is_not_a_word",
                        offset=offset,
                        found=reversed_letters,
                        expected="a word",
                    )
                )
        return self._report(
            good=len(words) - len(violations),
            total=len(words),
            violations=violations,
            metrics={"words": float(len(words))},
        )
