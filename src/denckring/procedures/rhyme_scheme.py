"""Rhyme scheme — line endings follow a prescribed pattern."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.prosody import metre_violations, scheme_violations
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans


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
) -> tuple[list[Violation], int, int]:
    """Check any combination of rhyme scheme, metre and refrain lines.

    The fixed forms are assembled from these three parts rather than
    reimplementing them, so a sonnet is a rhyme scheme plus a metre and says so.
    """
    violations: list[Violation] = []
    good = 0
    total = 0
    if scheme is not None:
        found, matched, checks = scheme_violations(
            text, pack, scheme, allow_identical=allow_identical
        )
        violations += found
        good += matched
        total += checks
    if metre is not None:
        for offset, line in line_spans(text):
            found, matched, checks = metre_violations(line, pack, metre, offset)
            violations += found
            good += matched
            total += checks
    if refrains is not None:
        lines = [line.strip().casefold() for _, line in line_spans(text)]
        for first, repeat in refrains:
            total += 1
            if first < len(lines) and repeat < len(lines) and lines[first] == lines[repeat]:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="broken_refrain",
                        offset=None,
                        found=lines[repeat] if repeat < len(lines) else "",
                        expected=lines[first] if first < len(lines) else f"line {first + 1}",
                    )
                )
    return violations, good, max(total, 1)


@register
class RhymeScheme(BaseProcedure[RhymeSchemeParams]):
    """Lines sharing a letter must rhyme; lines with different letters must not."""

    id = "rhyme_scheme"

    @classmethod
    def params_model(cls) -> type[RhymeSchemeParams]:
        return RhymeSchemeParams

    def _check(self, text: str, pack: LanguagePack, params: RhymeSchemeParams) -> Report:
        violations, good, total = form_report(
            text, pack, scheme=params.scheme, allow_identical=params.allow_identical
        )
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={"pairs_checked": float(total)},
        )
