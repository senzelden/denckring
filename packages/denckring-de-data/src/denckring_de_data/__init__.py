"""German lexicon data for denckring.

Installing this package gives the German pack the two lexical capabilities the
English pack has had since ADR 0015: `lexicon.words` and `lexicon.nouns`.
Nothing branches on whether it is present — the same procedures answer the same
calls, in a second language.

The data is Wikidata Lexemes, CC0. See LICENSE-WIKIDATA.
"""

from __future__ import annotations

import gzip
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import ClassVar

from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    LETTER_SHAPES,
    NOUNS,
    TOKENS,
    WORDS,
)
from denckring.lang.de import GermanPack

NOUNS_PATH = Path(str(files("denckring_de_data") / "data" / "nouns.txt.gz"))
WORDS_PATH = Path(str(files("denckring_de_data") / "data" / "words.txt.gz"))

__version__ = "0.1.0"


def _read(path: Path) -> tuple[str, ...]:
    """Every line of a gzipped list.

    A truncated file raises rather than returning a short list: a short noun
    list makes N+7 quietly wrong, and a wrong answer is worse than an exception.
    """
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return tuple(line for line in handle.read().split("\n") if line)


@lru_cache(maxsize=1)
def noun_list() -> tuple[str, ...]:
    """Every noun lemma, in dictionary order, capitalised as German writes them."""
    return _read(NOUNS_PATH)


@lru_cache(maxsize=1)
def noun_positions() -> dict[str, int]:
    return {word.casefold(): index for index, word in enumerate(noun_list())}


@lru_cache(maxsize=1)
def known_words() -> frozenset[str]:
    """Membership, from every inflected form of every German lexeme.

    Deliberately broad, in a way callers inherit: it answers "could this be a
    German word" rather than "is this in a dictionary of standard German", and
    procedures resting on it inherit that. The same caveat ADR 0015 recorded for
    English.
    """
    return frozenset(_read(WORDS_PATH))


class GermanDataPack(GermanPack):
    """German with a lexicon behind it."""

    capabilities: ClassVar[frozenset[str]] = frozenset(
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, NOUNS, WORDS}
    )

    def is_word(self, word: str) -> bool:
        return self._lemma(word) in known_words()

    def nouns(self) -> tuple[str, ...]:
        return noun_list()

    def noun_index(self, word: str) -> int | None:
        return noun_positions().get(self._lemma(word))

    @staticmethod
    def _lemma(word: str) -> str:
        """Casefold, and keep umlauts and ß.

        English strips to ASCII here. German must not: `fold_diacritics` would
        collide `Bär` with `Bar`, and ADR 0009 makes folding a parameter of the
        procedure rather than a property of the lexicon.
        """
        return "".join(ch for ch in word.casefold() if ch.isalpha())
