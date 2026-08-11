"""Antigram — an anagram that differs from its source."""

from __future__ import annotations

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans
from denckring.procedures.anagram import AnagramParams, letter_counts, multiset_violations


class AntigramParams(AnagramParams):
    pass


@register
class Antigram(BaseProcedure[AntigramParams]):
    """An anagram whose sense opposes its source.

    Whether the meaning is genuinely opposite is a judgement no program makes;
    the checker verifies the anagram and that the text is not simply its source
    repeated, and the catalogue definition says so.
    """

    id = "antigram"

    @classmethod
    def params_model(cls) -> type[AntigramParams]:
        return AntigramParams

    def _check(self, text: str, pack: LanguagePack, params: AntigramParams) -> Report:
        fold = params.fold_diacritics
        candidate = letter_counts(text, pack, fold=fold)
        source = letter_counts(params.source, pack, fold=fold)
        violations, shared, total = multiset_violations(candidate, source)
        candidate_letters = [ch for _, ch in letter_spans(text, pack, fold=fold)]
        source_letters = [ch for _, ch in letter_spans(params.source, pack, fold=fold)]
        identical = candidate_letters == source_letters
        if identical:
            violations.append(
                Violation(
                    rule="unchanged",
                    offset=None,
                    found=text.strip(),
                    expected="a rearrangement, not the source itself",
                )
            )
        return self._report(
            good=shared - (1 if identical else 0),
            total=total,
            violations=violations,
            metrics={"letters": float(sum(candidate.values())), "shared": float(shared)},
        )
