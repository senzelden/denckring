"""Anaphora — every line opens with the same word."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans


class AnaphoraParams(BaseModel):
    opening: str | None = Field(default=None, description="Shared opening; inferred if unset.")


@register
class Anaphora(BaseProcedure[AnaphoraParams]):
    """The repetition that carries the structure from the front of the line."""

    id = "anaphora"

    @classmethod
    def params_model(cls) -> type[AnaphoraParams]:
        return AnaphoraParams

    def _check(self, text: str, pack: LanguagePack, params: AnaphoraParams) -> Report:
        openings = [
            (offset, words[0].casefold())
            for offset, line in line_spans(text)
            if (words := pack.tokenize(line))
        ]
        expected = params.opening.casefold() if params.opening else None
        if expected is None and openings:
            expected = openings[0][1]
        violations = [
            Violation(rule="wrong_opening", offset=offset, found=word, expected=expected or "")
            for offset, word in openings
            if word != expected
        ]
        return self._report(
            good=len(openings) - len(violations),
            total=len(openings),
            violations=violations,
            metrics={"lines": float(len(openings)), "wrong": float(len(violations))},
        )
