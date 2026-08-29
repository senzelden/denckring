"""Anagram — the candidate uses exactly the letters of its source."""

from __future__ import annotations

from collections import Counter

from pydantic import Field

from denckring.core.base import (
    ApplyParams,
    ConstructiveProcedure,
    DiacriticParams,
    SourceParams,
)
from denckring.core.errors import InputTooLong
from denckring.core.protocol import Candidate, LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class AnagramParams(SourceParams, DiacriticParams):
    pass


class AnagramApplyParams(AnagramParams, ApplyParams):
    max_words: int = Field(
        default=3,
        ge=1,
        description="How many words a cover may use.",
    )
    min_word_length: int = Field(
        default=2,
        ge=1,
        description="Shortest word a cover may use, which is what keeps orphan letters out.",
    )
    # `le=60` matches `MAX_BAND` in the build script: nothing above band 60 is
    # shipped, so without a ceiling `max_size=70` would silently mean 60 — a
    # parameter promising more than the data delivers, which is the defect class
    # ADR 0015 exists to prevent. Raising the ceiling means raising both.
    max_size: int = Field(
        default=60,
        ge=1,
        le=60,
        description=(
            "Largest SCOWL size band to draw words from. Larger bands are less "
            "common words; 60 is the largest SCOWL states it is confident carries "
            "no misspellings, and the largest this package ships."
        ),
    )
    # Measured against the shipped list at `max_words=3`, `min_word_length=2`:
    # `listen` exhausts in 2,994 nodes, `dormitory` in 7,958, `astronomer` in
    # 747,769 (0.92s). A million is the smallest round value that leaves the
    # worst of the three untruncated, with about 34% headroom. Work per node is
    # near-constant, so this is also what bounds wall-clock time — `MAX_LETTERS`
    # does not: an unbounded search over a seventeen-letter input runs for minutes.
    max_nodes: int = Field(
        default=1_000_000,
        ge=1,
        description="Search nodes to visit before stopping and reporting truncation.",
    )


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
class Anagram(ConstructiveProcedure[AnagramParams, AnagramApplyParams]):
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

    #: The letter count past which the cover search is not worth starting. The
    #: candidate pool grows with the number of lexicon words that fit inside the
    #: remaining letters, and a real anagram of a paragraph is not something any
    #: depth-bounded search finds.
    #:
    #: This is not what bounds the search's cost — `max_nodes` is, and measurably:
    #: an unbounded search over a seventeen-letter input runs for minutes, and 17
    #: is well inside this cap. What this cap does is refuse the inputs where even
    #: a budgeted search would return nothing worth reading. See ADR 0028 on why
    #: the budget counts nodes and not seconds.
    MAX_LETTERS = 60

    @classmethod
    def apply_params_model(cls) -> type[AnagramApplyParams]:
        return AnagramApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: AnagramApplyParams) -> Produced:
        """Rearrange the letters of `text` into covers the lexicon can spell.

        A depth-first search for sets of words whose letters together are exactly
        the source's, bounded by `max_words` and by a node budget, then ranked.
        Nothing is left over: a walk that cannot spend its remaining letters is
        not a cover and is abandoned, where the greedy walk this replaced emitted
        the unspendable tail as a run of letters to keep `check` satisfied.

        `lexicon.graded_words` is declared on the catalogue row's `apply_requires`,
        not its `requires`: the latter gates `check` too, and `check` has always
        run on core alone. ADR 0002 makes `apply` the optional half, and
        `apply_requires` is how the optional half states its own cost.

        The row declared `lexicon.words` and the code called `pack.nouns()` —
        neither the capability it named nor the one it used was the one it wanted.
        Nouns are why `astronomer` returned itself: a source word that is itself a
        noun is the longest cover of its own letters. Narrowing to nouns could not
        have been the fix either, since `dirty` and `silent` are not nouns.
        """
        letters = sorted(ch for _, ch in letter_spans(text, pack, fold=params.fold_diacritics))
        if len(letters) > self.MAX_LETTERS:
            raise InputTooLong(self.id, len(letters), self.MAX_LETTERS)
        source = Counter(letters)

        # Filtered to words that fit before the walk begins, not inside it: the
        # pool for `astronomer` is 373 words out of the whole lexicon, and testing
        # containment once per word beats testing it once per node.
        graded = pack.graded_words()
        pool = sorted(
            word
            for word, band in graded.items()
            if band <= params.max_size
            and len(word) >= params.min_word_length
            and not Counter(word) - source
        )

        covers: list[tuple[int, int, str]] = []
        # A list, not an int, because `walk` closes over it and rebinding an int
        # inside a closure would need `nonlocal` in every branch that spends one.
        budget = [params.max_nodes]

        def walk(remaining: Counter[str], chosen: list[str], start: int) -> None:
            if not sum(remaining.values()):
                # `chosen` is empty only at the root, when the input held no
                # letters at all — `apply(".")`. The empty cover is not a result,
                # so it is dropped here rather than reaching the spine as a
                # candidate whose `max()` has nothing to take a band from; with
                # no covers at all the spine raises `DegenerateOutput.NOTHING`,
                # which is what a letterless input got before this search.
                if chosen:
                    covers.append(
                        (len(chosen), max(graded[word] for word in chosen), " ".join(chosen))
                    )
                return
            if len(chosen) == params.max_words:
                return
            # `start` and not `start + 1`: a cover may legitimately use the same
            # word twice when the letters allow it. Not descending below `start`
            # is what keeps `room dirty` and `dirty room` from both being found —
            # they are one cover, and the ranking picks its spelling.
            for index in range(start, len(pool)):
                if budget[0] <= 0:
                    return
                budget[0] -= 1
                word = pool[index]
                if Counter(word) - remaining:
                    continue
                walk(remaining - Counter(word), [*chosen, word], index)

        walk(source, [], 0)

        # Fewest words, then commonest word last — SCOWL's bands run backwards
        # from intuition, so a cover is judged by its *least* common word (its
        # maximum band) and lower wins. Alphabetical last: with the word count it
        # is Dewdney's ordering in *The Armchair Universe* (1988), the band
        # inserted between the two, and it is what makes the order total so the
        # row stays `deterministic: true`.
        covers.sort()
        return Produced(
            candidates=[
                Candidate(text=cover, metrics={"words": float(count), "max_band": float(band)})
                for count, band, cover in covers
            ],
            truncated=budget[0] <= 0,
        )
