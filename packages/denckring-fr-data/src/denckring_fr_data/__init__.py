"""French lexicon data for denckring.

Installing this gives the French pack `lexicon.words`, `lexicon.nouns`,
`lexicon.glosses` and `lexicon.graded_words`. Nothing branches on whether it is
present — the same procedures answer the same calls, in a third language.

Two sources, both CC BY-SA 4.0: Lexique 3.82 for membership, nouns and frequency,
and French Wiktionary for definitions. ADR 0032 records why Wikidata Lexemes,
which supplies German, could not supply French.
"""

from __future__ import annotations

import gzip
from collections.abc import Mapping, Sequence
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar, TypeVar

from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    GLOSSES,
    GRADED_WORDS,
    LETTER_SHAPES,
    NOUNS,
    TOKENS,
    WORDS,
)
from denckring.lang.fr import FrenchPack

#: What `look_up` returns is whatever the table holds, and the caller must get
#: its own type back. The same shape as `denckring_de_wiktionary.look_up`.
_V = TypeVar("_V", bound=Sequence[str])

WORDS_PATH = Path(str(files("denckring_fr_data") / "data" / "words.txt.gz"))
NOUNS_PATH = Path(str(files("denckring_fr_data") / "data" / "nouns.txt.gz"))
GRADED_WORDS_PATH = Path(str(files("denckring_fr_data") / "data" / "graded_words.txt.gz"))
GLOSSES_PATH = Path(str(files("denckring_fr_data") / "data" / "glosses.txt.gz"))

__version__ = "0.1.0"


def _read(path: Path) -> tuple[str, ...]:
    """Every line of a gzipped list.

    A truncated file raises rather than returning a short list: a short noun list
    makes N+7 quietly wrong, and a wrong answer is worse than an exception.
    """
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return tuple(line for line in handle.read().split("\n") if line)


@lru_cache(maxsize=1)
def noun_list() -> tuple[str, ...]:
    """Every noun form, in dictionary order. N+7 walks this, so order is the point."""
    return _read(NOUNS_PATH)


@lru_cache(maxsize=1)
def noun_positions() -> dict[str, int]:
    return {word.casefold(): index for index, word in enumerate(noun_list())}


@lru_cache(maxsize=1)
def known_words() -> frozenset[str]:
    """Membership, from every form Lexique carries."""
    return frozenset(_read(WORDS_PATH))


@lru_cache(maxsize=1)
def graded_words() -> Mapping[str, int]:
    """Word to band, where **larger means less common** — SCOWL's direction."""
    table: dict[str, int] = {}
    with gzip.open(GRADED_WORDS_PATH, mode="rt", encoding="utf-8") as handle:
        for line in handle:
            word, _, band = line.rstrip("\n").partition("\t")
            if band:
                table[word] = int(band)
    return table


@lru_cache(maxsize=1)
def gloss_table() -> dict[str, tuple[str, ...]]:
    """Headword to every sense's definition, in Wiktionary's order.

    Split on `" | "` rather than `"|"`, because a definition may contain a bare
    pipe and the build rejects any that contains the spaced separator.
    """
    with gzip.open(GLOSSES_PATH, mode="rt", encoding="utf-8") as handle:
        return {
            key: tuple(values.split(" | "))
            for key, _, values in (line.rstrip("\n").partition("\t") for line in handle)
            if values
        }


def look_up(table: Mapping[str, _V], word: str) -> _V | None:
    """The token as written, then case-flipped.

    French Wiktionary titles are case-sensitive, and the build stores them as
    written: `France`, `Paris` and `Toulouse` are the titles, not `france`,
    `paris`, `toulouse`. Looking a headword up through `_lemma` — which
    casefolds and drops every non-letter — therefore misses every capitalised
    and every hyphenated title. Measured over the shipped table: 261,638 of
    510,973 headwords (51.2%) were unreachable that way, 121,388 of them to case
    alone, and proper nouns are the material loss. Trying the flipped case
    recovers them, and the reverse direction recovers a proper noun someone
    lowercased.

    On the word **as written**, never `_lemma`'d: accents are meaning here, and
    folding them would collide `côte` with `cote`. Same reason ADR 0009 makes
    folding a decision of the procedure rather than of the lexicon. This is the
    shape `denckring_de_wiktionary.look_up` already uses; French diverged from it
    only by oversight, which is the same key/lookup mismatch fixed for the noun
    list in fdad0c8.
    """
    for candidate in (word, word.capitalize(), word.lower(), word.upper()):
        found = table.get(candidate)
        if found:
            return found
    return None


class FrenchDataPack(FrenchPack):
    """French with a lexicon behind it: membership, nouns, glosses and frequency.

    A fixed `ClassVar`, as on every pack but German's: German's `pack()` factory
    (`denckring_de_data`) exists because two distributions carry German data
    under two different licences and the registry allows only one `de` entry
    point to win. This distribution is the only source of French lexicon data,
    under one licence, so there is nothing for the install to choose between —
    a plain class is the honest shape.
    """

    capabilities: ClassVar[frozenset[str]] = frozenset(
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, NOUNS, WORDS, GLOSSES, GRADED_WORDS}
    )

    def is_word(self, word: str) -> bool:
        return self._lemma(word) in known_words()

    def nouns(self) -> tuple[str, ...]:
        return noun_list()

    def noun_index(self, word: str) -> int | None:
        return noun_positions().get(self._lemma(word))

    def glosses(self, word: str) -> tuple[str, ...]:
        """Every sense, or nothing. Empty rather than raising, matching English."""
        return look_up(gloss_table(), word) or ()

    def graded_words(self) -> Mapping[str, int]:
        """A read-only view over the cached table, for the reason English gives:
        the module function is `lru_cache`d and shared, so handing the dict out
        would let one caller's mutation corrupt it for all the others."""
        return MappingProxyType(graded_words())

    @staticmethod
    def _lemma(word: str) -> str:
        """Casefold, and keep accents.

        English strips to ASCII here. French must not: `fold_diacritics` would
        collide `côte` with `cote` and `pêcheur` with `pecheur`, and ADR 0009
        makes folding a parameter of the procedure rather than a property of the
        lexicon. German keeps its umlauts for the same reason.
        """
        return "".join(ch for ch in word.casefold() if ch.isalpha())
