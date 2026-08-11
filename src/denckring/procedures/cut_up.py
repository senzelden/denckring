"""Cut-up — the source cut into words and reassembled."""

from __future__ import annotations

import random
from collections import Counter

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


class CutUpParams(SourceParams):
    pass


class CutUpApplyParams(BaseModel):
    seed: int | None = Field(default=None, description="Fixes the shuffle.")


@register
class CutUp(BaseProcedure[CutUpParams]):
    """Every word comes from the source, with multiplicity, and none is invented.

    The order is deliberately unconstrained — rearrangement is the procedure.
    What the checker can verify is provenance: nothing appears that the scissors
    could not have produced.
    """

    id = "cut_up"

    @classmethod
    def params_model(cls) -> type[CutUpParams]:
        return CutUpParams

    def _check(self, text: str, pack: LanguagePack, params: CutUpParams) -> Report:
        available = Counter(word.casefold() for _, word in word_spans(params.source, pack))
        used: Counter[str] = Counter()
        violations: list[Violation] = []
        candidate = word_spans(text, pack)
        for offset, word in candidate:
            folded = word.casefold()
            used[folded] += 1
            if used[folded] > available[folded]:
                violations.append(
                    Violation(
                        rule="word_not_in_source",
                        offset=offset,
                        found=word,
                        expected=f"at most {available[folded]} of {folded!r}",
                    )
                )
        return self._report(
            good=len(candidate) - len(violations),
            total=len(candidate),
            violations=violations,
            metrics={
                "words": float(len(candidate)),
                "source_words": float(sum(available.values())),
            },
        )

    def apply(
        self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: object
    ) -> str:
        """Shuffle the source's own words. Deterministic under a fixed seed."""
        from denckring.lang import get_pack

        words = [word for _, word in word_spans(text, get_pack(lang))]
        random.Random(seed).shuffle(words)
        return " ".join(words)
