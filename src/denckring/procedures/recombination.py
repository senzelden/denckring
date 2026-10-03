"""Recombination — the source's sentences in a new order, unaltered."""

from __future__ import annotations

import random
import re
from collections import Counter

from denckring.core.base import (
    ApplyParams,
    ConstructiveProcedure,
    IdentityParams,
    SeedParams,
    SourceParams,
    plain,
)
from denckring.core.errors import InputTooShort, counted
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.source_compare import unchanged
from denckring.core.text import letter_spans

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class RecombinationParams(SourceParams, IdentityParams):
    pass


def sentences(text: str) -> list[str]:
    return [s.strip().casefold() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def _reorder_changes_letters(source: str, pack: LanguagePack) -> bool:
    """Whether some order of the source's sentences has other letters than the copy.

    Decided on what `unchanged` compares, each sentence's letters, not on the
    sentences `_check` counts: `It rains.` and `It rains!` are two sentences there
    and one letter string here, so swapping them is no other answer. Reordering
    changes the concatenation exactly when two of the strings do not commute
    (`no` + `nono` does), the case `No. No no.` needs.
    """
    words = [
        "".join(ch for _, ch in letter_spans(piece, pack, fold=False))
        for piece in SENTENCE_SPLIT.split(source.strip())
    ]
    return any(a + b != b + a for i, a in enumerate(words) for b in words[i + 1 :])


class RecombinationApplyParams(ApplyParams, RecombinationParams, SeedParams):
    pass


@register
class Recombination(ConstructiveProcedure[RecombinationParams, RecombinationApplyParams]):
    """The same sentences, redistributed, with none rewritten."""

    id = "recombination"
    rules = ("sentence_dropped", "sentence_not_in_source", "unchanged")

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
        copy = unchanged(
            text,
            params.source,
            pack,
            allow=params.allow_identity,
            alternative=lambda: _reorder_changes_letters(params.source, pack),
            fold=False,
        )
        return self._report(
            good=shared,
            total=total + len(copy),
            violations=violations + copy,
            metrics={"sentences": float(sum(candidate.values()))},
        )

    @classmethod
    def apply_params_model(cls) -> type[RecombinationApplyParams]:
        return RecombinationApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: RecombinationApplyParams) -> Produced:
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
        return plain([" ".join(parts + tail)])
