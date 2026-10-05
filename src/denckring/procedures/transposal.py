"""Transposal — each word is an anagram of the source word in the same place."""

from __future__ import annotations

from collections import Counter

from denckring.core.base import BaseProcedure, DiacriticParams, IdentityParams, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import unchanged
from denckring.core.text import letter_spans, word_spans


class TransposalParams(SourceParams, DiacriticParams, IdentityParams):
    pass


@register
class Transposal(BaseProcedure[TransposalParams]):
    """Word for word, the same letters in a different order."""

    id = "transposal"
    rules = ("extra_word", "missing_word", "not_a_transposal", "unchanged")

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
        copy = unchanged(
            text,
            params.source,
            pack,
            allow=params.allow_identity,
            # Word for word, so some word needs two different letters to reorder.
            alternative=lambda: any(
                len({ch for _, ch in letter_spans(word, pack, fold=fold)}) >= 2 for word in source
            ),
            fold=fold,
        )
        return self._report(
            good=matched,
            total=total + len(copy),
            violations=violations + copy,
            metrics={"words": float(len(candidate)), "matched": float(matched)},
        )
