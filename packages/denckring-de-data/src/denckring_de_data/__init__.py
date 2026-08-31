"""German lexicon data for denckring.

Installing this package gives the German pack the two lexical capabilities the
English pack has had since ADR 0015: `lexicon.words` and `lexicon.nouns`.
Nothing branches on whether it is present — the same procedures answer the same
calls, in a second language.

It also carries the *only* `de` language-pack registration, and since ADR 0030
that is a load-bearing fact rather than an incidental one. `denckring-de-wiktionary`
holds German pronunciations and glosses under CC BY-SA, which ADR 0013 forbids
merging into this CC0 distribution — and `denckring/lang/__init__.py` refuses two
entry points claiming one language, so it cannot register `de` for itself either.
The entry point therefore resolves to `pack()` below rather than to a class, and
that one function is the whole of the seam.

The data here is Wikidata Lexemes, CC0. See LICENSE-WIKIDATA.
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
    SYLLABLES_HEURISTIC,
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
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, SYLLABLES_HEURISTIC, NOUNS, WORDS}
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


def pack() -> GermanPack:
    """The best German pack this install can supply. The `de` entry point.

    A factory rather than a class, because two distributions have German data
    under two licences and only one of them may register the language.
    `denckring/lang/__init__.py` raises `DuplicatePack` for a second `de` entry
    point — deliberately, so that no installer has to choose between two packs —
    and ADR 0013 forbids merging CC BY-SA data into this CC0 distribution. A
    factory satisfies both: one entry point, and the richer pack wins when its
    data is installed.

    `entry.load()()` is what the registry calls, so a function and a class are
    interchangeable there; nothing in core learns that German is special.

    The subclass is imported here rather than at module scope because this
    distribution does not depend on that one — the dependency runs the other way.
    """
    try:
        from denckring_de_wiktionary import GermanWiktionaryPack
    except ImportError:
        # Not installed. The lexical pack is the whole answer, and a procedure
        # wanting `phonemes` will raise `MissingCapability` naming it, which is
        # the honest failure rather than a guessed pronunciation.
        return GermanDataPack()
    return GermanWiktionaryPack()
