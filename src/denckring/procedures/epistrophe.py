"""Epistrophe — every line closes with the same word."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans


class EpistropheParams(BaseModel):
    closing: str | None = Field(default=None, description="Shared closing; inferred if unset.")


@register
class Epistrophe(BaseProcedure[EpistropheParams]):
    """Anaphora read from the other end of the line."""

    id = "epistrophe"

    @classmethod
    def params_model(cls) -> type[EpistropheParams]:
        return EpistropheParams

    def _check(self, text: str, pack: LanguagePack, params: EpistropheParams) -> Report:
        closings = [
            (offset, words[-1].casefold())
            for offset, line in line_spans(text)
            if (words := pack.tokenize(line))
        ]
        expected = params.closing.casefold() if params.closing else None
        if expected is None and closings:
            expected = closings[0][1]
        violations = [
            Violation(rule="wrong_closing", offset=offset, found=word, expected=expected or "")
            for offset, word in closings
            if word != expected
        ]
        return self._report(
            good=len(closings) - len(violations),
            total=len(closings),
            violations=violations,
            metrics={"lines": float(len(closings)), "wrong": float(len(violations))},
        )
