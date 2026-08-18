"""Ghazal — couplets closing on a repeated word, the radif, with a rhyme before it.

The radif is taken from the opening couplet rather than given as a parameter: the
form defines it as whatever word the first couplet repeats, so asking the caller
would let a text declare its own compliance.

A ghazal is radif *and* qafia: the repeated end word, and a rhyme immediately
preceding it. The word before the radif in line 1 sets the qafia; every later
line carrying the radif must rhyme with it there. Scored as one more check per
carrying line rather than a hard gate — real ghazals vary in how strictly the
qafia is kept, so a poem that drops it does not fail outright, it scores lower.
"""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans, word_spans


class GhazalParams(BaseModel):
    pass


@register
class Ghazal(BaseProcedure[GhazalParams]):
    """Every second line ends on the word both lines of the first couplet end on."""

    id = "ghazal"

    @classmethod
    def params_model(cls) -> type[GhazalParams]:
        return GhazalParams

    def _check(self, text: str, pack: LanguagePack, params: GhazalParams) -> Report:
        lines = [line for _, line in line_spans(text)]
        violations: list[Violation] = []
        if len(lines) < 2:
            return self._report(
                good=0,
                total=1,
                violations=[
                    Violation(
                        rule="wrong_line_count",
                        offset=None,
                        found=f"{len(lines)} lines",
                        expected="at least 2 lines",
                    )
                ],
                metrics={"couplets": 0.0},
            )

        def words_of(line: str) -> list[str]:
            return [word.casefold() for _, word in word_spans(line, pack)]

        first_words = words_of(lines[0])
        radif = first_words[-1] if first_words else ""
        base_qafia = pack.rhyme_key(first_words[-2]) if len(first_words) >= 2 else None

        good = 0
        total = 0
        qafia_good = 0
        qafia_total = 0
        # The opening couplet carries the radif on both lines; thereafter every second.
        carriers = [1, *range(3, len(lines), 2)]
        for index in carriers:
            total += 1
            words = words_of(lines[index])
            actual = words[-1] if words else ""
            if actual == radif:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="missing_radif",
                        offset=None,
                        found=actual,
                        expected=radif,
                    )
                )
                continue
            if base_qafia is None or len(words) < 2:
                continue
            qafia_total += 1
            candidate = pack.rhyme_key(words[-2])
            if candidate == base_qafia:
                qafia_good += 1
            else:
                violations.append(
                    Violation(
                        rule="broken_qafia",
                        offset=None,
                        found=candidate,
                        expected=base_qafia,
                    )
                )
        return self._report(
            good=good + qafia_good,
            total=max(total + qafia_total, 1),
            violations=violations,
            metrics={"couplets": float(len(lines) // 2)},
        )
