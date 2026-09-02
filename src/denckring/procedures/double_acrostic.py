"""Double acrostic — the initials spell one word and the finals another."""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import fold_target, letter_spans, line_spans


class DoubleAcrosticParams(DiacriticParams):
    first: str = Field(description="What the line initials must spell.")
    last: str = Field(description="What the line final letters must spell.")

    @field_validator("first", "last")
    @classmethod
    def _at_least_one_letter(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("targets must contain at least one letter")
        return value


@register
class DoubleAcrostic(BaseProcedure[DoubleAcrosticParams]):
    """A poem bounded on both margins by a hidden word."""

    id = "double_acrostic"

    @classmethod
    def params_model(cls) -> type[DoubleAcrosticParams]:
        return DoubleAcrosticParams

    def _check(self, text: str, pack: LanguagePack, params: DoubleAcrosticParams) -> Report:
        fold = params.fold_diacritics
        lines = [
            (offset, letters)
            for offset, line in line_spans(text)
            if (letters := letter_spans(line, pack, fold=fold))
        ]
        # The same flattening as `acrostic`, through the same function: this
        # row kept its own copy of the expression once and diverged from it,
        # which is the divergence ADR 0035 D3 cites (and `fold_target` ends).
        wanted_first = fold_target(params.first, pack, fold=fold)
        wanted_last = fold_target(params.last, pack, fold=fold)
        expected_length = max(len(wanted_first), len(wanted_last))

        violations: list[Violation] = []
        matches = 0
        for index in range(expected_length):
            if index >= len(lines):
                violations.append(
                    Violation(rule="missing_line", offset=None, found="", expected="a line")
                )
                continue
            offset, letters = lines[index]
            for edge, wanted in (("initial", wanted_first), ("final", wanted_last)):
                if index >= len(wanted):
                    continue
                got = letters[0][1] if edge == "initial" else letters[-1][1]
                if got == wanted[index]:
                    matches += 1
                else:
                    violations.append(
                        Violation(
                            rule=f"wrong_{edge}", offset=offset, found=got, expected=wanted[index]
                        )
                    )
        for offset, letters in lines[expected_length:]:
            violations.append(
                Violation(rule="extra_line", offset=offset, found=letters[0][1], expected="")
            )
        total = len(wanted_first) + len(wanted_last) + max(0, len(lines) - expected_length)
        return self._report(
            good=matches,
            total=total,
            violations=violations,
            metrics={"lines": float(len(lines)), "matches": float(matches)},
        )
