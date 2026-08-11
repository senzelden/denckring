"""Lipogram — a text omitting a chosen letter."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class LipogramParams(BaseModel):
    forbidden: str = Field(default="e", description="The letter the text must omit.")

    @field_validator("forbidden")
    @classmethod
    def _single_letter(cls, value: str) -> str:
        if len(value) != 1 or not value.isalpha():
            raise ValueError("forbidden must be a single alphabetic character")
        return value.lower()


@register
class Lipogram(BaseProcedure[LipogramParams]):
    """Perec's constraint: choose a letter and never use it."""

    id = "lipogram"

    @classmethod
    def params_model(cls) -> type[LipogramParams]:
        return LipogramParams

    def _check(self, text: str, pack: LanguagePack, params: LipogramParams) -> Report:
        letters = letter_spans(text, pack)
        violations = [
            Violation(
                rule="forbidden_letter",
                offset=offset,
                found=letter,
                expected=f"any letter but {params.forbidden!r}",
            )
            for offset, letter in letters
            if letter == params.forbidden
        ]
        return self._report(
            good=len(letters) - len(violations),
            total=len(letters),
            violations=violations,
            metrics={"letters": float(len(letters)), "hits": float(len(violations))},
        )
