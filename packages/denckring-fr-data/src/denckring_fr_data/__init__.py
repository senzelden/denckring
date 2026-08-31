"""French lexicon data for denckring.

Installing this gives the French pack `lexicon.words`, `lexicon.nouns`,
`lexicon.glosses` and `lexicon.graded_words`. Nothing branches on whether it is
present — the same procedures answer the same calls, in a third language.

Two sources, both CC BY-SA 4.0: Lexique 3.82 for membership, nouns and frequency,
and French Wiktionary for definitions. ADR 0032 records why Wikidata Lexemes,
which supplies German, could not supply French.
"""

from __future__ import annotations

from denckring.lang.fr import FrenchPack

__version__ = "0.1.0"


class FrenchDataPack(FrenchPack):
    """French with lexicon data. No data is yet vendored; skeleton only."""

    pass
