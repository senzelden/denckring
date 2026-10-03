"""Consonantal lipogram — a whole group of consonants is banned."""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, single_letter


class ConsonantalLipogramParams(DiacriticParams):
    forbidden: str = Field(
        description="The consonants the text must avoid.",
        # A set of letters, not a word: a hint renders "st" as `"s", "t"`.
        json_schema_extra={"x-denckring-show": "letters"},
    )

    @field_validator("forbidden")
    @classmethod
    def _letters_only(cls, value: str) -> str:
        if not value or not value.isalpha():
            raise ValueError("forbidden must be one or more alphabetic characters")
        return value.lower()


@register
class ConsonantalLipogram(BaseProcedure[ConsonantalLipogramParams]):
    """The lipogram widened from one letter to a set."""

    id = "consonantal_lipogram"
    rules = ("forbidden_letter",)

    @classmethod
    def params_model(cls) -> type[ConsonantalLipogramParams]:
        return ConsonantalLipogramParams

    def _check(self, text: str, pack: LanguagePack, params: ConsonantalLipogramParams) -> Report:
        # Folded the same way the text is, as `lipogram` and `bivocalic` fold
        # theirs: unfolded, `forbidden="ç"` never matched a folded letter and
        # any text at all was vacuously satisfied (ADR 0035, D3).
        folded = [
            single_letter(
                ch,
                pack,
                fold=params.fold_diacritics,
                procedure_id=self.id,
                field="forbidden",
                whole=params.forbidden,
            )
            for ch in params.forbidden
        ]
        banned = set(folded)
        expected = f"any letter outside {''.join(folded)!r}"
        letters = letter_spans(text, pack, fold=params.fold_diacritics)
        violations = [
            Violation(
                rule="forbidden_letter",
                offset=offset,
                found=ch,
                expected=expected,
            )
            for offset, ch in letters
            if ch in banned
        ]
        return self._report(
            good=len(letters) - len(violations),
            total=len(letters),
            violations=violations,
            metrics={"letters": float(len(letters)), "hits": float(len(violations))},
        )
