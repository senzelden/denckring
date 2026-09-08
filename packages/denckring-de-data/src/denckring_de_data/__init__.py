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

__version__ = "0.1.1"


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

    data_distributions: ClassVar[tuple[str, ...]] = ("denckring-de-data",)
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

    A factory rather than a class, because three distributions carry German data
    under three licences and only one of them may register the language.
    `denckring/lang/__init__.py` raises `DuplicatePack` for a second `de` entry
    point — deliberately, so no installer has to choose between packs — and ADR
    0013 forbids merging their licences. A factory satisfies both: one entry
    point, and the richest pack whose data is installed wins.

    `entry.load()()` is what the registry calls, so a function and a class are
    interchangeable there; nothing in core learns that German is special.

    **Four combinations, each naming a class rather than composing one at
    runtime.** ADR 0030 replaced a computed-capabilities probe with a named
    factory once already, and its reason still holds: a reader should be able to
    see what a class carries without running it. Two optional distributions made
    two branches; a third (ADR 0038) makes four, and four named branches are
    still cheaper to read than one clever line.

    The subclasses are imported here rather than at module scope because this
    distribution depends on neither of them — the dependencies run the other way.
    """
    try:
        from denckring_de_frequency import (
            GermanFrequencyPack,
            GermanWiktionaryFrequencyPack,
        )
    except ImportError:
        # No frequency data. `anagram` can still check in German and will raise
        # `MissingCapability` naming `lexicon.graded_words` if asked to generate,
        # which is the honest failure rather than an unranked pile of covers.
        try:
            from denckring_de_wiktionary import GermanWiktionaryPack
        except ImportError:
            return GermanDataPack()
        return GermanWiktionaryPack()
    try:
        import denckring_de_wiktionary  # noqa: F401
    except ImportError:
        # Not installed. A procedure wanting `phonemes` will raise
        # `MissingCapability` naming it, which is the honest failure rather than
        # a guessed pronunciation.
        return GermanFrequencyPack()
    return GermanWiktionaryFrequencyPack()
