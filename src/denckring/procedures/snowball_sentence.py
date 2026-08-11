"""Snowball sentence — each sentence has one more word than the last."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class SnowballSentenceParams(BaseModel):
    start: int | None = Field(default=None, description="Words in the first sentence.")
    step: int = Field(default=1, description="Words added per sentence.")


@register
class SnowballSentence(BaseProcedure[SnowballSentenceParams]):
    """The snowball raised from the word to the sentence."""

    id = "snowball_sentence"

    @classmethod
    def params_model(cls) -> type[SnowballSentenceParams]:
        return SnowballSentenceParams

    def _check(self, text: str, pack: LanguagePack, params: SnowballSentenceParams) -> Report:
        sentences = [s for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]
        counts = [len(pack.tokenize(s)) for s in sentences]
        if not counts:
            return self._report(good=0, total=0, violations=[], metrics={"sentences": 0.0})
        start = params.start if params.start is not None else counts[0]
        violations = [
            Violation(
                rule="wrong_sentence_length",
                offset=None,
                found=f"{count} words",
                expected=f"{start + index * params.step} words",
            )
            for index, count in enumerate(counts)
            if count != start + index * params.step
        ]
        return self._report(
            good=len(counts) - len(violations),
            total=len(counts),
            violations=violations,
            metrics={"sentences": float(len(counts)), "wrong": float(len(violations))},
        )
