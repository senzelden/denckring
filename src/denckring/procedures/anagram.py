"""Anagram — the candidate uses exactly the letters of its source."""

from __future__ import annotations

from collections import Counter
from typing import Any

from denckring.core.base import (
    BaseProcedure,
    DiacriticParams,
    SourceParams,
    require_capability,
)
from denckring.core.errors import InputTooLong
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans
from denckring.lang.base import WORDS


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

    #: Longer than this and the search is not worth the wait: the candidate pool
    #: is every prefix-length of the remaining letters, and a real anagram of a
    #: paragraph is not something a greedy walk finds anyway.
    MAX_LETTERS = 60

    def apply(self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: Any) -> str:
        """Rearrange the letters of `text` into words the lexicon knows.

        Greedy: take the longest word the remaining letters can still spell, and
        repeat. Whatever will not form a word is emitted as a trailing run, which
        keeps the letter multiset — and therefore `check` — intact even when the
        tail is unusable.

        `lexicon.words` is required here but deliberately NOT added to the
        catalogue row's `requires`: that list gates `check` too, and adding it
        would make `check` raise for every caller without the data extra, for a
        procedure that has always been checkable with core alone. ADR 0002 makes
        `apply` the optional half, so the generator carries its own requirement.
        """
        from denckring.lang import get_pack

        pack = get_pack(lang)
        require_capability(pack, WORDS, self.id)
        parsed = self.parse_params({"source": text, **params})

        letters = sorted(ch for _, ch in letter_spans(text, pack, fold=parsed.fold_diacritics))
        if len(letters) > self.MAX_LETTERS:
            raise InputTooLong(self.id, len(letters), self.MAX_LETTERS)

        remaining = Counter(letters)
        found: list[str] = []
        while sum(remaining.values()):
            word = self._longest_word(remaining, pack)
            if word is None:
                break
            found.append(word)
            remaining -= Counter(word)
        if sum(remaining.values()):
            found.append("".join(sorted(remaining.elements())))
        return " ".join(found)

    @staticmethod
    def _longest_word(remaining: Counter[str], pack: LanguagePack, minimum: int = 2) -> str | None:
        """The longest word the remaining letters spell, or None.

        Walks candidate words from the lexicon rather than permuting letters:
        permutations of even a dozen letters are astronomically many, while the
        word list is finite and already indexed.
        """
        best: str | None = None
        for candidate in pack.nouns():
            folded = candidate.casefold()
            if len(folded) <= (len(best) if best else minimum - 1):
                continue
            if not (Counter(folded) - remaining):
                best = folded
        return best
