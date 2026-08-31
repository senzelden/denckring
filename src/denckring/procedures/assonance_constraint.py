"""Assonance — a vowel sound repeated across the words of a line.

Unlike `alliterative_verse`, this row declares `phonemes`, so it compares vowel
phonemes rather than written vowels and reads *rain* and *stays* as assonant.

`pack.phonemes` is checked on every word of every line, not only line endings, and
it raises `MissingCapability` for a word the pronouncing dictionary does not carry.
On an ordinary text that is a routine event rather than an exceptional one — the
same situation `word_stress` in `core.prosody` handles for metre scanning — so a
word whose phonemes cannot be resolved is skipped rather than treated as fatal, and
counted in the `estimated_words` metric the metre-scanning rows already report.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.errors import MissingCapability
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans, word_spans


def _vowels(word: str, pack: LanguagePack) -> list[str]:
    """Every vowel phoneme of the word, with CMUdict's stress digit removed.

    Which phonemes are vowels is the pack's question, not this row's: the test
    used to be "carries a stress digit", which is CMUdict's convention, and it
    found no vowels at all in a German transcription. `rstrip` is a no-op on a
    source that marks no stress on the segment, and stays because it is what
    makes `AY1` and `AY0` one vowel.
    """
    return [p.rstrip("012") for p in pack.phonemes(word) if pack.is_vowel_phoneme(p)]


def _vowels_or_none(word: str, pack: LanguagePack) -> list[str] | None:
    """`_vowels`, or `None` if the word is absent from the pronouncing dictionary."""
    try:
        return _vowels(word, pack)
    except MissingCapability:
        return None


class AssonanceParams(BaseModel):
    minimum: int = Field(
        default=2, ge=2, description="How many words in a line must share a vowel."
    )


@register
class AssonanceConstraint(BaseProcedure[AssonanceParams]):
    """Each line must carry `minimum` words sharing one vowel sound."""

    id = "assonance_constraint"

    @classmethod
    def params_model(cls) -> type[AssonanceParams]:
        return AssonanceParams

    def _check(self, text: str, pack: LanguagePack, params: AssonanceParams) -> Report:
        violations: list[Violation] = []
        good = 0
        total = 0
        estimated = 0
        for offset, line in line_spans(text):
            words = [word for _, word in word_spans(line, pack)]
            if not words:
                continue
            total += 1
            carried: Counter[str] = Counter()
            for word in words:
                vowels = _vowels_or_none(word, pack)
                if vowels is None:
                    estimated += 1
                    continue
                carried.update(set(vowels))
            best, count = carried.most_common(1)[0] if carried else ("", 0)
            if count >= params.minimum:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="no_repeated_vowel",
                        offset=offset,
                        found=f"{count} on {best!r}" if best else "no vowels found",
                        expected=f"{params.minimum} words sharing a vowel",
                    )
                )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"lines": float(total), "estimated_words": float(estimated)},
        )
