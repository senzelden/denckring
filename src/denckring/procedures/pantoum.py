"""Pantoum — lines 2 and 4 of each quatrain open the next."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_identity, line_spans

QUATRAIN = 4


class PantoumParams(BaseModel):
    pass


@register
class Pantoum(BaseProcedure[PantoumParams]):
    """Checks the line interlocking only, not metre or rhyme."""

    id = "pantoum"

    @classmethod
    def params_model(cls) -> type[PantoumParams]:
        return PantoumParams

    def _check(self, text: str, pack: LanguagePack, params: PantoumParams) -> Report:
        # A repeated line is the same line whatever punctuation its new position
        # gives it — see `line_identity`.
        lines = [line_identity(line) for _, line in line_spans(text)]
        stanzas = [lines[i : i + QUATRAIN] for i in range(0, len(lines), QUATRAIN)]
        violations: list[Violation] = []
        checked = 0
        matched = 0
        for index in range(len(stanzas) - 1):
            current, following = stanzas[index], stanzas[index + 1]
            if len(current) < QUATRAIN or len(following) < QUATRAIN:
                violations.append(
                    Violation(
                        rule="incomplete_quatrain",
                        offset=None,
                        found=str(min(len(current), len(following))),
                        expected="4 lines",
                    )
                )
                checked += 1
                continue
            for carried, lands in ((1, 0), (3, 2)):
                checked += 1
                if current[carried] == following[lands]:
                    matched += 1
                else:
                    violations.append(
                        Violation(
                            rule="broken_interlock",
                            offset=None,
                            found=following[lands],
                            expected=current[carried],
                        )
                    )
        return self._report(
            good=matched,
            total=checked,
            violations=violations,
            metrics={"stanzas": float(len(stanzas)), "lines": float(len(lines))},
        )
