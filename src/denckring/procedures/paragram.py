"""Paragram — one letter changed, and the change made the point."""

from __future__ import annotations

import string
from itertools import combinations

from pydantic import Field

from denckring.core.base import ApplyParams, ConstructiveProcedure, DiacriticParams, plain
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans
from denckring.lang.base import NOUNS, SYLLABLES_HEURISTIC

#: What makes one candidate swap better than another. Highest first:
#: (1) the pronouncing dictionary actually has an entry for it — `pack.nouns()`
#: carries lower-cased scientific and unit abbreviations ("thc", "thm", "tce")
#: that are WordNet noun lemmas but nothing English speakers say, and none of
#: them has a CMUdict pronunciation, which is a sharper test than eyeballing
#: for a vowel; (2) it is in `pack.nouns()` at all — the same curated list
#: `anagram.apply` walks — rather than merely being in the union `is_word`
#: checks; (3) it is the longer word. A ranking, not a filter: a candidate
#: that clears none of these is still better than no candidate at all, so it
#: is never dropped from consideration, only ranked last.
CandidateScore = tuple[bool, bool, int]


class ParagramParams(DiacriticParams):
    minimum: int = Field(default=1, ge=0, description="How many swapped pairs are wanted.")


class ParagramApplyParams(ParagramParams, ApplyParams):
    pass


def differ_by_one(left: str, right: str) -> bool:
    """Equal length, differing at exactly one position."""
    if len(left) != len(right) or left == right:
        return False
    return sum(a != b for a, b in zip(left, right, strict=True)) == 1


@register
class Paragram(ConstructiveProcedure[ParagramParams, ParagramApplyParams]):
    """The swap is in the text, so the text alone decides.

    The row is `checkability: self` and requires no lexicon, so what can be
    verified is that both halves of the alteration are present — two words of a
    length, differing in one place. Whether the swap is witty is not a question
    code answers.
    """

    id = "paragram"

    @classmethod
    def params_model(cls) -> type[ParagramParams]:
        return ParagramParams

    def _normalise(self, text: str, pack: LanguagePack, fold: bool) -> list[str]:
        words = []
        for _, word in word_spans(text, pack):
            letters = "".join(
                pack.fold_diacritics(ch) if fold else ch.lower() for ch in word if ch.isalpha()
            )
            if letters:
                words.append(letters.lower())
        return words

    def _check(self, text: str, pack: LanguagePack, params: ParagramParams) -> Report:
        words = self._normalise(text, pack, params.fold_diacritics)
        pairs = [
            (left, right)
            for left, right in combinations(sorted(set(words)), 2)
            if differ_by_one(left, right)
        ]
        violations: list[Violation] = []
        if len(pairs) < params.minimum:
            violations.append(
                Violation(
                    rule="no_paragram",
                    offset=None,
                    found=f"{len(pairs)} swapped pairs",
                    expected=f"at least {params.minimum}",
                )
            )
        return self._report(
            good=min(len(pairs), params.minimum),
            total=params.minimum,
            violations=violations,
            metrics={"pairs": float(len(pairs))},
        )

    @classmethod
    def apply_params_model(cls) -> type[ParagramApplyParams]:
        return ParagramApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: ParagramApplyParams) -> Produced:
        """Change one letter of a word in `text` into another word the lexicon knows.

        The original word is left in place and the swapped word is inserted
        right after it, so both halves of the pair survive into the output —
        `check` finds its pair by comparing words already in the text, and a
        generator that replaced the original in place would leave nothing for
        it to compare against.

        Every word, position and letter in the text is a candidate, and every
        one of them is returned, best-scoring first — not just the first one
        found. A first-match search against a broad lexicon (CMUdict union
        WordNet) reliably surfaces the noisiest entry available: "the" always
        became "the che" long before anything a writer would reach for.
        `CandidateScore` ranks what is found rather than gating it, so the
        search still returns its best effort — never a refusal — when nothing
        scores well.

        `lexicon.words` is declared on the catalogue row's `apply_requires`,
        not its `requires`: the latter gates `check` too, and this row has
        always been checkable with core alone. ADR 0002 makes `apply` the
        optional half, and `apply_requires` is how the optional half states
        its own cost — the same arrangement `anagram` uses.
        """
        has_nouns = NOUNS in pack.capabilities
        has_syllables = SYLLABLES_HEURISTIC in pack.capabilities

        found: list[tuple[CandidateScore, int, str, str]] = []
        for offset, word in word_spans(text, pack):
            if not word.isalpha():
                continue
            lowered = word.lower()
            for position in range(len(word)):
                for letter in string.ascii_lowercase:
                    if letter == lowered[position]:
                        continue
                    swapped = lowered[:position] + letter + lowered[position + 1 :]
                    if not pack.is_word(swapped):
                        continue
                    # `syllable_count`'s second element is True only when the
                    # pronouncing dictionary itself listed the word, not when a
                    # spelling heuristic guessed at one — the same distinction
                    # every syllabic procedure's `estimated_words` metric rests on.
                    pronounced = has_syllables and pack.syllable_count(swapped)[1]
                    is_noun = has_nouns and pack.noun_index(swapped) is not None
                    score: CandidateScore = (pronounced, is_noun, len(swapped))
                    found.append((score, offset, word, swapped))
        if not found:
            raise NoCandidateWord(self.id)
        # Stable, so candidates that score equally keep the order the search
        # walked them in and two runs of the same input agree. `CandidateScore`
        # is a plain tuple and totally ordered, so this needs no key beyond it.
        found.sort(key=lambda candidate: candidate[0], reverse=True)
        return plain(
            [
                text[: offset + len(word)] + " " + swapped + text[offset + len(word) :]
                for _, offset, word, swapped in found
            ]
        )
