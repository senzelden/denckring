"""Transposal — each word is an anagram of the source word in the same place."""

from __future__ import annotations

from collections import Counter

from denckring.core.base import BaseProcedure, DiacriticParams, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans


class TransposalParams(SourceParams, DiacriticParams):
    pass


@register
class Transposal(BaseProcedure[TransposalParams]):
    """Word for word, the same letters in a different order."""

    id = "transposal"

    @classmethod
    def params_model(cls) -> type[TransposalParams]:
        return TransposalParams

    def _check(self, text: str, pack: LanguagePack, params: TransposalParams) -> Report:
        fold = params.fold_diacritics
        candidate = word_spans(text, pack)
        source = [word for _, word in word_spans(params.source, pack)]
        violations: list[Violation] = []
        matched = 0
        for index, (offset, word) in enumerate(candidate):
            if index >= len(source):
                violations.append(
                    Violation(rule="extra_word", offset=offset, found=word, expected="")
                )
                continue
            here = Counter(ch for _, ch in letter_spans(word, pack, fold=fold))
            there = Counter(ch for _, ch in letter_spans(source[index], pack, fold=fold))
            if here == there:
                matched += 1
            else:
                violations.append(
                    Violation(
                        rule="not_a_transposal",
                        offset=offset,
                        found=word,
                        expected=f"a rearrangement of {source[index]!r}",
                    )
                )
        for missing in source[len(candidate) :]:
            violations.append(
                Violation(rule="missing_word", offset=None, found="", expected=missing)
            )
        total = max(len(candidate), len(source))
        return self._report(
            good=matched,
            total=total,
            violations=violations,
            metrics={"words": float(len(candidate)), "matched": float(matched)},
        )
