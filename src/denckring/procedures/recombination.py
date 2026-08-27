"""Recombination — the source's sentences in a new order, unaltered."""

from __future__ import annotations

import random
import re
from collections import Counter

from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams, SourceParams
from denckring.core.errors import InputTooShort
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class RecombinationParams(SourceParams):
    pass


def sentences(text: str) -> list[str]:
    return [s.strip().casefold() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]


class RecombinationApplyParams(RecombinationParams, SeedParams, ApplyParams):
    pass


@register
class Recombination(ConstructiveProcedure[RecombinationParams, RecombinationApplyParams]):
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

    @classmethod
    def apply_params_model(cls) -> type[RecombinationApplyParams]:
        return RecombinationApplyParams

    def _apply(self, text: str, pack: LanguagePack, params: RecombinationApplyParams) -> str:
        """The same sentences in another order, none rewritten.

        A permutation and nothing else: the checker compares multisets, so
        dropping or joining a sentence here would produce something its own
        verdict rejects.
        """
        chooser = random.Random(params.seed)
        parts = [s.strip() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]
        if len(parts) < 2:
            raise InputTooShort(
                self.id,
                needed="more than one sentence to recombine",
                found=f"{len(parts)} sentence",
            )
        chooser.shuffle(parts)
        return " ".join(parts)
