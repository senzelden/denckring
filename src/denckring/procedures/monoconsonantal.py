"""Monoconsonantal — the text uses only one consonant."""

from __future__ import annotations

from collections import Counter

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans


class MonoconsonantalParams(DiacriticParams):
    consonant: str | None = Field(default=None, description="The permitted consonant.")

    @field_validator("consonant")
    @classmethod
    def _single_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != 1 or not value.isalpha():
            raise ValueError("consonant must be a single alphabetic character")
        return value.lower()


@register
class Monoconsonantal(BaseProcedure[MonoconsonantalParams]):
    """The mirror of the univocalic: one consonant, vowels unconstrained."""

    id = "monoconsonantal"

    @classmethod
    def params_model(cls) -> type[MonoconsonantalParams]:
        return MonoconsonantalParams

    def _check(self, text: str, pack: LanguagePack, params: MonoconsonantalParams) -> Report:
        vowel_set = pack.vowels()
        found = [
            (offset, ch)
            for offset, ch in letter_spans(text, pack, fold=params.fold_diacritics)
            if ch not in vowel_set
        ]
        permitted = params.consonant
        if permitted is None and found:
            permitted = Counter(ch for _, ch in found).most_common(1)[0][0]
        violations = [
            Violation(rule="foreign_consonant", offset=offset, found=ch, expected=permitted or "")
            for offset, ch in found
            if ch != permitted
        ]
        return self._report(
            good=len(found) - len(violations),
            total=len(found),
            violations=violations,
            metrics={"consonants": float(len(found)), "foreign": float(len(violations))},
        )
