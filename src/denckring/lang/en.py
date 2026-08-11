"""English. Ships in core with no data files and no heavy dependencies."""

from __future__ import annotations

import re
from typing import ClassVar

from denckring.core.protocol import Lang
from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    LETTER_SHAPES,
    SYLLABLES_HEURISTIC,
    TOKENS,
    BasePack,
)

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_VOWELS = frozenset("aeiou")
_ASCENDERS = frozenset("bdfhklt")
_DESCENDERS = frozenset("fgjpqy")
_VOWEL_GROUP = re.compile(r"[aeiouy]+")
#: "-le" after a consonant is its own syllable: ta-ble, but not ale.
_SYLLABIC_LE = re.compile(r"[^aeiouy]le$")


class EnglishPack(BasePack):
    """The one pack that ships in core."""

    lang: ClassVar[Lang] = "en"
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, SYLLABLES_HEURISTIC}
    )

    def alphabet(self) -> str:
        return _ALPHABET

    def vowels(self) -> frozenset[str]:
        return _VOWELS

    def ascenders(self) -> frozenset[str]:
        return _ASCENDERS

    def descenders(self) -> frozenset[str]:
        return _DESCENDERS

    def syllable_count(self, word: str) -> tuple[int, bool]:
        """Estimate syllables from spelling. Never reports itself as exact.

        Count vowel groups, drop a silent terminal "e", add back a syllabic
        "-le", and never return less than one. This is the standard spelling
        heuristic and it is wrong for a measurable share of English, which is
        why the second element of the pair is always False and why installing
        `denckring[en]` replaces it with dictionary lookups.
        """
        letters = "".join(ch for ch in self.fold_diacritics(word) if ch.isalpha())
        if not letters:
            return 0, False
        groups = _VOWEL_GROUP.findall(letters)
        count = len(groups)
        if letters.endswith("e") and count > 1 and not _SYLLABIC_LE.search(letters):
            count -= 1
        if _SYLLABIC_LE.search(letters):
            count = max(count, len(_VOWEL_GROUP.findall(letters[:-2])) + 1)
        return max(count, 1), False
