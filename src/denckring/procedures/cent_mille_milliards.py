"""Cent mille milliards de poèmes — one line chosen per position."""

from __future__ import annotations

import random

from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams, SourceParams, plain
from denckring.core.errors import InputTooShort, counted
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
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


class CentMilleMilliardsApplyParams(CentMilleMilliardsParams, SeedParams, ApplyParams):
    pass


@register
class CentMilleMilliards(
    ConstructiveProcedure[CentMilleMilliardsParams, CentMilleMilliardsApplyParams]
):
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

    @classmethod
    def apply_params_model(cls) -> type[CentMilleMilliardsApplyParams]:
        return CentMilleMilliardsApplyParams

    def _produce(
        self, text: str, pack: LanguagePack, params: CentMilleMilliardsApplyParams
    ) -> Produced:
        """One reading of the machine: a line drawn for each position.

        `text` is the machine itself — the sheet of alternatives — not a poem to
        transform. Queneau's book is ten sonnets cut into strips, and turning a
        page is exactly this draw.

        A position offering no alternative at all is a malformed sheet, not a
        poem with a gap: `_check` requires one produced line per source
        position, so a position with nothing to draw from can never be
        satisfied and must be refused up front rather than silently skipped.
        Skipping it — the previous behaviour — drew one fewer line than the
        sheet has positions, which is exactly the shape `_check`'s own
        `missing_line` violation exists to catch; refusing it here means that
        violation can no longer be produced by this row's own `apply`. Checked
        before the "no position offers a choice" guard below, which is the
        sibling case — every position has exactly one alternative — rather
        than a subset having none.
        """
        chooser = random.Random(params.seed)
        options = alternatives(text)
        empty = [index for index, position in enumerate(options) if not position]
        if empty:
            raise InputTooShort(
                self.id,
                needed=(
                    f"every position to offer at least one alternative, separated by {SEPARATOR!r}"
                ),
                found=f"line {empty[0] + 1} of {counted(len(options), 'position')} offers none",
            )
        if not any(len(position) > 1 for position in options):
            raise InputTooShort(
                self.id,
                needed=f"at least one position offering alternatives, separated by {SEPARATOR!r}",
                found=f"{counted(len(options), 'position')}, none with a choice",
            )
        return plain(["\n".join(chooser.choice(position) for position in options)])
