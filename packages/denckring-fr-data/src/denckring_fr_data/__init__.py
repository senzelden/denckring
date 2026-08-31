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
from collections.abc import Mapping
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from denckring.lang.fr import FrenchPack

WORDS_PATH = Path(str(files("denckring_fr_data") / "data" / "words.txt.gz"))
NOUNS_PATH = Path(str(files("denckring_fr_data") / "data" / "nouns.txt.gz"))
GRADED_WORDS_PATH = Path(str(files("denckring_fr_data") / "data" / "graded_words.txt.gz"))

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


class FrenchDataPack(FrenchPack):
    """French with lexicon data. No data is yet vendored; skeleton only."""

    pass
