"""Single sentence — one sentence, however long, and no more."""

from __future__ import annotations

import re

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register

TERMINATOR = re.compile(r"[.!?]")


class SingleSentenceParams(BaseModel):
    pass


@register
class SingleSentence(BaseProcedure[SingleSentenceParams]):
    """At most one sentence-ending mark, and only at the very end.

    An empty text is vacuously satisfied: it breaks the sentence into no more
    than one piece, which is what the constraint asks.
    """

    id = "single_sentence"

    @classmethod
    def params_model(cls) -> type[SingleSentenceParams]:
        return SingleSentenceParams

    def _check(self, text: str, pack: LanguagePack, params: SingleSentenceParams) -> Report:
        stripped = text.rstrip()
        marks = list(TERMINATOR.finditer(stripped))
        interior = [m for m in marks if m.end() < len(stripped)]
        violations = [
            Violation(
                rule="interior_terminator",
                offset=m.start(),
                found=m.group(),
                expected="no sentence break before the end",
            )
            for m in interior
        ]
        total = max(len(marks), 1)
        return self._report(
            good=total - len(violations),
            total=total,
            violations=violations,
            metrics={"terminators": float(len(marks)), "interior": float(len(interior))},
        )
