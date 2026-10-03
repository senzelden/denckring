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
#: A final "-es" or "-ed" whose `e` is a stem's silent one: awake-s, hope-d. Not
#: after a sibilant (fa-ces, wish-es), nor "-ed" after t or d (want-ed), where
#: the suffix is a syllable; nor after a consonant and a liquid (ta-bles,
#: hun-dred), the syllabic ending `_SYLLABIC_LE` keeps for "-le". Measured on
#: CMUdict: agreement on "-es" words rose from 54% to 89%, on "-ed" from 42% to
#: 91%, and on every word from 83.4% to 87.0% (ADR 0012's measured floor). Not a
#: pure gain: 450 words read right before and wrong now, against 4,626 the other
#: way. They are mostly "-ires", "-ired", "-ates" and adjectival "-ed" (`tired`,
#: `fires`, `naked`, `wicked`, `affiliates`), read a syllable short. Only a
#: core-only install, or a word the dictionary and its stems both lack, sees it.
_SILENT_E_SUFFIX = re.compile(r"(?:[^aeiouyszxcgh]es|[^aeiouytd]ed)$")
_SYLLABIC_LIQUID_SUFFIX = re.compile(r"[^aeiouy][lr]e[sd]$")


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

        Count vowel groups, drop a silent terminal "e" (also when an "-s" or
        "-d" follows it), add back a syllabic "-le", and never return less than
        one. This is the standard spelling
        heuristic and it is wrong for a measurable share of English, which is
        why the second element of the pair is always False and why installing
        `denckring[en]` replaces it with dictionary lookups.
        """
        letters = "".join(ch for ch in self.fold_diacritics(word) if ch.isalpha())
        if not letters:
            return 0, False
        groups = _VOWEL_GROUP.findall(letters)
        count = len(groups)
        final_e = letters.endswith("e") and not _SYLLABIC_LE.search(letters)
        suffixed_e = bool(_SILENT_E_SUFFIX.search(letters)) and not _SYLLABIC_LIQUID_SUFFIX.search(
            letters
        )
        if (final_e or suffixed_e) and count > 1:
            count -= 1
        if _SYLLABIC_LE.search(letters):
            count = max(count, len(_VOWEL_GROUP.findall(letters[:-2])) + 1)
        return max(count, 1), False
