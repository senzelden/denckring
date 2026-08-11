"""Tautogram — every word begins with the same letter."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


class TautogramParams(BaseModel):
    initial: str | None = Field(default=None, description="Shared initial; inferred if unset.")

    @field_validator("initial")
    @classmethod
    def _single_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != 1 or not value.isalpha():
            raise ValueError("initial must be a single alphabetic character")
        return value.lower()


@register
class Tautogram(BaseProcedure[TautogramParams]):
    """Hucbald's constraint: one initial letter for every word."""

    id = "tautogram"

    @classmethod
    def params_model(cls) -> type[TautogramParams]:
        return TautogramParams

    def _check(self, text: str, pack: LanguagePack, params: TautogramParams) -> Report:
        words = word_spans(text, pack)
        initials = [(offset, word, pack.fold_diacritics(word[0])[:1]) for offset, word in words]
        expected = params.initial
        if expected is None and initials:
            expected = initials[0][2]
        violations = [
            Violation(rule="wrong_initial", offset=offset, found=word, expected=expected or "")
            for offset, word, initial in initials
            if initial != expected
        ]
        return self._report(
            good=len(words) - len(violations),
            total=len(words),
            violations=violations,
            metrics={"words": float(len(words)), "wrong": float(len(violations))},
        )
