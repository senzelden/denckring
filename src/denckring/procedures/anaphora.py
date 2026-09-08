"""Anaphora — successive clauses or lines opening with the same word or phrase."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import clause_spans, line_spans


class AnaphoraParams(BaseModel):
    opening: str | None = Field(default=None, description="Shared opening; inferred if unset.")
    #: The catalogue says "clauses or lines" and this row read lines only, so it
    #: could not see the figure inside a line. `line` stays the default because
    #: no existing verdict may move.
    unit: Literal["line", "clause"] = Field(
        default="line", description="Whether the repetition is counted per line or per clause."
    )
    #: Real anaphora survives an enjambment: six of the seven lines of Gaunt's
    #: "This royal throne of kings" open with `This`, and the seventh is the
    #: second half of the sixth's sentence. Demanding all of them rejects the
    #: passage the figure is named for. `None` keeps the old meaning, all of them.
    minimum: int | None = Field(
        default=None, ge=1, description="How many units must share the opening; all, if unset."
    )


@register
class Anaphora(BaseProcedure[AnaphoraParams]):
    """The repetition that carries the structure from the front."""

    id = "anaphora"

    @classmethod
    def params_model(cls) -> type[AnaphoraParams]:
        return AnaphoraParams

    def _check(self, text: str, pack: LanguagePack, params: AnaphoraParams) -> Report:
        spans = clause_spans(text) if params.unit == "clause" else line_spans(text)
        wanted = params.opening.split() if params.opening else None
        width = len(wanted) if wanted else 1
        openings = [
            (offset, " ".join(words[:width]).casefold())
            for offset, piece in spans
            if (words := pack.tokenize(piece))
        ]
        expected = " ".join(wanted).casefold() if wanted else None
        if expected is None and openings:
            expected = openings[0][1]
        matched = [span for span in openings if span[1] == expected]
        # With a `minimum` the question is whether the run reaches it, so that is
        # the denominator: six of the six you asked for scores 1.0, four of six
        # scores 0.667. Without one the question is still every unit, unchanged.
        want = params.minimum if params.minimum else len(openings)
        good = min(len(matched), want)
        violations = (
            []
            if good >= want
            else [
                Violation(rule="wrong_opening", offset=offset, found=word, expected=expected or "")
                for offset, word in openings
                if word != expected
            ]
        )
        return self._report(
            good=good,
            total=want,
            violations=violations,
            metrics={"units": float(len(openings)), "matched": float(len(matched))},
        )
