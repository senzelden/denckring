"""Perverb — graft a proverb prefix onto a different proverb's suffix.

ADR 0048: corpus membership and editorial seams are explicit; this checks the
hybrid saying, not the literary merit of writing inspired by it.
"""

from __future__ import annotations

import unicodedata

from pydantic import Field

from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams, plain
from denckring.core.errors import MissingCapability, NoCandidateWord
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register


class PerverbParams(SourceParams):
    donor: str = Field(description="A different saying from the pack's proverb corpus.")


class PerverbApplyParams(PerverbParams, ApplyParams):
    pass


def _words(text: str, pack: LanguagePack) -> tuple[str, ...]:
    # NFC first, matching core/bilingual.words(): an NFD-typed saying (a
    # combining-mark input) must casefold the same as its NFC form, or it can
    # fail to match a corpus entry it should match.
    return tuple(word.casefold() for word in pack.tokenize(unicodedata.normalize("NFC", text)))


def _hybrid(source: str, donor: str, pack: LanguagePack) -> str | None:
    # `ProverbCorpus` is optional and not part of the stable `LanguagePack`
    # contract, so a pack can declare `corpus.proverbs` without implementing
    # the method. A three-arg `getattr` turns that mismatch into the same
    # `MissingCapability` a caller gets from a pack that never claimed the
    # capability, instead of a bare `AttributeError` (core/errors.py: no error
    # is silent).
    #
    # Deliberately not cached across calls: an earlier attempt keyed a module-
    # level cache on `pack.lang`, which broke
    # `test_requires_honesty.py::test_every_declared_capability_is_reached_by_its_fixtures`
    # — that guard wraps a fresh pack instance per fixture and spies on
    # `pack.proverbs()`, and a cache hit from an *different*, earlier-called
    # instance means the spied instance never sees the call it declares.
    # Today's 3-entry corpus makes the recompute free; a real cache would need
    # to key on pack identity, not `pack.lang`, to keep that guard honest.
    proverbs = getattr(pack, "proverbs", None)
    if proverbs is None:
        raise MissingCapability("perverb", pack.lang, "corpus.proverbs")
    corpus = {_words(f"{left} {right}", pack): (left, right) for left, right in proverbs()}
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
