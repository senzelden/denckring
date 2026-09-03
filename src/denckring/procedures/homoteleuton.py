"""Homoteleuton — every word ends with the same letter."""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, single_letter, word_spans


class HomoteleutonParams(DiacriticParams):
    final: str | None = Field(default=None, description="Shared final letter; inferred if unset.")

    @field_validator("final")
    @classmethod
    def _single_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != 1 or not value.isalpha():
            raise ValueError("final must be a single alphabetic character")
        return value.lower()


@register
class Homoteleuton(BaseProcedure[HomoteleutonParams]):
    """The tautogram read from the other end of each word."""

    id = "homoteleuton"

    @classmethod
    def params_model(cls) -> type[HomoteleutonParams]:
        return HomoteleutonParams

    def _check(self, text: str, pack: LanguagePack, params: HomoteleutonParams) -> Report:
        finals = [
            (offset, word, letters[-1][1])
            for offset, word in word_spans(text, pack)
            if (letters := letter_spans(word, pack, fold=params.fold_diacritics))
        ]
        # Folded the same way each word's own final letter is folded, or
        # `final="é"` never matched the folded finals it was compared
        # against. ADR 0035, D3; Known remaining.
        expected = (
            None
            if params.final is None
            else single_letter(
                params.final,
                pack,
                fold=params.fold_diacritics,
                procedure_id=self.id,
                field="final",
            )
        )
        if expected is None and finals:
            expected = finals[0][2]
        violations = [
            Violation(rule="wrong_final", offset=offset, found=word, expected=expected or "")
            for offset, word, final in finals
            if final != expected
        ]
        return self._report(
            good=len(finals) - len(violations),
            total=len(finals),
            violations=violations,
            metrics={"words": float(len(finals)), "wrong": float(len(violations))},
        )
