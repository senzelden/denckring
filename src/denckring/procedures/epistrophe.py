"""Epistrophe — successive clauses or lines closing with the same word or phrase."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import clause_spans, line_spans


class EpistropheParams(BaseModel):
    closing: str | None = Field(default=None, description="Shared closing; inferred if unset.")
    #: The figure's most quoted instance — "of the people, by the people, for the
    #: people" — is three clauses inside one line, so by lines there is nothing to
    #: compare. `line` stays the default because no existing verdict may move.
    unit: Literal["line", "clause"] = Field(
        default="line", description="Whether the repetition is counted per line or per clause."
    )
    minimum: int | None = Field(
        default=None, ge=1, description="How many units must share the closing; all, if unset."
    )


@register
class Epistrophe(BaseProcedure[EpistropheParams]):
    """Anaphora read from the other end."""

    id = "epistrophe"

    @classmethod
    def params_model(cls) -> type[EpistropheParams]:
        return EpistropheParams

    def _check(self, text: str, pack: LanguagePack, params: EpistropheParams) -> Report:
        spans = clause_spans(text) if params.unit == "clause" else line_spans(text)
        wanted = params.closing.split() if params.closing else None
        width = len(wanted) if wanted else 1
        closings = [
            (offset, " ".join(words[-width:]).casefold())
            for offset, piece in spans
            if (words := pack.tokenize(piece))
        ]
        expected = " ".join(wanted).casefold() if wanted else None
        if expected is None and closings:
            expected = closings[0][1]
        matched = [span for span in closings if span[1] == expected]
        # See `anaphora`: with a `minimum` the denominator is what was asked for.
        want = params.minimum if params.minimum else len(closings)
        good = min(len(matched), want)
        violations = (
            []
            if good >= want
            else [
                Violation(rule="wrong_closing", offset=offset, found=word, expected=expected or "")
                for offset, word in closings
                if word != expected
            ]
        )
        return self._report(
            good=good,
            total=want,
            violations=violations,
            metrics={"units": float(len(closings)), "matched": float(len(matched))},
        )
