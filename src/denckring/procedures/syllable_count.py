"""Syllable count — each line matches a prescribed number of syllables."""

from __future__ import annotations

from typing import NamedTuple

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.fields import param
from denckring.core.protocol import Evidence, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans


def line_syllables(text: str, pack: LanguagePack) -> list[tuple[int, int, int]]:
    """Per line: offset, syllable total, and how many words were estimated.

    The estimate count is what keeps a heuristic pack honest — every syllabic
    report carries it, and installing `denckring[en]` drives it to zero.

    The counting itself belongs to the pack (spec D3): French cannot be counted
    word by word, and the other two languages must not change to accommodate it.
    """
    measured: list[tuple[int, int, int]] = []
    for offset, line in line_spans(text):
        total, estimated = pack.line_syllables(line)
        measured.append((offset, total, estimated))
    return measured


def word_syllable_counts(word: str, pack: LanguagePack) -> tuple[frozenset[int], bool]:
    """Every count the word's listed pronunciations give, and whether it was looked up.

    Read with `getattr`, as `syllable_evidence` reads its method: `syllable_counts`
    is not on the published protocol, so a pack that predates it answers with its
    one count, as it did before ADR 0054.
    """
    counts = getattr(pack, "syllable_counts", None)
    if counts is None:
        count, exact = pack.syllable_count(word)
        return frozenset({count}), exact
    found: tuple[frozenset[int], bool] = counts(word)
    return found


def line_syllable_counts(text: str, pack: LanguagePack) -> list[tuple[int, frozenset[int], int]]:
    """Per line: offset, every total some choice of pronunciations gives, and estimates.

    What the line-count rows judge since 0.4.0 (ADR 0054): a line meets its count
    when any combination of the words' listed readings does, where `line_syllables`
    sums first readings only. A pack without `line_syllable_counts` gives its one
    total.
    """
    by_line = getattr(pack, "line_syllable_counts", None)
    measured: list[tuple[int, frozenset[int], int]] = []
    for offset, line in line_spans(text):
        if by_line is None:
            total, estimated = pack.line_syllables(line)
            measured.append((offset, frozenset({total}), estimated))
        else:
            totals, estimated = by_line(line)
            measured.append((offset, totals, estimated))
    return measured


def syllables_text(counts: frozenset[int]) -> str:
    """`7 syllables`, or every reading when there are several: `6 or 7 syllables`.

    The format `line_metre` widens a length message to, so a reader meets one
    spelling of "any of these" across the syllabic and metrical rows.
    """
    ordered = sorted(counts)
    if len(ordered) == 1:
        return f"{ordered[0]} syllables"
    heads = ", ".join(str(n) for n in ordered[:-1])
    return f"{heads} or {ordered[-1]} syllables"


class PatternResult(NamedTuple):
    """Exactly the arguments `BaseProcedure._report` takes.

    Returned rather than turned into a Report here, so each procedure builds its
    own and the shared helper never reaches into another object's internals.
    """

    good: int
    total: int
    violations: list[Violation]
    metrics: dict[str, float]
    evidence: list[Evidence]


def syllable_evidence(text: str, pack: LanguagePack) -> list[Evidence]:
    """Which words were counted, how, and which of them were guessed at.

    `metrics["estimated_words"]` says how many were estimated and never which.
    This is the same measurement with the identities kept, so a reader repairing
    a line knows where to look and an auditor knows what the verdict rests on.

    Read with `getattr` so a third-party pack that predates the method reports no
    evidence rather than failing: `LanguagePack` is a published contract, and the
    breakdown is an improvement on the count rather than a replacement for it.
    """
    breakdown = getattr(pack, "syllable_evidence", None)
    if breakdown is None:  # pragma: no cover - every shipped pack has it
        return []
    evidence: list[Evidence] = []
    for offset, line in line_spans(text):
        for subject, scope, at, count, exact in breakdown(line):
            # A word keeps every reading the verdict accepted (ADR 0054); a line
            # scope is the pack's one total and has none to keep.
            counts = word_syllable_counts(subject, pack)[0] if scope == "word" else {count}
            evidence.append(
                Evidence(
                    subject=subject,
                    scope=scope,
                    # The pack measures within the line it was handed; the offset
                    # a caller can use is into the whole text.
                    offset=None if at is None else offset + at,
                    value=syllables_text(frozenset(counts)),
                    basis=(
                        "estimated"
                        if not exact
                        else "ambiguous"
                        if len(counts) > 1
                        else "dictionary"
                    ),
                )
            )
    return evidence


def pattern_result(
    text: str, pack: LanguagePack, pattern: list[int], *, extra: int = 0
) -> PatternResult:
    """Compare each line's syllables against the expected pattern.

    `extra` admits a longer close — one unstressed syllable for a feminine
    ending — as a second acceptable count rather than a different one, so a row
    that permits it still rejects a line two syllables over (ADR 0040 D1).
    """
    measured = line_syllable_counts(text, pack)
    violations: list[Violation] = []
    matched = 0
    for index, expected in enumerate(pattern):
        if index >= len(measured):
            violations.append(
                Violation(
                    rule="missing_line", offset=None, found="", expected=f"{expected} syllables"
                )
            )
            continue
        offset, totals, _ = measured[index]
        # Any reading meets it (ADR 0054), as any scansion does for metre (ADR 0014).
        if expected in totals or (extra and expected + extra in totals):
            matched += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_syllable_count",
                    offset=offset,
                    found=syllables_text(totals),
                    expected=(
                        f"{expected} or {expected + extra} syllables"
                        if extra
                        else f"{expected} syllables"
                    ),
                )
            )
    for offset, totals, _ in measured[len(pattern) :]:
        violations.append(
            Violation(rule="extra_line", offset=offset, found=syllables_text(totals), expected="")
        )
    estimated = sum(estimate for _, _, estimate in measured)
    return PatternResult(
        good=matched,
        total=max(len(pattern), len(measured)),
        violations=violations,
        metrics={"lines": float(len(measured)), "estimated_words": float(estimated)},
        evidence=syllable_evidence(text, pack),
    )


class SyllableCountParams(BaseModel):
    pattern: list[int] = Field(
        description="Syllables required, line by line.",
        json_schema_extra=param("task", examples=[[5, 7, 5], [5, 7, 5, 7, 7]]),
    )


@register
class SyllableCount(BaseProcedure[SyllableCountParams]):
    """The general case the fixed syllabic forms delegate to."""

    id = "syllable_count"
    rules = ("extra_line", "missing_line", "wrong_syllable_count")

    @classmethod
    def params_model(cls) -> type[SyllableCountParams]:
        return SyllableCountParams

    def _check(self, text: str, pack: LanguagePack, params: SyllableCountParams) -> Report:
        return self._report(**pattern_result(text, pack, params.pattern)._asdict())
