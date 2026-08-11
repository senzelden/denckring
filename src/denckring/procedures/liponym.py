"""Liponym — a chosen word never appears."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


class LiponymParams(BaseModel):
    forbidden: str = Field(description="The word the text must never use.")

    @field_validator("forbidden")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("forbidden must be a non-empty word")
        return value.strip().lower()


@register
class Liponym(BaseProcedure[LiponymParams]):
    """The lipogram raised from the letter to the word."""

    id = "liponym"

    @classmethod
    def params_model(cls) -> type[LiponymParams]:
        return LiponymParams

    def _check(self, text: str, pack: LanguagePack, params: LiponymParams) -> Report:
        words = word_spans(text, pack)
        violations = [
            Violation(
                rule="forbidden_word",
                offset=offset,
                found=word,
                expected=f"any word but {params.forbidden!r}",
            )
            for offset, word in words
            if word.casefold() == params.forbidden
        ]
        return self._report(
            good=len(words) - len(violations),
            total=len(words),
            violations=violations,
            metrics={"words": float(len(words)), "hits": float(len(violations))},
        )
