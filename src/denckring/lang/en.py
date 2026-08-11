"""English. Ships in core with no data files and no heavy dependencies."""

from __future__ import annotations

from typing import ClassVar

from denckring.core.protocol import Lang
from denckring.lang.base import ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, TOKENS, BasePack

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_VOWELS = frozenset("aeiou")
_ASCENDERS = frozenset("bdfhklt")
_DESCENDERS = frozenset("fgjpqy")


class EnglishPack(BasePack):
    """The one pack that ships in core."""

    lang: ClassVar[Lang] = "en"
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
