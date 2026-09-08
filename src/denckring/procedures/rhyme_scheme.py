"""Rhyme scheme — line endings follow a prescribed pattern."""

from __future__ import annotations

from typing import NamedTuple

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.prosody import UnknownRhyme, metre_violations, scheme_violations
from denckring.core.protocol import Evidence, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans


class FormResult(NamedTuple):
    """A fixed form's outcome. Named for the same reason `MetreResult` is:
    the estimated-word count from the metre branch must reach every caller.
    """

    violations: list[Violation]
    good: int
    total: int
    estimated: int
    #: Gathered from whichever parts ran. A form is assembled from a scheme, a
    #: metre, refrains and a line count, and the first two each have an account
    #: of what they read; this is where the assembled form's account lives so
    #: that eighteen procedures do not each have to collect it.
    evidence: tuple[Evidence, ...] = ()


class RhymeSchemeParams(RhymeParams):
    scheme: str = Field(description="Rhyme pattern such as ABAB.")
    allow_identical: bool = Field(
        default=False,
        description="Permit a word to rhyme with itself, as French rime riche does.",
    )

    @field_validator("scheme")
    @classmethod
    def _has_letters(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("scheme must contain at least one letter")
        return value


def form_report(
    text: str,
    pack: LanguagePack,
    *,
    scheme: str | None = None,
    metre: str | None = None,
    refrains: list[tuple[int, int]] | None = None,
    allow_identical: bool = False,
    lines: int | None = None,
    unknown_rhyme: UnknownRhyme = "undecidable",
) -> FormResult:
    """Check any combination of rhyme scheme, metre, refrain lines and line count.

    The fixed forms are assembled from these parts rather than
    reimplementing them, so a sonnet is a rhyme scheme plus a metre plus a
    line count and says so.

    As `stanza_violations` does for the same rule: a text of the wrong length
    reports `wrong_line_count` and stops — scanning line three against line
    four's pattern would bury the real fault under false ones. So when `lines`
    is given and the count is wrong, this returns immediately without running
    the scheme, metre or refrain checks.
    """
    violations: list[Violation] = []
    good = 0
    total = 0
    estimated = 0
    evidence: list[Evidence] = []
    if lines is not None:
        n = len(line_spans(text))
        if n != lines:
            return FormResult(
                [
                    Violation(
                        rule="wrong_line_count",
                        offset=None,
                        found=f"{n} lines",
                        expected=f"{lines} lines",
                    )
                ],
                0,
                1,
                0,
            )
        total += 1
        good += 1
    if scheme is not None:
        rhyme = scheme_violations(
            text,
            pack,
            scheme,
            allow_identical=allow_identical,
            unknown_rhyme=unknown_rhyme,
        )
        violations += rhyme.violations
        good += rhyme.good
        total += rhyme.total
        estimated += rhyme.estimated
        evidence += rhyme.evidence
    if metre is not None:
        for offset, line in line_spans(text):
            result = metre_violations(line, pack, metre, offset)
            violations += result.violations
            good += result.good
            total += result.total
            estimated += result.estimated
            evidence += result.evidence
    if refrains is not None:
        stripped_lines = [line.strip().casefold() for _, line in line_spans(text)]
        for first, repeat in refrains:
            total += 1
            if (
                first < len(stripped_lines)
                and repeat < len(stripped_lines)
                and stripped_lines[first] == stripped_lines[repeat]
            ):
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="broken_refrain",
                        offset=None,
                        found=stripped_lines[repeat] if repeat < len(stripped_lines) else "",
                        expected=stripped_lines[first]
                        if first < len(stripped_lines)
                        else f"line {first + 1}",
                    )
                )
    return FormResult(violations, good, max(total, 1), estimated, tuple(evidence))


@register
class RhymeScheme(BaseProcedure[RhymeSchemeParams]):
    """Lines sharing a letter must rhyme; lines with different letters must not."""

    id = "rhyme_scheme"

    @classmethod
    def params_model(cls) -> type[RhymeSchemeParams]:
        return RhymeSchemeParams

    def _check(self, text: str, pack: LanguagePack, params: RhymeSchemeParams) -> Report:
        result = form_report(
            text,
            pack,
            scheme=params.scheme,
            allow_identical=params.allow_identical,
            unknown_rhyme=params.unknown_rhyme,
        )
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            evidence=list(result.evidence),
            metrics={
                "pairs_checked": float(result.total),
                "estimated_words": float(result.estimated),
            },
        )
