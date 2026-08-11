"""Anagram — the candidate uses exactly the letters of its source."""

from __future__ import annotations

from collections import Counter

from denckring.core.base import BaseProcedure, DiacriticParams, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class AnagramParams(SourceParams, DiacriticParams):
    pass


def letter_counts(text: str, pack: LanguagePack, *, fold: bool) -> Counter[str]:
    return Counter(ch for _, ch in letter_spans(text, pack, fold=fold))


def multiset_violations(
    candidate: Counter[str], source: Counter[str]
) -> tuple[list[Violation], int, int]:
    """Report the letters that are surplus and those that are short."""
    violations: list[Violation] = []
    for letter in sorted(set(candidate) | set(source)):
        difference = candidate[letter] - source[letter]
        if difference > 0:
            violations.append(
                Violation(
                    rule="surplus_letter",
                    offset=None,
                    found=letter * difference,
                    expected=f"{source[letter]} of {letter!r}",
                )
            )
        elif difference < 0:
            violations.append(
                Violation(
                    rule="missing_letter",
                    offset=None,
                    found=f"{candidate[letter]} of {letter!r}",
                    expected=letter * -difference,
                )
            )
    shared = sum((candidate & source).values())
    total = max(sum(candidate.values()), sum(source.values()))
    return violations, shared, total


@register
class Anagram(BaseProcedure[AnagramParams]):
    """Every letter of the source, rearranged, and nothing else."""

    id = "anagram"

    @classmethod
    def params_model(cls) -> type[AnagramParams]:
        return AnagramParams

    def _check(self, text: str, pack: LanguagePack, params: AnagramParams) -> Report:
        fold = params.fold_diacritics
        candidate = letter_counts(text, pack, fold=fold)
        source = letter_counts(params.source, pack, fold=fold)
        violations, shared, total = multiset_violations(candidate, source)
        return self._report(
            good=shared,
            total=total,
            violations=violations,
            metrics={"letters": float(sum(candidate.values())), "shared": float(shared)},
        )
