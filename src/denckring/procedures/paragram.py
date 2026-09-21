"""Paragram — one letter changed, and the change made the point."""

from __future__ import annotations

import string

from pydantic import Field

from denckring.core.base import (
    MID_BAND,
    ApplyParams,
    ConstructiveProcedure,
    DiacriticParams,
    plain,
)
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans
from denckring.lang.base import GRADED_WORDS, NOUNS, SYLLABLES_HEURISTIC

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
#: Ranks a swap, richest signal first, and sorted *descending* — so a larger
#: element wins. The fourth is the negated frequency band, because bands run
#: the other way (larger means rarer), and it sits last on purpose: it breaks
#: ties among candidates already equal on pronunciation, nounhood and length,
#: which is exactly the `bight` vs `light` case. Putting it earlier would let
#: commonness overrule those three rather than settle between them.
CandidateScore = tuple[bool, bool, int, int]


class ParagramParams(DiacriticParams):
    minimum: int = Field(default=1, ge=0, description="How many swapped pairs are wanted.")


class ParagramApplyParams(ParagramParams, ApplyParams):
    pass


# A fixed base under a 61-bit Mersenne prime modulus: fixed and non-randomised,
# so `deterministic: true` still means the same input always yields the same
# output, reproducible across machines and CI runs — not a per-run salt. The
# base is large and not round so a fixed-length wildcarded pattern doesn't
# collide with a shifted or truncated one under casual arithmetic coincidence.
_HASH_MOD = (1 << 61) - 1
_HASH_BASE = 1_000_003


def _pow_table(length: int) -> list[int]:
    """`_HASH_BASE**0 .. _HASH_BASE**length`, shared by every word in a length bucket."""
    powers = [1] * (length + 1)
    for i in range(1, length + 1):
        powers[i] = (powers[i - 1] * _HASH_BASE) % _HASH_MOD
    return powers


def _prefix_hash(word: str) -> list[int]:
    """Horner-scheme prefix hash under `_HASH_MOD`: `prefix[i]` hashes `word[:i]`.

    Built once per word in O(length) — this is the fix for the bug fix round 1
    found: the first version of this function rebuilt an O(length) wildcarded
    *string* for every one of a word's `length` positions, which was
    O(length^2) per word despite the docstring's O(U*L) claim, and hung on a
    single very long word (`_count_pairs(["a" * 99999 + "b"])` took over a
    second) even though the O(U^2*L) `combinations()` code this task
    originally replaced was instant on it — a one-element set has no pairs to
    check at all, so `combinations()` never even entered its inner loop. This
    version does the O(length) work once per word, not once per (word,
    position), which is what makes the per-position combine in `_count_pairs`
    O(1) and the whole function truly O(U*L) rather than O(U*L^2). Verified by
    `test_count_pairs_scales_with_word_length`, which fixes word *count* low
    and varies *length* — the axis the first version's own tests never
    exercised, which is why they didn't catch the regression.
    """
    prefix = [0] * (len(word) + 1)
    for i, ch in enumerate(word):
        prefix[i + 1] = (prefix[i] * _HASH_BASE + ord(ch) + 1) % _HASH_MOD
    return prefix


def _count_pairs(words: list[str]) -> int:
    """Count unique unordered pairs differing at exactly one position, in O(U*L).

    Replaces an all-pairs `combinations()` scan (P1-02): that was O(U^2 * L) and
    the project's own SECURITY.md treats a checker hang on adversarial input as
    in scope. For each length bucket, and each character position within that
    length, words sharing a wildcard pattern at that position agree everywhere
    except possibly there — so a true distance-1 pair collides in exactly one
    (length, position) bucket, and summing `n*(n-1)//2` per bucket counts every
    pair exactly once (this counting argument is unchanged from the first
    version of this function and does not need re-deriving).

    What changed under fix round 1: the wildcard pattern at a position is no
    longer an actual `length`-character string (rebuilding one per position
    made the first version O(U*L^2), not O(U*L) — see `_prefix_hash`). Instead
    each word gets one prefix-hash array, built once in O(length), and the
    hash of "everything except position `i`" is then an O(1) combination of
    the hash of the piece before `i` and the piece after `i`, both read off
    that one array via the standard substring-hash trick
    (`hash(l, r) = prefix[r] - prefix[l] * base**(r - l)`).

    This makes the count technically probabilistic rather than exact — a hash
    collision could in principle merge two different patterns into the same
    bucket and overcount a pair that was never really there. With a fixed
    61-bit modulus that risk is not a practical concern: for it to matter, two
    distinct `(length - 1)`-character strings would need to collide under one
    fixed polynomial hash, which at this modulus size is the same accepted
    tradeoff established "exact" string-matching algorithms (e.g. Rabin-Karp)
    make routinely. `test_count_pairs_agrees_with_the_reference_on_small_corpora`
    exercises exactly the small-alphabet, many-near-collision regime where a
    weak hash would be most likely to show it, and finds none across 200
    random corpora.
    """
    by_length: dict[int, list[str]] = {}
    for word in set(words):
        by_length.setdefault(len(word), []).append(word)
    if not by_length:
        return 0

    pow_table = _pow_table(max(by_length))

    total = 0
    for length, bucket_words in by_length.items():
        # O(length) per word — done once per word, not once per (word,
        # position); see `_prefix_hash`.
        prefix_table = [_prefix_hash(word) for word in bucket_words]
        for position in range(length):
            suffix_len = length - position - 1
            power = pow_table[suffix_len]
            counts: dict[int, int] = {}
            for prefix in prefix_table:
                key = (
                    prefix[position] * power + (prefix[length] - prefix[position + 1] * power)
                ) % _HASH_MOD
                counts[key] = counts.get(key, 0) + 1
            total += sum(n * (n - 1) // 2 for n in counts.values())
    return total


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
        pair_count = _count_pairs(words)
        violations: list[Violation] = []
        if pair_count < params.minimum:
            violations.append(
                Violation(
                    rule="no_paragram",
                    offset=None,
                    found=f"{pair_count} swapped pairs",
                    expected=f"at least {params.minimum}",
                )
            )
        return self._report(
            good=min(pair_count, params.minimum),
            total=params.minimum,
            violations=violations,
            metrics={"pairs": float(pair_count)},
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

        # Read only where the pack declares it. `lexicon.graded_words` is
        # deliberately absent from this row's `apply_requires`: a ranking signal
        # is worth having, and not worth refusing to generate without.
        grades = pack.graded_words() if GRADED_WORDS in pack.capabilities else {}
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
                    # A word the table does not list is mid-band, not
                    # commonest — the same default `calculator_word` chose, and
                    # for the same reason: absent is not evidence of anything.
                    band = grades.get(swapped, MID_BAND)
                    score: CandidateScore = (pronounced, is_noun, len(swapped), -band)
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
