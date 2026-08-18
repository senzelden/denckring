"""Alliterative verse — most words in a line beginning on the same sound.

**Initial letter stands in for initial sound.** The catalogue row requires only
`tokens` and `fold_diacritics`, not `phonemes`, so this compares first letters. That
is an approximation: it reads *knight* and *king* as alliterating, which Old English
metre would not. It is recorded here rather than hidden, and the row would need
`phonemes` in `requires` to do better.
"""

from __future__ import annotations

from collections import Counter

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans, word_spans


class AlliterativeVerseParams(DiacriticParams):
    minimum: int = Field(
        default=3, ge=2, description="How many words in a line must share an initial."
    )


@register
class AlliterativeVerse(BaseProcedure[AlliterativeVerseParams]):
    """Each line must carry `minimum` words on one initial."""

    id = "alliterative_verse"

    @classmethod
    def params_model(cls) -> type[AlliterativeVerseParams]:
        return AlliterativeVerseParams

    def _check(self, text: str, pack: LanguagePack, params: AlliterativeVerseParams) -> Report:
        violations: list[Violation] = []
        good = 0
        total = 0
        for offset, line in line_spans(text):
            words = [word for _, word in word_spans(line, pack)]
            if not words:
                continue
            total += 1
            initials = Counter(
                pack.fold_diacritics(word[0]).casefold()
                if params.fold_diacritics
                else word[0].casefold()
                for word in words
                if word
            )
            best, count = initials.most_common(1)[0]
            if count >= params.minimum:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="too_few_alliterating",
                        offset=offset,
                        found=f"{count} on {best!r}",
                        expected=f"{params.minimum} sharing an initial",
                    )
                )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"lines": float(total)},
        )
