"""French. A built-in default, exactly like English and German (ADR 0022).

Carries no data files. A row needing only `tokens`, `alphabet`,
`fold_diacritics` or `letter_shapes` runs in French; one needing a lexicon
fails on the capability it lacks rather than on the language, which is the
whole reason this pack exists.
"""

from __future__ import annotations

from typing import ClassVar

from denckring.core.protocol import Lang
from denckring.lang.base import ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, TOKENS, BasePack

#: The 26 base letters. The accented forms are decorated members of these, not
#: additional letters — the same reading `de.py` takes of the umlauts.
_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
#: `y` is a vowel in French, which is why this set is not English's.
_VOWELS = frozenset("aeiouyàâäéèêëîïôöùûüÿ")
_ASCENDERS = frozenset("bdfhklt")
_DESCENDERS = frozenset("fgjpqy")

#: `ß` folds to `ss` for free because `casefold()` maps it. These two have no
#: casefold mapping and no NFKD decomposition, so `BasePack.fold_diacritics`
#: returns them whole — and an unfolded `œ` is one letter that no anagram of
#: `oeuvre` could ever match. ADR 0009 keeps folding a parameter, so a caller
#: who wants `œ` to stay a letter passes `fold_diacritics=False`.
_LIGATURES = {"œ": "oe", "æ": "ae"}


class FrenchPack(BasePack):
    """French, with no data files and the same four capabilities as German."""

    lang: ClassVar[Lang] = "fr"
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES}
    )

    def alphabet(self) -> str:
        return _ALPHABET

    def vowels(self) -> frozenset[str]:
        return _VOWELS

    def ascenders(self) -> frozenset[str]:
        return _ASCENDERS

    def descenders(self) -> frozenset[str]:
        return _DESCENDERS

    def fold_diacritics(self, ch: str) -> str:
        return "".join(_LIGATURES.get(c, c) for c in super().fold_diacritics(ch))
