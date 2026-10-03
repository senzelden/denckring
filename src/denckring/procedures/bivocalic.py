"""Bivocalic — the text uses at most two of the vowels."""

from __future__ import annotations

from collections import Counter

from pydantic import Field, field_validator

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.fields import param
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, quoted_letters, single_letter

PERMITTED = 2


class BivocalicParams(DiacriticParams):
    vowels: str | None = Field(
        default=None,
        description="The two permitted vowels.",
        # A set of letters, not a word: a hint renders "ae" as `"a", "e"`.
        json_schema_extra=param("inferred", "vowels", **{"x-denckring-show": "letters"}),
    )

    @field_validator("vowels")
    @classmethod
    def _exactly_two(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != PERMITTED or not value.isalpha():
            raise ValueError("vowels must be exactly two alphabetic characters")
        return value.lower()


@register
class Bivocalic(BaseProcedure[BivocalicParams]):
    """The univocalic loosened by one: two vowels, no more."""

    id = "bivocalic"
    rules = ("foreign_vowel",)

    @classmethod
    def params_model(cls) -> type[BivocalicParams]:
        return BivocalicParams

    def _check(self, text: str, pack: LanguagePack, params: BivocalicParams) -> Report:
        vowel_set = pack.vowels()
        found = [
            (offset, ch)
            for offset, ch in letter_spans(text, pack, fold=params.fold_diacritics)
            if ch in vowel_set
        ]
        # Each of the two folded as the text was — ADR 0035, D3. `vowels="äö"`
        # was unsatisfiable in German for want of this.
        if params.vowels is not None:
            permitted = {
                single_letter(
                    ch,
                    pack,
                    fold=params.fold_diacritics,
                    procedure_id=self.id,
                    field="vowels",
                    whole=params.vowels,
                )
                for ch in params.vowels
            }
        else:
            permitted = {ch for ch, _ in Counter(ch for _, ch in found).most_common(PERMITTED)}
        violations = [
            Violation(
                rule="foreign_vowel",
                offset=offset,
                found=ch,
                expected=f"one of {quoted_letters(sorted(permitted))}",
            )
            for offset, ch in found
            if ch not in permitted
        ]
        return self._report(
            good=len(found) - len(violations),
            total=len(found),
            violations=violations,
            metrics={"vowel_count": float(len(found)), "distinct": float(len(permitted))},
        )
