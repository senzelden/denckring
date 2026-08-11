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
    STRESS,
    SYLLABLES,
    SYLLABLES_DICTIONARY,
    SYLLABLES_HEURISTIC,
    TOKENS,
)
from denckring.lang.en import EnglishPack

DICTIONARY_PATH = Path(str(files("denckring_en_data") / "data" / "cmudict.dict"))

__version__ = "0.1.0"


@lru_cache(maxsize=1)
def variants() -> dict[str, list[list[str]]]:
    """Word to every pronunciation CMUdict lists for it.

    Variants are written `word(2)`, `word(3)` and so on. They matter: Shakespeare
    needs the three-syllable `tem-per-ate`, which CMUdict lists second because the
    compressed modern form comes first.
    """
    entries: dict[str, list[list[str]]] = {}
    for line in DICTIONARY_PATH.read_text(encoding="utf-8").splitlines():
        head, _, rest = line.partition(" ")
        if not rest:
            continue
        word = head.split("(")[0].lower()
        entries.setdefault(word, []).append(rest.split())
    return entries


@lru_cache(maxsize=1)
def pronunciations() -> dict[str, list[str]]:
    """Word to its first listed pronunciation, for callers wanting one answer."""
    return {word: forms[0] for word, forms in variants().items()}


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
            STRESS,
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
        return _phones_or_raise(self, word)

    def rhyme_key(self, word: str) -> str:
        """The first pronunciation's rhyme key."""
        return _rhyme_of(_phones_or_raise(self, word))

    def rhyme_keys(self, word: str) -> list[str]:
        """Every pronunciation's rhyme key. Two words rhyme if any pair matches."""
        return list(dict.fromkeys(_rhyme_of(f) for f in _forms_or_raise(self, word)))

    def stress_pattern(self, word: str) -> str:
        """The first pronunciation's stress pattern."""
        return _stress_of(_phones_or_raise(self, word))

    def stress_patterns(self, word: str) -> list[str]:
        """Every pronunciation's stress pattern, longest first.

        A line scans if some combination of listed pronunciations fits, which is
        the same satisfiability principle the free monosyllable rests on.
        """
        found = dict.fromkeys(_stress_of(f) for f in _forms_or_raise(self, word))
        return sorted(found, key=len, reverse=True)


def _forms_or_raise(pack: EnglishDataPack, word: str) -> list[list[str]]:
    from denckring.core.errors import MissingCapability

    letters = "".join(ch for ch in pack.fold_diacritics(word) if ch.isalpha())
    forms = variants().get(letters)
    if not forms:
        # Guessing a pronunciation is the silent wrongness ADR 0004 forbids.
        raise MissingCapability(f"<word {word!r}>", pack.lang, PHONEMES)
    return forms


def _phones_or_raise(pack: EnglishDataPack, word: str) -> list[str]:
    return _forms_or_raise(pack, word)[0]


def _stress_of(phones: list[str]) -> str:
    marks = [p[-1] for p in phones if p[-1].isdigit()]
    if len(marks) <= 1:
        return "?" * len(marks)
    return "".join("?" if mark == "2" else mark for mark in marks)


def _rhyme_of(phones: list[str]) -> str:
    primary = [i for i, p in enumerate(phones) if p.endswith("1")]
    if not primary:
        primary = [i for i, p in enumerate(phones) if p[-1].isdigit()]
    if not primary:
        return " ".join(phones)
    return " ".join(phones[primary[-1] :])


__all__ = ["DICTIONARY_PATH", "EnglishDataPack", "pronunciations"]
