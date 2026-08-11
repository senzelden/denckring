"""Sentence length constraint — every sentence has a prescribed word count."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class SentenceLengthConstraintParams(BaseModel):
    words: int = Field(description="Words each sentence must contain.")
    tolerance: int = Field(default=0, description="Permitted departure in either direction.")


@register
class SentenceLengthConstraint(BaseProcedure[SentenceLengthConstraintParams]):
    """Every sentence within tolerance of the target word count."""

    id = "sentence_length_constraint"

    @classmethod
    def params_model(cls) -> type[SentenceLengthConstraintParams]:
        return SentenceLengthConstraintParams

    def _check(
        self, text: str, pack: LanguagePack, params: SentenceLengthConstraintParams
    ) -> Report:
        sentences = [s for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]
        counts = [len(pack.tokenize(s)) for s in sentences]
        violations = [
            Violation(
                rule="wrong_sentence_length",
                offset=None,
                found=f"{count} words",
                expected=f"{params.words} words",
            )
            for count in counts
            if abs(count - params.words) > params.tolerance
        ]
        return self._report(
            good=len(counts) - len(violations),
            total=len(counts),
            violations=violations,
            metrics={"sentences": float(len(counts)), "wrong": float(len(violations))},
        )
