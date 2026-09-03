"""Pangrammatic lipogram — every letter but one, and that one never."""

from __future__ import annotations

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, single_letter


class PangrammaticLipogramParams(DiacriticParams):
    forbidden: str = Field(default="e", description="The one letter that must not appear.")

    @field_validator("forbidden")
    @classmethod
    def _single_letter(cls, value: str) -> str:
        if len(value) != 1 or not value.isalpha():
            raise ValueError("forbidden must be a single alphabetic character")
        return value.lower()


@register
class PangrammaticLipogram(BaseProcedure[PangrammaticLipogramParams]):
    """A pangram and a lipogram at once, so an empty text fails on both counts.

    Like `pangram`, this requires something rather than forbidding it, so it
    builds its Report directly instead of going through `_report`.
    """

    id = "pangrammatic_lipogram"

    @classmethod
    def params_model(cls) -> type[PangrammaticLipogramParams]:
        return PangrammaticLipogramParams

    def _check(self, text: str, pack: LanguagePack, params: PangrammaticLipogramParams) -> Report:
        # Folded the same way the text is — ADR 0035, D3; Known remaining.
        # Unfolded, `forbidden="ä"` never matched a folded letter, so `hits`
        # stayed empty and `pack.alphabet()` (already unaccented) was
        # unaffected by excluding it either.
        forbidden = single_letter(
            params.forbidden,
            pack,
            fold=params.fold_diacritics,
            procedure_id=self.id,
            field="forbidden",
        )
        required = [ch for ch in pack.alphabet() if ch != forbidden]
        present = {ch for _, ch in letter_spans(text, pack, fold=params.fold_diacritics)}
        missing = [ch for ch in required if ch not in present]
        hits = [
            (offset, ch)
            for offset, ch in letter_spans(text, pack, fold=params.fold_diacritics)
            if ch == forbidden
        ]
        violations = [
            Violation(rule="missing_letter", offset=None, found="", expected=ch) for ch in missing
        ]
        violations += [
            Violation(
                rule="forbidden_letter",
                offset=offset,
                found=ch,
                expected=f"any letter but {forbidden!r}",
            )
            for offset, ch in hits
        ]
        coverage = (len(required) - len(missing)) / len(required)
        purity = 0.0 if hits else 1.0
        score = coverage * purity
        return Report(
            procedure=self.id,
            satisfied=score == 1.0,
            score=score,
            violations=violations,
            metrics={"coverage": coverage, "forbidden_hits": float(len(hits))},
        )
