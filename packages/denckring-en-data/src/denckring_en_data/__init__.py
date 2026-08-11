"""English pronunciation data for denckring.

Installing this package replaces the core pack's spelling heuristic with lookups
in the CMU Pronouncing Dictionary. Nothing branches on whether it is present: the
same procedures answer the same calls, more accurately, and the `estimated_words`
metric on every syllabic report shows how much was still guessed.
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import ClassVar

from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    LETTER_SHAPES,
    PHONEMES,
    SYLLABLES,
    SYLLABLES_DICTIONARY,
    SYLLABLES_HEURISTIC,
    TOKENS,
)
from denckring.lang.en import EnglishPack

DICTIONARY_PATH = Path(str(files("denckring_en_data") / "data" / "cmudict.dict"))

__version__ = "0.1.0"


@lru_cache(maxsize=1)
def pronunciations() -> dict[str, list[str]]:
    """Word to phonemes, first pronunciation only.

    CMUdict lists variants as `word(2)`, `word(3)` and so on. The first entry is
    the one taken, so a count is deterministic; the alternatives matter for rhyme
    and are left for that chapter.
    """
    entries: dict[str, list[str]] = {}
    for line in DICTIONARY_PATH.read_text(encoding="utf-8").splitlines():
        head, _, rest = line.partition(" ")
        if not rest or head.endswith(")"):
            continue
        entries.setdefault(head.lower(), rest.split())
    return entries


class EnglishDataPack(EnglishPack):
    """English with a pronouncing dictionary behind it."""

    lang: ClassVar[str] = "en"  # type: ignore[assignment]
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {
            TOKENS,
            ALPHABET,
            FOLD_DIACRITICS,
            LETTER_SHAPES,
            SYLLABLES_HEURISTIC,
            SYLLABLES_DICTIONARY,
            SYLLABLES,
            PHONEMES,
        }
    )

    def syllable_count(self, word: str) -> tuple[int, bool]:
        """Exact when the dictionary knows the word, estimated otherwise."""
        letters = "".join(ch for ch in self.fold_diacritics(word) if ch.isalpha())
        phones = pronunciations().get(letters)
        if phones is None:
            return super().syllable_count(word)
        return sum(1 for phone in phones if phone[-1].isdigit()), True

    def phonemes(self, word: str) -> list[str]:
        """The word's phonemes, or raise if the dictionary does not know it."""
        from denckring.core.errors import MissingCapability

        letters = "".join(ch for ch in self.fold_diacritics(word) if ch.isalpha())
        phones = pronunciations().get(letters)
        if phones is None:
            raise MissingCapability(f"<word {word!r}>", self.lang, PHONEMES)
        return phones


__all__ = ["DICTIONARY_PATH", "EnglishDataPack", "pronunciations"]
