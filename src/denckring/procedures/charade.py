"""Charade — a word that divides into shorter words."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans

MIN_PARTS = 2


class CharadeParams(BaseModel):
    parts: int = Field(
        default=MIN_PARTS, ge=MIN_PARTS, description="Pieces each word must split into."
    )


def splits_into(letters: str, parts: int, pack: LanguagePack) -> list[str] | None:
    """The first division of `letters` into `parts` known words, or None."""
    if parts == 1:
        return [letters] if letters and pack.is_word(letters) else None
    for cut in range(1, len(letters)):
        head = letters[:cut]
        if not pack.is_word(head):
            continue
        rest = splits_into(letters[cut:], parts - 1, pack)
        if rest is not None:
            return [head, *rest]
    return None


@register
class Charade(BaseProcedure[CharadeParams]):
    """Every word must come apart into smaller words."""

    id = "charade"

    @classmethod
    def params_model(cls) -> type[CharadeParams]:
        return CharadeParams

    def _check(self, text: str, pack: LanguagePack, params: CharadeParams) -> Report:
        words = word_spans(text, pack)
        violations: list[Violation] = []
        for offset, word in words:
            letters = "".join(ch for _, ch in letter_spans(word, pack))
            if splits_into(letters, params.parts, pack) is None:
                violations.append(
                    Violation(
                        rule="does_not_divide",
                        offset=offset,
                        found=word,
                        expected=f"a word dividing into {params.parts} words",
                    )
                )
        return self._report(
            good=len(words) - len(violations),
            total=len(words),
            violations=violations,
            metrics={"words": float(len(words))},
        )
