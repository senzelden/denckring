"""Word ladder — Lewis Carroll's Doublets: one letter changed per step, every
step itself a word.

Task 1 corrected this row's `requires` to `[tokens, fold_diacritics,
lexicon.words]`: the "every step being itself a word" clause is a membership
test, via `pack.is_word`, and comparing two same-length words letter by letter
is what `fold_diacritics` earns its keep on — see `_folded` below.
"""

from __future__ import annotations

import string
from collections import deque
from functools import lru_cache
from itertools import pairwise

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure, require_capability
from denckring.core.errors import InvalidParams, NoCandidateWord
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans
from denckring.lang.base import WORDS

#: A ladder longer than this is not worth searching for. Carroll's own puzzles
#: run to a handful of steps; a breadth-first search that has not reached the
#: target within this many words is far more likely sitting inside a large
#: connected component of same-length words than about to succeed one step
#: later. Bounds the search's depth; MAX_EXPLORED bounds its breadth.
MAX_LADDER_WORDS = 12

#: A safety valve on top of MAX_LADDER_WORDS. The graph of same-length words
#: joined by one-letter swaps is finite, so breadth-first search over it
#: terminates on its own even with no cap at all — unlike a depth-first walk,
#: which can wander a fifty-thousand-word lexicon indefinitely. But "finite"
#: still means "thousands of nodes" for common lengths, and this caps how many
#: of them one `apply` call will visit before giving up, so a single call
#: cannot make the repo-wide round-trip fuzz property (`tests/test_round_trip.py`)
#: slow no matter what start and target it happens to draw.
MAX_EXPLORED = 4000


def _folded(word: str, pack: LanguagePack) -> str:
    """Letters only, diacritics folded — what `check` compares position by position.

    Deliberately not what `pack.is_word` is asked about: `charade` established
    that folding before a lexicon lookup can make an accented word unfindable,
    because the lexicon stores each language's own diacritics. Folding here is
    for comparing two spellings' *shapes*, not for looking either of them up.
    """
    return "".join(pack.fold_diacritics(ch) for ch in word if ch.isalpha())


class WordLadderParams(BaseModel):
    # Named `target`, not `end` or anything shorter: `apply`'s reserved
    # keywords are `seed` and `lang` (see `every_nth_word.py`), and `target`
    # collides with neither. Left optional — defaulting to `None` — so `check`,
    # which never needs a target, only the ladder text itself, can be called
    # with no extra parameter; `apply` is the one that requires it, and does
    # so explicitly rather than through this field's own validation, because
    # the same model has to serve both callers.
    target: str | None = Field(
        default=None, description="The word `apply` searches a ladder toward."
    )


@register
class WordLadder(BaseProcedure[WordLadderParams]):
    """Constructive: `apply` searches the ladder `check` verifies."""

    id = "word_ladder"

    @classmethod
    def params_model(cls) -> type[WordLadderParams]:
        return WordLadderParams

    def _check(self, text: str, pack: LanguagePack, params: WordLadderParams) -> Report:
        spans = word_spans(text, pack)
        violations: list[Violation] = []
        good = 0
        total = 0

        for offset, word in spans:
            total += 1
            if pack.is_word(word):
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="not_a_word",
                        offset=offset,
                        found=word,
                        expected="a word the lexicon knows",
                    )
                )

        for (_, first), (offset, second) in pairwise(spans):
            total += 1
            folded_first = _folded(first, pack)
            folded_second = _folded(second, pack)
            if len(folded_first) != len(folded_second):
                violations.append(
                    Violation(
                        rule="different_length",
                        offset=offset,
                        found=second,
                        expected=f"a word of length {len(folded_first)}, like {first!r}",
                    )
                )
                continue
            changed = sum(1 for a, b in zip(folded_first, folded_second, strict=True) if a != b)
            if changed == 1:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="step_too_large",
                        offset=offset,
                        found=second,
                        expected=f"a word differing from {first!r} by exactly one letter",
                        note=f"{changed} letters differ" if changed else "no letters differ",
                    )
                )

        # `total` stays 0 for empty text rather than being floored at 1: an
        # empty ladder violates none of the per-word or per-step rules above,
        # so `_report`'s own vacuous-truth branch (score 1.0 when total == 0)
        # is the right answer here, unlike `diastic`'s deliberate departure
        # from it for a selection that is supposed to select something.
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={"words": float(len(spans)), "steps": float(max(len(spans) - 1, 0))},
        )

    def apply(
        self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: object
    ) -> str:
        """Search the lexicon for the shortest ladder from `text` to `target`.

        Breadth-first, not depth-first: a depth-first walk of a fifty-thousand
        word lexicon can wander indefinitely without ever backtracking out of
        an unproductive branch, where breadth-first guarantees both that the
        ladder returned is the shortest one and that the search terminates.

        Neighbours of a word are generated by substitution — every other
        letter at every position — and tested with `pack.is_word` rather than
        by scanning the lexicon for words of the target's length: each test is
        one dictionary lookup, so expanding a word never costs more than
        `len(word) * 25` lookups regardless of how large the lexicon is. This
        also restricts the search to words of the right length for free, since
        a substitution can never change a word's length.
        """
        from denckring.lang import get_pack

        pack = get_pack(lang)
        require_capability(pack, WORDS, self.id)
        parsed = self.parse_params(params)
        if not parsed.target:
            raise InvalidParams(self.id, "target is required: apply(start_word, target=end_word)")

        start = text.strip().lower()
        target = parsed.target.strip().lower()
        if not start.isalpha() or not target.isalpha():
            raise NoCandidateWord(
                self.id,
                "both the start word and target must be single alphabetic "
                "words — try one word each, or check a ladder instead of "
                "generating one",
            )
        if len(start) != len(target):
            raise NoCandidateWord(
                self.id,
                f"{start!r} and {target!r} are different lengths "
                f"({len(start)} vs {len(target)}); a ladder needs the same "
                "length word throughout",
            )
        if not pack.is_word(start) or not pack.is_word(target):
            raise NoCandidateWord(
                self.id,
                f"{start!r} and {target!r} must both be words the lexicon knows",
            )

        ladder, gave_up_on_breadth = _search_ladder(start, target, pack)
        if ladder is None:
            if gave_up_on_breadth:
                raise NoCandidateWord(
                    self.id,
                    f"the search gave up after visiting {MAX_EXPLORED} words "
                    f"without finding a path from {start!r} to {target!r} — "
                    "the connected component here is larger than this search "
                    "chases, not necessarily empty; check a ladder instead of "
                    "generating one",
                )
            raise NoCandidateWord(
                self.id,
                f"no ladder connects {start!r} to {target!r} within "
                f"{MAX_LADDER_WORDS} words — try a shorter hop, or check a "
                "ladder instead of generating one",
            )
        return " ".join(ladder)


@lru_cache(maxsize=4096)
def _substitutions(word: str) -> tuple[str, ...]:
    """Every one-letter substitution of `word`.

    Keyed on the word itself, not on a `LanguagePack` instance: this is pure
    string combinatorics, the same for any pack that might ask, so caching it
    by the word carries no risk of pinning a discarded pack in memory the way
    keying on the pack would. `denckring_en_data` caches its own loaders
    (`known_words`, `variants`, ...) the same way — by what they compute,
    never by the identity of whoever is asking.
    """
    candidates = []
    for position in range(len(word)):
        for letter in string.ascii_lowercase:
            if letter == word[position]:
                continue
            candidates.append(word[:position] + letter + word[position + 1 :])
    return tuple(candidates)


def _search_ladder(start: str, target: str, pack: LanguagePack) -> tuple[list[str] | None, bool]:
    """The shortest word-to-word ladder, or `None` within the search's bounds.

    Breadth-first: `frontier` is a FIFO queue, so words are dequeued in order
    of their distance from `start`, and the first time `target` is discovered
    is necessarily by way of a shortest path. `parents` doubles as the visited
    set — a word is recorded the moment it is first reached — so nothing is
    ever queued twice.

    Returns the ladder alongside a flag distinguishing *why* it is `None`:
    `True` means the search gave up on breadth, hitting `MAX_EXPLORED` before
    the frontier ran out; `False` means the frontier ran out on its own,
    within `MAX_LADDER_WORDS` of depth, having genuinely found nothing.
    `apply` uses this to tell a caller "the search gave up" from "no path
    exists this short" rather than blaming both on the same bound.
    """
    if start == target:
        return [start], False
    parents: dict[str, str] = {start: start}
    frontier: deque[tuple[str, int]] = deque([(start, 1)])
    explored = 0
    while frontier:
        word, depth = frontier.popleft()
        if depth >= MAX_LADDER_WORDS:
            continue
        for candidate in _substitutions(word):
            if candidate in parents or not pack.is_word(candidate):
                continue
            parents[candidate] = word
            if candidate == target:
                return _reconstruct(parents, target), False
            explored += 1
            if explored >= MAX_EXPLORED:
                return None, True
            frontier.append((candidate, depth + 1))
    return None, False


def _reconstruct(parents: dict[str, str], target: str) -> list[str]:
    path = [target]
    while parents[path[-1]] != path[-1]:
        path.append(parents[path[-1]])
    path.reverse()
    return path
