"""Proteus verse — a line whose words permute into many metrically valid variants.

Bauhusius's single hexameter to the Virgin is the case the whole tradition argues
over: how many of its 40,320 orderings still scan? Puteanus printed 1,022 in 1617,
Prestet 2,196 in 1675, Wallis 3,096, Leibniz 2,580, Bernoulli 3,312. They disagree
because they scanned by different rules, not because any of them counted badly, and
that is why this row takes its ruleset as parameters and reports the count as a
metric rather than pinning a number. Knuth tells the history in TAOCP §7.2.1.7.

**Not a prosody library.** The scansion is `denckring.core.prosody`'s, unchanged:
`word_stress` gives each word every reading its pack knows, `?` matches either beat,
and an unknown word constrains length without constraining stress. What this module
adds is the permutation search, and the search never learns what language it is in.

**The factorial is guarded by counting rather than enumerating.** Nine words is
362,880 orderings and the hexameter is thirty-two readings, so scanning each ordering
against each pattern is eleven million scans for one call. Instead the count comes
from a walk over (which words are placed, how many syllables they fill), which is at
most 2^n * (pattern length + 1) states — 9,216 for a nine-word hexameter, and most of
them unreachable. `produce` reconstructs orderings from the same walk, stopping at the
caller's limit.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field

from denckring.core.base import ApplyParams, ConstructiveProcedure, plain
from denckring.core.errors import InputTooLong
from denckring.core.prosody import word_stress
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.dactylic_hexameter import PATTERNS as HEXAMETER

#: The measures a line can be asked to hold under permutation, as sets of
#: acceptable stress readings. Named rather than free-form because the historical
#: question is always "under which ruleset", and a name is what a caller can
#: report alongside the count. Each value is what the row of the same name in
#: this catalogue already scans against, so a proteus count and that row's
#: verdict cannot drift apart.
METRES: dict[str, list[str]] = {
    "hexameter": HEXAMETER,
    "iambic_pentameter": ["01" * 5],
    "iambic_tetrameter": ["01" * 4],
    "trochaic_tetrameter": ["10" * 4],
}

#: Above this many words the search is refused rather than run. Nine is the
#: handover's figure and it is the right shape of limit: the state space is
#: exponential in the word count, so the cost of one more word is not a constant.
DEFAULT_MAX_WORDS = 9


def _fits(form: str, wanted: str) -> bool:
    """`?` means "either" on both sides, exactly as in `core.prosody`."""
    return len(form) == len(wanted) and all(
        want == "?" or mark in ("?", want) for mark, want in zip(form, wanted, strict=True)
    )


def _lengths(forms: list[str], pattern: str, position: int) -> list[int]:
    """The syllable counts at which this word can start at `position`.

    Lengths and not forms: two readings of the same length that both fit put the
    word in the same place in the same ordering, and counting them twice would
    inflate the total by an artefact of how the dictionary is written rather than
    by anything about the verse.
    """
    found = []
    for form in forms:
        if len(form) in found or position + len(form) > len(pattern):
            continue
        if _fits(form, pattern[position : position + len(form)]):
            found.append(len(form))
    return found


def _count(forms: tuple[tuple[str, ...], ...], pattern: str) -> int:
    """How many orderings of these words fill this pattern.

    A walk over `(placed, syllables so far)`. Two orderings reaching the same
    state are interchangeable from there on, which is what collapses the
    factorial into something bounded by 2^n.
    """
    states: dict[tuple[int, int], int] = {(0, 0): 1}
    full = (1 << len(forms)) - 1
    target = len(pattern)
    for _ in forms:
        following: dict[tuple[int, int], int] = {}
        for (placed, position), ways in states.items():
            for index, word_forms in enumerate(forms):
                bit = 1 << index
                if placed & bit:
                    continue
                for length in _lengths(list(word_forms), pattern, position):
                    key = (placed | bit, position + length)
                    following[key] = following.get(key, 0) + ways
        states = following
    return states.get((full, target), 0)


def _orderings(
    forms: tuple[tuple[str, ...], ...], pattern: str, limit: int
) -> list[tuple[int, ...]]:
    """Up to `limit` orderings that fill the pattern, as word-index tuples.

    Depth-first rather than the counting walk, because a caller asking for texts
    wants whole orderings and the counting walk deliberately forgets which words
    reached a state. Bounded by `limit`, so the exponential is never entered any
    further than the caller asked for.
    """
    found: list[tuple[int, ...]] = []

    def walk(placed: int, position: int, order: list[int]) -> None:
        if len(found) >= limit:
            return
        if position == len(pattern):
            if placed == (1 << len(forms)) - 1:
                found.append(tuple(order))
            return
        for index, word_forms in enumerate(forms):
            bit = 1 << index
            if placed & bit:
                continue
            for length in _lengths(list(word_forms), pattern, position):
                order.append(index)
                walk(placed | bit, position + length, order)
                order.pop()
                if len(found) >= limit:
                    return

    walk(0, 0, [])
    return found


@lru_cache(maxsize=256)
def _readings(
    forms: tuple[tuple[str, ...], ...], patterns: tuple[str, ...]
) -> tuple[int, tuple[str, ...]]:
    """The total across every acceptable pattern, and the patterns that admit any.

    Cached because `check` and `produce` ask the same question of the same line,
    and because the eval harness asks it repeatedly of the fixtures.
    """
    total = 0
    admitting = []
    for pattern in patterns:
        count = _count(forms, pattern)
        if count:
            total += count
            admitting.append(pattern)
    return total, tuple(admitting)


class ProteusVerseParams(BaseModel):
    metre: str = Field(
        default="hexameter",
        description=f"Which measure the permutations must hold: {', '.join(METRES)}.",
    )
    minimum: int = Field(
        default=2,
        ge=1,
        description="How many valid orderings the line must admit, itself included.",
    )
    max_words: int = Field(
        default=DEFAULT_MAX_WORDS,
        ge=1,
        description="Refuse a line longer than this rather than search it.",
    )


class ProteusVerseApplyParams(ProteusVerseParams, ApplyParams):
    pass


@register
class ProteusVerse(ConstructiveProcedure[ProteusVerseParams, ProteusVerseApplyParams]):
    """One line, scanned in every order its words can take.

    Two things have to hold and they are reported separately, because a writer can
    fix them separately: the line as written must scan, and its words must admit at
    least `minimum` orderings that do. A line satisfying the second and not the
    first is a proteus verse someone has mis-transcribed.
    """

    id = "proteus_verse"

    @classmethod
    def params_model(cls) -> type[ProteusVerseParams]:
        return ProteusVerseParams

    @classmethod
    def apply_params_model(cls) -> type[ProteusVerseApplyParams]:
        return ProteusVerseApplyParams

    def _read(
        self, text: str, pack: LanguagePack, params: ProteusVerseParams
    ) -> tuple[list[str], tuple[tuple[str, ...], ...], tuple[str, ...], int]:
        """The words, their readings, the metre, and how many were guessed."""
        if params.metre not in METRES:
            # Through the params model would be a Literal, which would freeze the
            # table into the type; the table is data this row expects to grow.
            from denckring.core.errors import InvalidParams

            raise InvalidParams(
                self.id, f"unknown metre {params.metre!r}; this row scans {sorted(METRES)}"
            )
        words = pack.tokenize(text)
        if len(words) > params.max_words:
            raise InputTooLong(self.id, len(words), params.max_words, "words")
        forms = []
        estimated = 0
        for word in words:
            readings, exact = word_stress(word, pack)
            if not exact:
                estimated += 1
            forms.append(tuple(readings))
        return words, tuple(forms), tuple(METRES[params.metre]), estimated

    def _check(self, text: str, pack: LanguagePack, params: ProteusVerseParams) -> Report:
        lines = line_spans(text)
        if len(lines) != 1:
            return self._report(
                good=0,
                total=1,
                violations=[
                    Violation(
                        rule="wrong_line_count",
                        offset=None,
                        found=f"{len(lines)} lines",
                        expected="1 line",
                    )
                ],
                metrics={"variants": 0.0, "words": 0.0, "estimated_words": 0.0},
            )

        words, forms, patterns, estimated = self._read(text, pack, params)
        total, _ = _readings(forms, patterns)

        violations: list[Violation] = []
        good = 0
        # Two checks, so two of two. Scoring them separately is what lets a line
        # that permutes well but is written in an order that does not scan land
        # at 0.5 rather than at 0.
        if self._scans(forms, patterns):
            good += 1
        else:
            violations.append(
                Violation(
                    rule="does_not_scan",
                    offset=0,
                    found=" ".join(f[0] for f in forms if f),
                    expected=f"the {params.metre}",
                )
            )
        if total >= params.minimum:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="too_few_variants",
                    offset=0,
                    found=f"{total} orderings scan",
                    expected=f"at least {params.minimum}",
                )
            )
        return self._report(
            good=good,
            total=2,
            violations=violations,
            metrics={
                "variants": float(total),
                "words": float(len(words)),
                "estimated_words": float(estimated),
            },
        )

    def _scans(self, forms: tuple[tuple[str, ...], ...], patterns: tuple[str, ...]) -> bool:
        """Whether the words *in the order given* fit any acceptable pattern.

        A set of reachable positions rather than a running total: a word with two
        readings of different lengths branches, and taking the first that fits
        would report a line as unscannable because an earlier word was read long
        when reading it short would have worked.
        """
        for pattern in patterns:
            positions = {0}
            for word_forms in forms:
                positions = {
                    position + length
                    for position in positions
                    for length in _lengths(list(word_forms), pattern, position)
                }
                if not positions:
                    break
            if len(pattern) in positions:
                return True
        return False

    def _produce(self, text: str, pack: LanguagePack, params: ProteusVerseApplyParams) -> Produced:
        words, forms, patterns, _ = self._read(text, pack, params)
        _, admitting = _readings(forms, patterns)
        seen: dict[str, None] = {}
        for pattern in admitting:
            # One more than asked for, because the line as written is usually
            # among them and the spine drops it as degenerate.
            for order in _orderings(forms, pattern, params.max_results + 1):
                seen.setdefault(" ".join(words[index] for index in order))
            if len(seen) > params.max_results:
                break
        return plain(seen)
