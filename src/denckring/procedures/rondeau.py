"""Rondeau — fifteen lines on two rhymes, with a rentrement closing two of them.

The rentrement is the opening *words* of the first line, not the whole line, and it
does not rhyme. That is why this cannot use `form_report`'s refrain check, which
compares whole lines: doing so would demand a rhyme the form forbids.

A standard rondeau is `aabba / aabR / aabbaR` — fifteen lines in three stanzas, the
rentrement closing the second and third. Written out as the thirteen full lines'
scheme plus the two rentrement slots: `AABBA` (lines 1-5) + `AAB` (lines 6-8) +
`AABBA` (lines 10-14), with the rentrement falling at lines 9 and 15 — indices 8
and 14.
"""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.prosody import scheme_violations
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_identity, line_spans

#: The thirteen full lines. Indices 8 and 14 are the rentrement and carry no letter.
SCHEME = "AABBAAABAABBA"
RENTREMENT_LINES = (8, 14)
LINES = 13 + len(RENTREMENT_LINES)


class RondeauParams(RhymeParams):
    rentrement_words: int = Field(
        default=3, ge=1, description="How many opening words the rentrement repeats."
    )


@register
class Rondeau(BaseProcedure[RondeauParams]):
    """Two rhymes across thirteen lines, plus two unrhymed rentrements."""

    id = "rondeau"

    @classmethod
    def params_model(cls) -> type[RondeauParams]:
        return RondeauParams

    def _check(self, text: str, pack: LanguagePack, params: RondeauParams) -> Report:
        lines = [line for _, line in line_spans(text)]
        violations: list[Violation] = []
        good = 0
        total = 1
        if len(lines) == LINES:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_line_count",
                    offset=None,
                    found=f"{len(lines)} lines",
                    expected=f"{LINES} lines",
                )
            )
        if lines:
            opening = line_identity(" ".join(lines[0].split()[: params.rentrement_words]))
            for index in RENTREMENT_LINES:
                total += 1
                actual = line_identity(lines[index]) if index < len(lines) else ""
                if actual == opening:
                    good += 1
                else:
                    violations.append(
                        Violation(
                            rule="broken_rentrement",
                            offset=None,
                            found=actual,
                            expected=opening,
                        )
                    )
        rhyming = "\n".join(
            line for index, line in enumerate(lines) if index not in RENTREMENT_LINES
        )
        found, matched, checks, _estimated, rhymes = scheme_violations(
            rhyming, pack, SCHEME, allow_identical=False
        )
        return self._report(
            good=good + matched,
            total=total + checks,
            violations=violations + found,
            metrics={"lines": float(len(lines))},
            evidence=list(rhymes),
        )
