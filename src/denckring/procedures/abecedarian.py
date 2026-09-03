"""Abecedarian — successive units begin with successive letters of the alphabet."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.errors import InvalidParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, line_spans, single_letter, word_spans


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
        # Folded the same way each unit's own initial is folded, or
        # `start="ä"` never matched `alphabet`, which is flat and unaccented —
        # `alphabet.index` fell back to 0 unconditionally, agreeing with the
        # correct answer only when the intended letter happened to be `a`
        # (index 0) and silently disagreeing for any other umlaut. ADR 0035,
        # D3; Known remaining.
        start = (
            initials[0][1]
            if params.start is None
            else single_letter(
                params.start,
                pack,
                fold=params.fold_diacritics,
                procedure_id=self.id,
                field="start",
            )
        )
        if start not in alphabet:
            raise InvalidParams(
                self.id, f"start {start!r} is not a letter of the {pack.lang} alphabet"
            )
        first = alphabet.index(start)
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
