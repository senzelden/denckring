"""Boustrophedon — lines alternate direction, "as an ox turns at the furrow's end".

Archaic Greek inscriptions ran left to right, then right to left, then back
again, so the eye never left the page to start a new line. Rendered here as a
plain string operation: the source is split into lines, and every odd-indexed
line (0-based — the second, fourth, ...) has its characters reversed end to
end, spaces included, so the words themselves run backwards too, exactly as
they would to an eye tracing the furrow home. Even-indexed lines are left
exactly as the source has them.

Written by hand first, with the comparison inline and no helper — see
`denckring.core.source_compare` for what this draft taught about
`rearrangement_report`'s shape, once it existed.
"""

from __future__ import annotations

from collections import Counter

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans, word_spans


class BoustrophedonParams(SourceParams):
    pass


@register
class Boustrophedon(BaseProcedure[BoustrophedonParams]):
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
        have = Counter(part.strip().casefold() for part in canonical)
        want = Counter(part.strip().casefold() for part in source_lines)
        violations: list[Violation] = []
        for part, count in (want - have).items():
            violations.append(
                Violation(
                    rule="missing_part", offset=None, found="", expected=part, note=f"x{count}"
                )
            )
        for part, count in (have - want).items():
            violations.append(
                Violation(
                    rule="invented_part", offset=None, found=part, expected="", note=f"x{count}"
                )
            )
        good = sum((want & have).values())
        # No `, 1` floor: an all-blank text has nothing turned and nothing
        # missing, and `_report` already scores a `total == 0` report
        # vacuously satisfied — the same reasoning `letter_class_report`
        # documents. Flooring here would score that case 0 with nothing to
        # explain why, and would also let an invented line slip past for
        # free: pinning `total` to `sum(want.values())` alone, as a first
        # draft of this comparison did, left `have`'s extra content costing
        # nothing against the score.
        total = max(sum(want.values()), sum(have.values()))

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

    def apply(
        self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: object
    ) -> str:
        """Turn `text`'s alternate lines, `text` serving as its own source.

        Every source line survives the turn — there is no candidate that can
        go missing — so, unlike the selection-based rows, this never raises
        `NoCandidateWord`.
        """
        self.parse_params({"source": text, **params})
        lines = [line for _, line in line_spans(text)]
        turned = [line[::-1] if index % 2 == 1 else line for index, line in enumerate(lines)]
        return "\n".join(turned)
