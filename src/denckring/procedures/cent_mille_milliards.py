"""Cent mille milliards de poèmes — one line chosen per position."""

from __future__ import annotations

import random
from typing import Any

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans

#: Alternatives for one position are written on one line, separated by this.
SEPARATOR = "|"


def alternatives(source: str) -> list[list[str]]:
    """One list of alternatives per position, read from the source text."""
    return [
        [part.strip() for part in line.split(SEPARATOR) if part.strip()]
        for _, line in line_spans(source)
    ]


class CentMilleMilliardsParams(SourceParams):
    pass


@register
class CentMilleMilliards(BaseProcedure[CentMilleMilliardsParams]):
    """Queneau's cut strips: is this poem one of the ten to the fourteenth?

    The source is the machine — each line listing the alternatives offered for
    that position, separated by a bar. Whether every one of them reads well is
    not a question code answers, and the catalogue row says so.
    """

    id = "cent_mille_milliards"

    @classmethod
    def params_model(cls) -> type[CentMilleMilliardsParams]:
        return CentMilleMilliardsParams

    def _check(self, text: str, pack: LanguagePack, params: CentMilleMilliardsParams) -> Report:
        offered = alternatives(params.source)
        chosen = line_spans(text)
        violations: list[Violation] = []
        matched = 0
        for index, options in enumerate(offered):
            if index >= len(chosen):
                violations.append(
                    Violation(
                        rule="missing_line",
                        offset=None,
                        found="",
                        expected=f"one of {len(options)} alternatives for line {index + 1}",
                    )
                )
                continue
            offset, line = chosen[index]
            if line.strip() in options:
                matched += 1
            else:
                violations.append(
                    Violation(
                        rule="line_not_offered",
                        offset=offset,
                        found=line.strip(),
                        expected=f"one of the {len(options)} alternatives for this position",
                    )
                )
        for offset, line in chosen[len(offered) :]:
            violations.append(
                Violation(rule="extra_line", offset=offset, found=line.strip(), expected="")
            )
        total = max(len(offered), len(chosen))
        combinations = 1
        for options in offered:
            combinations *= max(len(options), 1)
        return self._report(
            good=matched,
            total=total,
            violations=violations,
            metrics={"positions": float(len(offered)), "combinations": float(combinations)},
        )

    def apply(self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: Any) -> str:
        """One reading of the machine: a line drawn for each position.

        `text` is the machine itself — the sheet of alternatives — not a poem to
        transform. Queneau's book is ten sonnets cut into strips, and turning a
        page is exactly this draw.
        """
        self.parse_params({"source": text, **params})
        chooser = random.Random(seed)
        return "\n".join(chooser.choice(options) for options in alternatives(text) if options)
