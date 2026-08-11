"""Recombination — the source's sentences in a new order, unaltered."""

from __future__ import annotations

import re
from collections import Counter

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class RecombinationParams(SourceParams):
    pass


def sentences(text: str) -> list[str]:
    return [s.strip().casefold() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]


@register
class Recombination(BaseProcedure[RecombinationParams]):
    """The same sentences, redistributed, with none rewritten."""

    id = "recombination"

    @classmethod
    def params_model(cls) -> type[RecombinationParams]:
        return RecombinationParams

    def _check(self, text: str, pack: LanguagePack, params: RecombinationParams) -> Report:
        candidate = Counter(sentences(text))
        source = Counter(sentences(params.source))
        violations: list[Violation] = []
        for sentence, count in sorted(candidate.items()):
            if count > source[sentence]:
                violations.append(
                    Violation(
                        rule="sentence_not_in_source",
                        offset=None,
                        found=sentence,
                        expected=f"at most {source[sentence]} occurrences",
                    )
                )
        for sentence, count in sorted(source.items()):
            if candidate[sentence] < count:
                violations.append(
                    Violation(
                        rule="sentence_dropped",
                        offset=None,
                        found=f"{candidate[sentence]} occurrences",
                        expected=sentence,
                    )
                )
        shared = sum((candidate & source).values())
        total = max(sum(candidate.values()), sum(source.values()))
        return self._report(
            good=shared,
            total=total,
            violations=violations,
            metrics={"sentences": float(sum(candidate.values()))},
        )
