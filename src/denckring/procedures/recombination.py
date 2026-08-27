"""Recombination — the source's sentences in a new order, unaltered."""

from __future__ import annotations

import random
import re
from collections import Counter

from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams, SourceParams
from denckring.core.errors import InputTooShort, counted
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

    def _produce(
        self, text: str, pack: LanguagePack, params: RecombinationApplyParams
    ) -> list[str]:
        """The same sentences in another order, none rewritten.

        A permutation and nothing else: the checker compares multisets, so
        dropping or joining a sentence here would produce something its own
        verdict rejects.
        """
        chooser = random.Random(params.seed)
        parts = [s.strip() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]

        # SENTENCE_SPLIT only splits *after* a terminator, so a fragment with
        # none is the tail of the text, not a sentence to permute. Shuffling it
        # in would let the join glue it onto whatever ends up as its new
        # neighbour — `'a'` next to a lone `'.'` becomes `'a .'` — and that
        # merged string re-splits into a different multiset than the one
        # shuffled, which is exactly what `_check` compares against. Pinning
        # the tail in final position keeps the join invertible.
        tail = [parts.pop()] if parts and not parts[-1].endswith((".", "!", "?")) else []
        if len(parts) < 2:
            # "sentence" here would undercount: an unterminated single line
            # pops its whole content into `tail`, leaving `parts` empty, and
            # "found 0 sentences" reads as a claim about the text rather than
            # about what survived the pop. "complete sentence" names the unit
            # this count actually is.
            raise InputTooShort(
                self.id,
                needed="more than one sentence to recombine",
                found=counted(len(parts), "complete sentence"),
            )
        chooser.shuffle(parts)
        return [" ".join(parts + tail)]
