"""Shared machinery for the rhyme and metre procedures."""

from __future__ import annotations

from denckring.core.protocol import LanguagePack, Violation
from denckring.core.text import line_spans

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
    return len(stress) == len(wanted) and all(
        mark in (FREE, want) for mark, want in zip(stress, wanted, strict=True)
    )


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


def metre_violations(
    line: str, pack: LanguagePack, pattern: str, offset: int
) -> tuple[list[Violation], int, int]:
    """Check a line against a stress pattern, treating `?` as satisfiable.

    Because each free syllable is independent of every other, this is a linear
    scan rather than a search: a fixed syllable landing on the wrong beat is the
    only way to fail. The violation names the word rather than the syllable
    index, because the word is what a writer can act on.
    """
    tokens = pack.tokenize(line)
    combinations = 1
    words: list[tuple[str, list[str]]] = []
    for word in tokens:
        forms = pack.stress_patterns(word)
        combinations *= max(len(forms), 1)
        words.append((word, forms if combinations <= MAX_COMBINATIONS else forms[:1]))

    fitted = _scan(words, pattern, 0, 0)
    if fitted is not None:
        return [], len(words), max(len(words), 1)

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
        return violations, 0, 1

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
    return violations, matched, max(len(words), 1)


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
