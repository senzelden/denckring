"""Shared machinery for the rhyme and metre procedures."""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import NamedTuple

from denckring.core.errors import MissingCapability
from denckring.core.protocol import LanguagePack, Violation
from denckring.core.text import line_spans
from denckring.lang.base import STRESS

#: `?` matches either, so a monosyllable takes whatever stress the line needs.
FREE = "?"


#: Above this many pronunciation combinations, only the first form of each word
#: is tried. Real lines are far below it; the cap exists so a pathological line
#: cannot hang the checker.
MAX_COMBINATIONS = 4096


def line_stress(line: str, pack: LanguagePack) -> list[tuple[str, str]]:
    """Each word of the line with its first stress pattern."""
    return [(word, pack.stress_pattern(word)) for word in pack.tokenize(line)]


def _fits(stress: str, wanted: str) -> bool:
    """`?` means "either" on both sides.

    On the word side it is a monosyllable taking whatever beat the line needs.
    On the pattern side it is the classical anceps — the position that may be
    long or short — which sapphics and alcaics both have.
    """
    return len(stress) == len(wanted) and all(
        want == FREE or mark in (FREE, want) for mark, want in zip(stress, wanted, strict=True)
    )


def word_stress(word: str, pack: LanguagePack) -> tuple[list[str], bool]:
    """Every stress pattern a word can take, and whether they are known.

    Mirrors `pack.syllable_count`'s `(value, exact)` contract, for the same
    reason: a pronouncing dictionary does not carry every word, and an unknown
    word is a normal event in verse rather than an exceptional one. The
    dictionary raises `MissingCapability` for a word it lacks — naming a
    capability the pack does provide — so that case is caught here and turned
    into a scan that measures the word's length while constraining no beat.

    A pack that genuinely lacks `stress` still raises, which is what the
    exception is for.
    """
    if STRESS not in pack.capabilities:
        raise MissingCapability(f"<word {word!r}>", pack.lang, STRESS)
    try:
        return pack.stress_patterns(word), True
    except MissingCapability:
        count, _ = pack.syllable_count(word)
        return [FREE * max(count, 1)], False


def _scan(
    words: list[tuple[str, list[str]]], pattern: str, position: int, index: int
) -> list[str] | None:
    """The first combination of pronunciations that fits, or None."""
    if index == len(words):
        return [] if position == len(pattern) else None
    _, forms = words[index]
    for form in forms:
        if position + len(form) > len(pattern):
            continue
        if not _fits(form, pattern[position : position + len(form)]):
            continue
        rest = _scan(words, pattern, position + len(form), index + 1)
        if rest is not None:
            return [form, *rest]
    return None


class MetreResult(NamedTuple):
    """A scan's outcome. Named rather than a bare tuple because it grew a
    fourth field, and `PatternResult` in `syllable_count` sets the precedent.
    """

    violations: list[Violation]
    good: int
    total: int
    estimated: int


def metre_violations(line: str, pack: LanguagePack, pattern: str, offset: int) -> MetreResult:
    """Check a line against a stress pattern, treating `?` as satisfiable.

    Because each free syllable is independent of every other, this is a linear
    scan rather than a search: a fixed syllable landing on the wrong beat is the
    only way to fail. The violation names the word rather than the syllable
    index, because the word is what a writer can act on.
    """
    tokens = pack.tokenize(line)
    combinations = 1
    words: list[tuple[str, list[str]]] = []
    estimated = 0
    for word in tokens:
        forms, exact = word_stress(word, pack)
        if not exact:
            estimated += 1
        combinations *= max(len(forms), 1)
        words.append((word, forms if combinations <= MAX_COMBINATIONS else forms[:1]))

    fitted = _scan(words, pattern, 0, 0)
    if fitted is not None:
        return MetreResult([], len(words), max(len(words), 1), estimated)

    violations: list[Violation] = []
    # No combination fits. Report against the first pronunciation of each word,
    # which is the reading a writer is most likely to have had in mind.
    first = [(word, forms[0]) for word, forms in words]
    actual = "".join(stress for _, stress in first)
    if len(actual) != len(pattern):
        violations.append(
            Violation(
                rule="wrong_line_length",
                offset=offset,
                found=f"{len(actual)} syllables",
                expected=f"{len(pattern)} syllables",
            )
        )
        return MetreResult(violations, 0, 1, estimated)

    matched = 0
    position = 0
    for word, stress in first:
        wanted = pattern[position : position + len(stress)]
        if _fits(stress, wanted):
            matched += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_stress", offset=offset, found=f"{word} ({stress})", expected=wanted
                )
            )
        position += len(stress)
    return MetreResult(violations, matched, max(len(words), 1), estimated)


def feet(units: Sequence[Sequence[str]]) -> list[str]:
    """Every pattern a line of substitutable feet can take.

    Classical metre substitutes: a dactyl may be a spondee, so a hexameter is
    thirty-two readings rather than one. `feet` enumerates them, and the set is
    bounded by construction — no metre in the catalogue has more than six feet.
    """
    return ["".join(combination) for combination in itertools.product(*units)]


def line_metre(line: str, pack: LanguagePack, options: Sequence[str], offset: int) -> MetreResult:
    """Scan a line against several acceptable readings, reporting the closest.

    A substitutable foot makes a metre a set rather than a single pattern, so
    the line satisfies if it fits any member. When none fits, the violations
    come from the candidate with the highest `good` count — the writer is told
    about one scansion rather than thirty-two. `good` is not normalised across
    candidates of differing pattern length, so this is a preference among the
    candidates tried, not a guarantee of the best possible reading.
    """
    best: MetreResult | None = None
    for pattern in options:
        result = metre_violations(line, pack, pattern, offset)
        if not result.violations:
            return result
        if best is None or result.good > best.good:
            best = result
    if best is None:
        raise ValueError("line_metre needs at least one pattern")
    return best


def stanza_violations(
    text: str, pack: LanguagePack, patterns: Sequence[Sequence[str]]
) -> MetreResult:
    """Check a stanza whose lines each have their own metre.

    `patterns[i]` is the set of readings acceptable for line `i`. A stanza of
    the wrong length reports `wrong_line_count` and stops — scanning line three
    against line four's pattern would bury the real fault under false ones.
    """
    lines = line_spans(text)
    if len(lines) != len(patterns):
        return MetreResult(
            [
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected=f"{len(patterns)} lines",
                )
            ],
            0,
            1,
            0,
        )

    violations: list[Violation] = []
    good = 0
    total = 0
    estimated = 0
    for (offset, line), options in zip(lines, patterns, strict=True):
        result = line_metre(line, pack, options, offset)
        violations += result.violations
        good += result.good
        total += result.total
        estimated += result.estimated
    return MetreResult(violations, good, max(total, 1), estimated)


def repeat_to(pattern_unit: str, feet: int) -> str:
    """`01` at five feet is `0101010101`."""
    return pattern_unit * feet


def rhyme_keys(text: str, pack: LanguagePack) -> list[tuple[int, str, frozenset[str]]]:
    """Per line: offset, the final word, and every rhyme key it can take.

    Two lines rhyme when their key sets intersect — the same satisfiability
    reading applied to pronunciation that metre applies to stress.
    """
    keys: list[tuple[int, str, frozenset[str]]] = []
    for offset, line in line_spans(text):
        words = pack.tokenize(line)
        if not words:
            continue
        keys.append((offset, words[-1], frozenset(pack.rhyme_keys(words[-1]))))
    return keys


def scheme_violations(
    text: str, pack: LanguagePack, scheme: str, *, allow_identical: bool
) -> tuple[list[Violation], int, int]:
    """Check line endings against a rhyme scheme such as `ABAB`.

    Both directions matter: lines sharing a letter must rhyme, and lines with
    different letters must not. A poem in which everything rhymes does not
    satisfy `ABAB`.
    """
    keys = rhyme_keys(text, pack)
    letters = [ch.upper() for ch in scheme if ch.isalpha()]
    violations: list[Violation] = []
    if len(keys) != len(letters):
        violations.append(
            Violation(
                rule="wrong_line_count",
                offset=None,
                found=f"{len(keys)} lines",
                expected=f"{len(letters)} lines",
            )
        )
        return violations, 0, 1

    checks = 0
    matched = 0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            checks += 1
            should_rhyme = letters[i] == letters[j]
            does_rhyme = bool(keys[i][2] & keys[j][2])
            identical = keys[i][1].casefold() == keys[j][1].casefold()
            if should_rhyme and identical and not allow_identical:
                violations.append(
                    Violation(
                        rule="identical_rhyme",
                        offset=keys[j][0],
                        found=keys[j][1],
                        expected=f"a word other than {keys[i][1]!r}",
                    )
                )
            elif should_rhyme and not does_rhyme:
                violations.append(
                    Violation(
                        rule="does_not_rhyme",
                        offset=keys[j][0],
                        found=keys[j][1],
                        expected=f"a rhyme for {keys[i][1]!r}",
                    )
                )
            elif not should_rhyme and does_rhyme:
                violations.append(
                    Violation(
                        rule="unwanted_rhyme",
                        offset=keys[j][0],
                        found=keys[j][1],
                        expected=f"a word not rhyming with {keys[i][1]!r}",
                    )
                )
            else:
                matched += 1
    return violations, matched, max(checks, 1)
