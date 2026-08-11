"""Abecedarian — successive units begin with successive letters of the alphabet."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, line_spans, word_spans


class AbecedarianParams(DiacriticParams):
    unit: Literal["line", "word"] = Field(default="line", description="What carries a letter.")
    start: str | None = Field(default=None, description="First letter; inferred if unset.")

    @field_validator("start")
    @classmethod
    def _single_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != 1 or not value.isalpha():
            raise ValueError("start must be a single alphabetic character")
        return value.lower()


@register
class Abecedarian(BaseProcedure[AbecedarianParams]):
    """The initials run A, B, C — the alphabet used as a spine."""

    id = "abecedarian"

    @classmethod
    def params_model(cls) -> type[AbecedarianParams]:
        return AbecedarianParams

    def _check(self, text: str, pack: LanguagePack, params: AbecedarianParams) -> Report:
        alphabet = pack.alphabet()
        units = line_spans(text) if params.unit == "line" else word_spans(text, pack)
        initials = [
            (offset, letters[0][1])
            for offset, unit_text in units
            if (letters := letter_spans(unit_text, pack, fold=params.fold_diacritics))
        ]
        if not initials:
            return self._report(good=0, total=0, violations=[], metrics={"units": 0.0})
        start = params.start if params.start is not None else initials[0][1]
        first = alphabet.index(start) if start in alphabet else 0
        violations = [
            Violation(
                rule="wrong_initial",
                offset=offset,
                found=initial,
                expected=alphabet[(first + index) % len(alphabet)],
            )
            for index, (offset, initial) in enumerate(initials)
            if initial != alphabet[(first + index) % len(alphabet)]
        ]
        return self._report(
            good=len(initials) - len(violations),
            total=len(initials),
            violations=violations,
            metrics={"units": float(len(initials)), "wrong": float(len(violations))},
        )
