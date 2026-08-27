"""Cut-up — the source cut into words and reassembled."""

from __future__ import annotations

import random
from collections import Counter

from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


class CutUpParams(SourceParams):
    pass


class CutUpApplyParams(CutUpParams, SeedParams, ApplyParams):
    """What the scissors accept. `CutUpParams` alone could not carry `seed`,
    because `seed` was a signature keyword no params model ever saw."""


@register
class CutUp(ConstructiveProcedure[CutUpParams, CutUpApplyParams]):
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

    @classmethod
    def apply_params_model(cls) -> type[CutUpApplyParams]:
        return CutUpApplyParams

    def _apply(self, text: str, pack: LanguagePack, params: CutUpApplyParams) -> str:
        """Shuffle the source's own words. Deterministic under a fixed seed."""
        words = [word for _, word in word_spans(text, pack)]
        random.Random(params.seed).shuffle(words)
        return " ".join(words)
