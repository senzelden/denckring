"""Rhyme scheme — line endings follow a prescribed pattern."""

from __future__ import annotations

from typing import NamedTuple

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.prosody import metre_violations, scheme_violations
from denckring.core.protocol import LanguagePack, Report, Violation
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


class RhymeSchemeParams(BaseModel):
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
) -> FormResult:
    """Check any combination of rhyme scheme, metre, refrain lines and line count.

    The fixed forms are assembled from these parts rather than
    reimplementing them, so a sonnet is a rhyme scheme plus a metre plus a
    line count and says so.
    """
    violations: list[Violation] = []
    good = 0
    total = 0
    estimated = 0
    if lines is not None:
        total += 1
        n = len(line_spans(text))
        if n == lines:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{n} lines",
                    expected=f"{lines} lines",
                )
            )
    if scheme is not None:
        found, matched, checks = scheme_violations(
            text, pack, scheme, allow_identical=allow_identical
        )
        violations += found
        good += matched
        total += checks
    if metre is not None:
        for offset, line in line_spans(text):
            result = metre_violations(line, pack, metre, offset)
            violations += result.violations
            good += result.good
            total += result.total
            estimated += result.estimated
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
    return FormResult(violations, good, max(total, 1), estimated)


@register
class RhymeScheme(BaseProcedure[RhymeSchemeParams]):
    """Lines sharing a letter must rhyme; lines with different letters must not."""

    id = "rhyme_scheme"

    @classmethod
    def params_model(cls) -> type[RhymeSchemeParams]:
        return RhymeSchemeParams

    def _check(self, text: str, pack: LanguagePack, params: RhymeSchemeParams) -> Report:
        result = form_report(
            text, pack, scheme=params.scheme, allow_identical=params.allow_identical
        )
        return self._report(
            good=result.good,
            total=result.total,
            violations=result.violations,
            metrics={
                "pairs_checked": float(result.total),
                "estimated_words": float(result.estimated),
            },
        )
