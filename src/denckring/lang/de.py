"""German. Ships in core, discovered through the entry-point group.

Batch 1 needs no lexicon and no hyphenation, so this pack carries no data and
core stays permissive. When German acquires a noun list, its licence decides
whether the data — not this module — moves behind an extra.
"""

from __future__ import annotations

from typing import ClassVar

from denckring.core.protocol import Lang
from denckring.lang.base import ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, TOKENS, BasePack

#: The 26 base letters. Traditional German pangrams satisfy exactly these — the
#: umlauts and ß count as decorated forms, not as alphabet members.
_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_VOWELS = frozenset("aeiouäöü")
#: ß is named here because its written form carries an ascender. ä, ö and ü need
#: no entry: BasePack.exceeds_x_height catches any character with a mark above.
_ASCENDERS = frozenset("bdfhklt") | {"ß"}
_DESCENDERS = frozenset("fgjpqy")


class GermanPack(BasePack):
    """German, with no data files and the same four capabilities as English."""

    lang: ClassVar[Lang] = "de"
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
