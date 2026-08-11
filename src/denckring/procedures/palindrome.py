"""Palindrome — the text reads identically in both directions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans


class PalindromeParams(BaseModel):
    unit: Literal["letter", "word"] = Field(default="letter", description="What is mirrored.")


@register
class Palindrome(BaseProcedure[PalindromeParams]):
    """Case, spacing and punctuation are ignored; only the letters mirror."""

    id = "palindrome"

    @classmethod
    def params_model(cls) -> type[PalindromeParams]:
        return PalindromeParams

    def _check(self, text: str, pack: LanguagePack, params: PalindromeParams) -> Report:
        if params.unit == "letter":
            spans = letter_spans(text, pack)
        else:
            spans = [
                (offset, "".join(ch for _, ch in letter_spans(word, pack)))
                for offset, word in word_spans(text, pack)
            ]
        values = [value for _, value in spans]
        mirrored = list(reversed(values))
        violations = [
            Violation(
                rule="mirror_mismatch",
                offset=spans[index][0],
                found=values[index],
                expected=mirrored[index],
            )
            for index in range(len(values))
            if values[index] != mirrored[index]
        ]
        return self._report(
            good=len(values) - len(violations),
            total=len(values),
            violations=violations,
            metrics={"units": float(len(values)), "mismatches": float(len(violations))},
        )
