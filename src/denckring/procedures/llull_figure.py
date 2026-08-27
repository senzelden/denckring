"""Llullian figure — a chamber of principles from the rotating wheels."""

from __future__ import annotations

import random

from pydantic import BaseModel, Field

from denckring.core import device as devices
from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register

MIN_ARITY = 2


def read_names(text: str, table: dict[str, str]) -> list[str]:
    """Consume the text as a run of principle names, or return nothing.

    Names are matched longest-first because some are several words long — the
    ninth question is `Quomodo et cum quo`, and splitting on whitespace would
    never find it. This is the Denckring's segmentation applied to a word list
    rather than a set of morphemes.
    """
    spoken = sorted(table.items(), key=lambda pair: len(pair[1]), reverse=True)
    remaining = " ".join(text.split()).casefold()
    letters: list[str] = []
    while remaining:
        for letter, name in spoken:
            folded = name.casefold()
            if remaining.startswith(folded):
                letters.append(letter)
                remaining = remaining[len(folded) :].lstrip()
                break
        else:
            return []
    return letters


class LlullFigureParams(BaseModel):
    figure: str = Field(default="llull_ternary", description="Which figure to read against.")
    level: str | None = Field(
        default=None,
        description="Which table to read the letters at; inferred if unset.",
    )
    arity: int = Field(default=3, ge=MIN_ARITY, description="Principles per chamber.")


class LlullFigureApplyParams(LlullFigureParams, SeedParams, ApplyParams):
    pass


@register
class LlullFigure(ConstructiveProcedure[LlullFigureParams, LlullFigureApplyParams]):
    """Three concentric wheels lettered B to K, turning to make chambers.

    A chamber may be written as letters — `BCD` — or spelled out at one of the
    figure's levels — `Bonitas Magnitudo Aeternitas`. Both are accepted, and if
    no level is named the checker asks whether *some* level reads, which is the
    satisfiability question the rest of this package already takes.

    What the wheels do not do is generate new truths freely: the stock of
    principles is fixed and the combinations that would be heterodox are ruled
    out elsewhere in the Ars. That is recorded in the catalogue note rather than
    smoothed away, because the device is often described as though it were an
    open-ended generator.
    """

    id = "llull_figure"

    @classmethod
    def params_model(cls) -> type[LlullFigureParams]:
        return LlullFigureParams

    def _check(self, text: str, pack: LanguagePack, params: LlullFigureParams) -> Report:
        figure = devices.load_figure(params.figure)
        levels = [params.level] if params.level else figure.level_names()
        letters = [ch.upper() for ch in text if ch.isalpha()]

        # A chamber written as letters — BCD, or B C D — is every character of
        # the text drawn from the figure's alphabet. A spelled-out principle
        # cannot be mistaken for one, since no name is built only of the nine.
        if letters and all(letter in figure.letters for letter in letters):
            return self._chamber_report(letters, figure, params)

        for level in levels:
            found = read_names(text, figure.levels.get(level, {}))
            if found:
                return self._chamber_report(found, figure, params)

        return self._report(
            good=0,
            total=1,
            violations=[
                Violation(
                    rule="not_a_chamber",
                    offset=None,
                    found=text.strip(),
                    expected=(
                        f"letters from {''.join(figure.letters)}, or principles named at "
                        f"one of: {', '.join(levels)}"
                    ),
                )
            ],
            metrics={"chambers": float(len(figure.chambers(params.arity)))},
        )

    def _chamber_report(
        self,
        letters: list[str],
        figure: devices.Figure,
        params: LlullFigureParams,
    ) -> Report:
        violations: list[Violation] = []
        if len(letters) != params.arity:
            violations.append(
                Violation(
                    rule="wrong_arity",
                    offset=None,
                    found=f"{len(letters)} principles",
                    expected=f"{params.arity} principles",
                )
            )
        repeated = {letter for letter in letters if letters.count(letter) > 1}
        for letter in sorted(repeated):
            violations.append(
                Violation(
                    rule="repeated_principle",
                    offset=None,
                    found=letter,
                    expected="a principle not already in the chamber",
                )
            )
        checks = 1 + len(letters)
        return self._report(
            good=checks - len(violations),
            total=checks,
            violations=violations,
            metrics={
                "principles": float(len(letters)),
                "chambers": float(len(figure.chambers(params.arity))),
            },
        )

    @classmethod
    def apply_params_model(cls) -> type[LlullFigureApplyParams]:
        return LlullFigureApplyParams

    def _apply(self, text: str, pack: LanguagePack, params: LlullFigureApplyParams) -> str:
        """Turn the wheels to a chamber, spelled out at the chosen level."""
        figure = devices.load_figure(params.figure)
        chamber = random.Random(params.seed).choice(figure.chambers(params.arity))
        level = params.level or "absolute"
        return " ".join(figure.read(chamber, level))
