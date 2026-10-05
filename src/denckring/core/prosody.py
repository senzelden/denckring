"""Shared machinery for the rhyme and metre procedures."""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import Literal, NamedTuple

from denckring.core.errors import MissingCapability
from denckring.core.protocol import Evidence, LanguagePack, Violation
from denckring.core.text import line_spans, split_elision
from denckring.lang.base import PHONEMES, STRESS

#: `?` matches either, so a monosyllable takes whatever stress the line needs.
FREE = "?"


#: Above this many pronunciation combinations, only the first form of each word
#: is tried. Real lines are far below it; the cap exists so a pathological line
#: cannot hang the checker.
MAX_COMBINATIONS = 4096

#: What a line ending the pronouncing dictionary does not carry means for a
#: rhyme. See `scheme_violations` for why this is a parameter and not a constant.
UnknownRhyme = Literal["undecidable", "free", "strict"]


class SchemeResult(NamedTuple):
    """A rhyme scheme's outcome.

    Carries `estimated` for the same reason `MetreResult` does: a report drawn
    from partial knowledge must say so, or a caller reads a score computed over
    fewer pairs than it thinks.
    """

    violations: list[Violation]
    good: int
    total: int
    estimated: int
    #: The rhyme key each line ending was read as, and whether the dictionary
    #: carried it. The same improvement on `estimated` that `MetreResult` gained:
    #: a writer told two lines do not rhyme can act on the keys they were read
    #: with, and cannot act on a count.
    evidence: tuple[Evidence, ...] = ()


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

    `evidence` is the fifth, and it is the same improvement `estimated` was: that
    field says how many words were guessed and this one says which, with the
    stress the scan actually read them as. A writer told a line does not scan can
    do nothing with a count and can act on `evening (10)`.

    A tuple with an empty default rather than a list, because a mutable default
    on a `NamedTuple` is shared by every instance that omits it.
    """

    violations: list[Violation]
    good: int
    total: int
    estimated: int
    evidence: tuple[Evidence, ...] = ()


def metre_violations(line: str, pack: LanguagePack, pattern: str, offset: int) -> MetreResult:
    """Check a line against a stress pattern, treating `?` as satisfiable.

    Because each free syllable is independent of every other, this is a linear
    scan rather than a search: a fixed syllable landing on the wrong beat is the
    only way to fail. The violation names the word rather than the syllable
    index, because the word is what a writer can act on.
    """
    # `word_spans` rather than `tokenize`, which is defined as this without the
    # offsets: the evidence has to be able to point at the word it is about.
    spans = pack.word_spans(line)
    combinations = 1
    words: list[tuple[str, list[str]]] = []
    estimated = 0
    evidence: list[Evidence] = []
    for at, word in spans:
        forms, exact = word_stress(word, pack)
        if not exact:
            estimated += 1
        combinations *= max(len(forms), 1)
        tried = forms if combinations <= MAX_COMBINATIONS else forms[:1]
        evidence.append(
            Evidence(
                subject=word,
                offset=offset + at,
                # Every form the scan could take, first first. A fitted line replaces
                # it below with the one form the scan read; a failed line keeps them
                # all, since the violations name the first and the scan tried the rest
                # (ADR 0054).
                value="/".join(tried),
                # `ambiguous` when the scan was free to take another listed form,
                # and not when the cap held it to the first (ADR 0054).
                basis="estimated" if not exact else "ambiguous" if len(tried) > 1 else "dictionary",
            )
        )
        words.append((word, tried))

    fitted = _scan(words, pattern, 0, 0)
    if fitted is not None:
        # The stress the verdict rests on, as `MetreResult` promises: `every` as `10`
        # in a line that scans only on that reading, not its first form `100`.
        read = tuple(
            entry.model_copy(update={"value": form})
            for entry, form in zip(evidence, fitted, strict=True)
        )
        return MetreResult([], len(words), max(len(words), 1), estimated, read)

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
        return MetreResult(violations, 0, 1, estimated, tuple(evidence))

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
    return MetreResult(violations, matched, max(len(words), 1), estimated, tuple(evidence))


def feet(units: Sequence[Sequence[str]]) -> list[str]:
    """Every pattern a line of substitutable feet can take.

    Classical metre substitutes: a dactyl may be a spondee, so a hexameter is
    thirty-two readings rather than one. `feet` enumerates them, and the set is
    bounded by construction — no metre in the catalogue has more than six feet.
    """
    return ["".join(combination) for combination in itertools.product(*units)]


def with_feminine(pattern: str, allowed: bool) -> list[str]:
    """The readings a line may take, with or without a feminine ending.

    A klingende Kadenz adds one unstressed syllable after the last stress, so it
    is an extra member of the option set `line_metre` already scans — the same
    shape `feet` produces for a substitutable dactyl, and for the same reason.
    It cannot be a longer fixed pattern: Gryphius rhymes feminine `Erden` against
    masculine `ein` inside one sonnet, so both readings must be live at once
    (ADR 0040 D1).
    """
    return [pattern, pattern + "0"] if allowed else [pattern]


def line_metre(line: str, pack: LanguagePack, options: Sequence[str], offset: int) -> MetreResult:
    """Scan a line against several acceptable readings, reporting the closest.

    A substitutable foot makes a metre a set rather than a single pattern, so
    the line satisfies if it fits any member. When none fits, the violations
    come from the candidate with the highest `good` count — the writer is told
    about one scansion rather than thirty-two. `good` is not normalised across
    candidates of differing pattern length, so this is a preference among the
    candidates tried, not a guarantee of the best possible reading.

    When the losing candidate's failure is `wrong_line_length`, its `expected`
    names only that one pattern's length — true of the candidate but not of
    the call, which offered every length in `options`. `pattern_result` in
    `syllable_count.py` already widens the same message for a feminine ending
    (`extra`); this reads every option's length instead of one `extra`, so it
    covers a substitutable metre's whole spread, not just two. A single option
    leaves the message untouched — ADR 0040 D6 requires the unwidened text to
    stay byte-identical.
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
    if len(best.violations) == 1 and best.violations[0].rule == "wrong_line_length":
        lengths = sorted({len(pattern) for pattern in options})
        if len(lengths) > 1:
            heads = ", ".join(str(n) for n in lengths[:-1])
            expected = f"{heads} or {lengths[-1]} syllables"
            widened = best.violations[0].model_copy(update={"expected": expected})
            best = best._replace(violations=[widened])
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
    evidence: list[Evidence] = []
    for (offset, line), options in zip(lines, patterns, strict=True):
        result = line_metre(line, pack, options, offset)
        violations += result.violations
        good += result.good
        total += result.total
        estimated += result.estimated
        evidence += result.evidence
    return MetreResult(violations, good, max(total, 1), estimated, tuple(evidence))


def repeat_to(pattern_unit: str, feet: int) -> str:
    """`01` at five feet is `0101010101`."""
    return pattern_unit * feet


def word_rhyme_keys(word: str, pack: LanguagePack) -> tuple[frozenset[str], bool]:
    """Every rhyme key a word can take, and whether they are known.

    The mirror of `word_stress`, for the same reason: a pronouncing dictionary
    does not carry every word, and an unknown word is a normal event in verse
    rather than an exceptional one. The dictionary raises `MissingCapability`
    for a word it lacks — naming a capability the pack does provide — so that
    case is caught here and returned as an empty key set the caller can
    recognise, rather than aborting the whole check.

    A pack that genuinely lacks `phonemes` still raises, which is what the
    exception is for. What an empty key set *means* for a rhyme is the caller's
    decision, not this function's — see `scheme_violations`.
    """
    if PHONEMES not in pack.capabilities:
        raise MissingCapability(f"<word {word!r}>", pack.lang, PHONEMES)
    try:
        return frozenset(pack.rhyme_keys(word)), True
    except MissingCapability:
        return frozenset(), False


def rhyme_keys(text: str, pack: LanguagePack) -> list[tuple[int, str, frozenset[str], bool]]:
    """Per line: offset, the final word, its rhyme keys, and whether they are known.

    Two lines may rhyme when their key sets intersect — the same satisfiability
    reading applied to pronunciation that metre applies to stress — and must when
    every pair of keys matches or the two sets are the same (`may_rhyme`,
    `must_rhyme`, ADR 0057). The fourth
    element distinguishes "this word rhymes with nothing here" from "the
    dictionary does not carry this word", which are different claims.
    """
    keys: list[tuple[int, str, frozenset[str], bool]] = []
    for offset, line in line_spans(text):
        words = pack.tokenize(line)
        if not words:
            continue
        found, exact = word_rhyme_keys(words[-1], pack)
        keys.append((offset, words[-1], found, exact))
    return keys


def may_rhyme(first: frozenset[str], second: frozenset[str]) -> bool:
    """Whether some reading of each word makes the two rhyme: any pair of keys matches.

    What a pair the scheme wants to rhyme needs, the satisfiability reading ADR 0014
    gave metre.
    """
    return bool(first & second)


def must_rhyme(first: frozenset[str], second: frozenset[str]) -> bool:
    """Whether the two rhyme against a scheme that keeps them apart (ADR 0057).

    Two ways, either of which fails the pair. Every pairing of the two words' readings
    rhymes, so no choice keeps them apart. Or the two have the same set of keys, so
    whichever accent a reader has, it reads both words alike: `fog` and `bog` are each
    `AA1 G` or `AO1 G`, and a speaker who says one way says both. Reading one word in
    one accent and the other in another models no speaker. A pair whose keys overlap
    without being the same set passes, because some reader keeps it apart: `gone` is
    `AO1 N`, and `on` may be `AA1 N`.

    Keys are compared for equality, so the first way is a case of the second: both
    words have the same single key. Decided per pair, like `may_rhyme`, and not for
    the scheme jointly: one word's variant may keep one pair apart while its other
    variant makes a second pair rhyme. An empty set, a word the dictionary lacks,
    rhymes with nothing.
    """
    every_pairing = all(a == b for a in first for b in second)
    return bool(first) and bool(second) and (every_pairing or first == second)


def rhyme_evidence(
    keys: Sequence[tuple[int, str, frozenset[str], bool]],
) -> tuple[Evidence, ...]:
    """The line endings a scheme was judged on, as evidence.

    Sorted so the account is stable between runs: `rhyme_keys` are a `frozenset`
    and its iteration order is not a fact about the word.
    """
    return tuple(
        Evidence(
            subject=word,
            # No offset. `rhyme_keys` carries the *line's* offset, and the subject
            # here is the word that line ends on — pairing the two would hand a
            # reader a position that does not point at the thing it names, which
            # is worse than declining to give one. The word is findable as the
            # line's ending; `Violation.offset` still locates the line.
            offset=None,
            value="/".join(sorted(found)) if found else "no rhyme key",
            # Any key may make the pair rhyme, so several is a verdict that may rest
            # on a variant (ADR 0054).
            basis="estimated" if not exact else "ambiguous" if len(found) > 1 else "dictionary",
        )
        for _, word, found, exact in keys
    )


def scheme_violations(
    text: str,
    pack: LanguagePack,
    scheme: str,
    *,
    allow_identical: bool,
    unknown_rhyme: UnknownRhyme = "undecidable",
) -> SchemeResult:
    """Check line endings against a rhyme scheme such as `ABAB`.

    Both directions matter: lines sharing a letter must rhyme, and lines with
    different letters must not. A poem in which everything rhymes does not
    satisfy `ABAB`. Each direction reads a word's several keys in the writer's
    favour, as far as one reader could: a wanted pair rhymes when some reading of
    each does, and an unwanted pair fails when every reading of each does or when
    the two have the same keys, so that every reader rhymes them (ADR 0057).

    `unknown_rhyme` decides what a line ending the pronouncing dictionary does
    not carry means, which is an editorial question rather than a library
    constant — the argument ADR 0009 makes for diacritic folding:

    - `undecidable` leaves the pair unscored and counts the word in `estimated`,
      claiming neither that it rhymes nor that it does not;
    - `free` lets it satisfy whatever the scheme asks, the reading `word_stress`
      takes for an unscannable word;
    - `strict` fails the pair, naming the word the dictionary lacks.

    Under `undecidable` a text whose every pair is unknown would score nothing
    over nothing, which `_report` reads as vacuously satisfied. That case is
    reported as a single `rhyme_undecidable` violation instead: a partial
    verdict is honest, an empty one is not.
    """
    keys = rhyme_keys(text, pack)
    letters = [ch.upper() for ch in scheme if ch.isalpha()]
    violations: list[Violation] = []
    estimated = sum(1 for key in keys if not key[3])
    if len(keys) != len(letters):
        violations.append(
            Violation(
                rule="wrong_line_count",
                offset=None,
                found=f"{len(keys)} lines",
                expected=f"{len(letters)} lines",
            )
        )
        return SchemeResult(violations, 0, 1, estimated, rhyme_evidence(keys))

    checks = 0
    matched = 0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if not (keys[i][3] and keys[j][3]):
                if unknown_rhyme == "undecidable":
                    continue
                checks += 1
                if unknown_rhyme == "free":
                    matched += 1
                else:
                    unknown = keys[j][1] if not keys[j][3] else keys[i][1]
                    violations.append(
                        Violation(
                            rule="unknown_rhyme",
                            offset=keys[j][0],
                            found=unknown,
                            expected="a word the pronouncing dictionary carries",
                        )
                    )
                continue
            checks += 1
            should_rhyme = letters[i] == letters[j]
            # A wanted rhyme needs one pairing of readings to match. An unwanted one
            # fails when every pairing does, or the key sets are the same (ADR 0057).
            does_rhyme = (may_rhyme if should_rhyme else must_rhyme)(keys[i][2], keys[j][2])
            # Compared past any leading elided proclitic, or `l'amour` and
            # `amour` — the same rhyme word — read as two different ones:
            # `identical_rhyme` exists to catch French rime riche's commonest
            # orthographic shape, and a `l'` in front of it defeated the
            # check that `hemeling`'s own `allow_identical` names it for.
            identical = (
                split_elision(keys[i][1])[1].casefold() == split_elision(keys[j][1])[1].casefold()
            )
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
    if unknown_rhyme == "undecidable" and checks == 0 and len(keys) > 1:
        violations.append(
            Violation(
                rule="rhyme_undecidable",
                offset=None,
                found=f"{estimated} line endings the dictionary does not carry",
                expected="at least one pair this install can decide",
            )
        )
        return SchemeResult(violations, 0, 1, estimated, rhyme_evidence(keys))
    return SchemeResult(violations, matched, max(checks, 1), estimated, rhyme_evidence(keys))
