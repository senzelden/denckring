"""Snowball — each word is one letter longer than the last."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.fields import param
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans


class SnowballParams(BaseModel):
    start: int | None = Field(
        default=None,
        description="Length of the first word; inferred if unset.",
        json_schema_extra=param("inferred"),
    )
    step: int = Field(
        default=1,
        description="Letters added per word; negative to shrink.",
        json_schema_extra=param("task"),
    )


def rhopalic_violations(
    text: str, pack: LanguagePack, start: int | None, step: int
) -> tuple[list[Violation], int]:
    """Words whose length departs from the arithmetic progression, and the word count.

    Shared with `reverse_snowball`, which is the same walk with a negative step.

    A word's length is its letters, not its characters (ADR 0058). The word pattern
    keeps an apostrophe between letters inside a word, so `len` read `I'm` as three
    while a writer told to count letters counts two. `letter_spans` is the notion of
    a letter every letter row shares; unfolded, so `ß` stays one letter.
    """
    words = [
        (offset, word, len(letter_spans(word, pack, fold=False)))
        for offset, word in word_spans(text, pack)
    ]
    if not words:
        return [], 0
    first = start if start is not None else words[0][2]
    violations = [
        Violation(
            rule="wrong_word_length",
            offset=offset,
            found=word,
            expected=f"{first + index * step} letters",
        )
        for index, (offset, word, letters) in enumerate(words)
        if letters != first + index * step
    ]
    return violations, len(words)


@register
class Snowball(BaseProcedure[SnowballParams]):
    """Ausonius's rhopalic line, growing one letter at a time."""

    id = "snowball"
    rules = ("wrong_word_length",)

    @classmethod
    def params_model(cls) -> type[SnowballParams]:
        return SnowballParams

    def _check(self, text: str, pack: LanguagePack, params: SnowballParams) -> Report:
        violations, words = rhopalic_violations(text, pack, params.start, params.step)
        return self._report(
            good=words - len(violations),
            total=words,
            violations=violations,
            metrics={"words": float(words), "wrong": float(len(violations))},
        )
