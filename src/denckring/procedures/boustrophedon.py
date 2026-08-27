"""Boustrophedon — lines alternate direction, "as an ox turns at the furrow's end".

Archaic Greek inscriptions ran left to right, then right to left, then back
again, so the eye never left the page to start a new line. Rendered here as a
plain string operation: the source is split into lines, and every odd-indexed
line (0-based — the second, fourth, ...) has its characters reversed end to
end, spaces included, so the words themselves run backwards too, exactly as
they would to an eye tracing the furrow home. Even-indexed lines are left
exactly as the source has them.

Written by hand first, with the comparison inline and no helper. That draft is
what `denckring.core.source_compare.rearrangement_report` was distilled from —
see that function's docstring for what the hand-written version taught about
its shape. The turning rule stays here: it is the one thing this row and
`text_folding` do not share.
"""

from __future__ import annotations

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams
from denckring.core.errors import InputTooShort
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import rearrangement_report
from denckring.core.text import line_spans, word_spans


class BoustrophedonParams(SourceParams):
    pass


class BoustrophedonApplyParams(BoustrophedonParams, ApplyParams):
    pass


@register
class Boustrophedon(ConstructiveProcedure[BoustrophedonParams, BoustrophedonApplyParams]):
    """Constructive: `apply` turns alternate lines that `check` verifies."""

    id = "boustrophedon"

    @classmethod
    def params_model(cls) -> type[BoustrophedonParams]:
        return BoustrophedonParams

    def _check(self, text: str, pack: LanguagePack, params: BoustrophedonParams) -> Report:
        text_lines = line_spans(text)
        source_lines = [line for _, line in line_spans(params.source)]

        # Undo the turn on every odd-indexed line before comparing to the
        # source: reversing a correctly-turned line a second time returns it
        # to its source spelling, and reversing an incorrectly-turned one
        # (still reading forwards) mismatches it instead — which is exactly
        # what should happen, since that line's content has not actually been
        # recovered.
        canonical = [
            line[::-1] if index % 2 == 1 else line for index, (_, line) in enumerate(text_lines)
        ]
        result = rearrangement_report(canonical, source_lines)
        violations = list(result.violations)
        good = result.good
        total = result.total

        for index, (offset, line) in enumerate(text_lines):
            if index % 2 == 0 or index >= len(source_lines):
                continue
            total += 1
            expected = source_lines[index][::-1]
            if line == expected:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="line_not_turned",
                        offset=offset,
                        found=line,
                        expected=expected,
                        note=f"line {index + 1} must run in reverse",
                    )
                )

        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={
                "lines": float(len(text_lines)),
                "words": float(len(word_spans(text, pack))),
            },
        )

    @classmethod
    def apply_params_model(cls) -> type[BoustrophedonApplyParams]:
        return BoustrophedonApplyParams

    def _apply(self, text: str, pack: LanguagePack, params: BoustrophedonApplyParams) -> str:
        """Turn `text`'s alternate lines, `text` serving as its own source.

        Every source line survives the turn — there is no candidate that can
        go missing — so, unlike the selection-based rows, this never raises
        `NoCandidateWord`.
        """
        lines = [line for _, line in line_spans(text)]
        if len(lines) < 2:
            raise InputTooShort(
                self.id,
                needed="more than one line, so there is an alternate to turn",
                found=f"{len(lines)} line",
            )
        turned = [line[::-1] if index % 2 == 1 else line for index, line in enumerate(lines)]
        return "\n".join(turned)
