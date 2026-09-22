"""Perverb — graft a proverb prefix onto a different proverb's suffix.

ADR 0048: corpus membership and editorial seams are explicit; this checks the
hybrid saying, not the literary merit of writing inspired by it.
"""

from __future__ import annotations

from typing import cast

from pydantic import Field

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams, plain
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import LanguagePack, Produced, ProverbCorpus, Report, Violation
from denckring.core.registry import register


class PerverbParams(SourceParams):
    donor: str = Field(description="A different saying from the pack's proverb corpus.")


class PerverbApplyParams(PerverbParams, ApplyParams):
    pass


def _words(text: str, pack: LanguagePack) -> tuple[str, ...]:
    return tuple(word.casefold() for word in pack.tokenize(text))


def _hybrid(source: str, donor: str, pack: LanguagePack) -> str | None:
    corpus = {
        _words(f"{left} {right}", pack): (left, right)
        for left, right in cast(ProverbCorpus, pack).proverbs()
    }
    first, second = _words(source, pack), _words(donor, pack)
    if first == second or first not in corpus or second not in corpus:
        return None
    return f"{corpus[first][0]} {corpus[second][1]}"


@register
class Perverb(ConstructiveProcedure[PerverbParams, PerverbApplyParams]):
    """The source supplies the prefix; the donor supplies the suffix."""

    id = "perverb"

    @classmethod
    def params_model(cls) -> type[PerverbParams]:
        return PerverbParams

    @classmethod
    def apply_params_model(cls) -> type[PerverbApplyParams]:
        return PerverbApplyParams

    def _check(self, text: str, pack: LanguagePack, params: PerverbParams) -> Report:
        expected = _hybrid(params.source, params.donor, pack)
        if expected is None:
            violation = Violation(
                rule="unresolved_proverb_pair",
                found="unknown or identical sayings",
                expected="two different sayings in the pack's proverb corpus",
            )
        elif _words(text, pack) != _words(expected, pack):
            violation = Violation(rule="not_the_graft", found=text, expected=expected)
        else:
            return self._report(good=1, total=1, violations=[], metrics={"grafts": 1.0})
        return self._report(good=0, total=1, violations=[violation], metrics={"grafts": 0.0})

    def _produce(self, text: str, pack: LanguagePack, params: PerverbApplyParams) -> Produced:
        expected = _hybrid(text, params.donor, pack)
        if expected is None:
            raise NoCandidateWord(self.id, "source and donor must be different corpus sayings")
        return plain([expected])
