"""Univocalic — a text using only one of the vowels."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class UnivocalicParams(BaseModel):
    vowel: str | None = Field(default=None, description="The permitted vowel; inferred if unset.")

    @field_validator("vowel")
    @classmethod
    def _single_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != 1 or not value.isalpha():
            raise ValueError("vowel must be a single alphabetic character")
        return value.lower()


@register
class Univocalic(BaseProcedure[UnivocalicParams]):
    """One vowel only. Consonants are unconstrained."""

    id = "univocalic"

    @classmethod
    def params_model(cls) -> type[UnivocalicParams]:
        return UnivocalicParams

    def _check(self, text: str, pack: LanguagePack, params: UnivocalicParams) -> Report:
        vowel_set = pack.vowels()
        found = [(offset, ch) for offset, ch in letter_spans(text, pack) if ch in vowel_set]
        permitted = params.vowel
        if permitted is None and found:
            permitted = Counter(ch for _, ch in found).most_common(1)[0][0]
        violations = [
            Violation(
                rule="foreign_vowel",
                offset=offset,
                found=ch,
                expected=permitted or "",
            )
            for offset, ch in found
            if ch != permitted
        ]
        return self._report(
            good=len(found) - len(violations),
            total=len(found),
            violations=violations,
            metrics={"vowel_count": float(len(found)), "foreign": float(len(violations))},
        )
