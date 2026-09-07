"""Syllable count — each line matches a prescribed number of syllables."""

from __future__ import annotations

from typing import NamedTuple

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
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
            evidence.append(
                Evidence(
                    subject=subject,
                    scope=scope,
                    # The pack measures within the line it was handed; the offset
                    # a caller can use is into the whole text.
                    offset=None if at is None else offset + at,
                    value=f"{count} syllables",
                    basis="dictionary" if exact else "estimated",
                )
            )
    return evidence


def pattern_result(text: str, pack: LanguagePack, pattern: list[int]) -> PatternResult:
    """Compare each line's syllables against the expected pattern."""
    measured = line_syllables(text, pack)
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
        offset, total, _ = measured[index]
        if total == expected:
            matched += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_syllable_count",
                    offset=offset,
                    found=f"{total} syllables",
                    expected=f"{expected} syllables",
                )
            )
    for offset, total, _ in measured[len(pattern) :]:
        violations.append(
            Violation(rule="extra_line", offset=offset, found=f"{total} syllables", expected="")
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
    pattern: list[int] = Field(description="Syllables required, line by line.")


@register
class SyllableCount(BaseProcedure[SyllableCountParams]):
    """The general case the fixed syllabic forms delegate to."""

    id = "syllable_count"

    @classmethod
    def params_model(cls) -> type[SyllableCountParams]:
        return SyllableCountParams

    def _check(self, text: str, pack: LanguagePack, params: SyllableCountParams) -> Report:
        return self._report(**pattern_result(text, pack, params.pattern)._asdict())
