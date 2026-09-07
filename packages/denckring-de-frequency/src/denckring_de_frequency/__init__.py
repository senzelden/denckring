"""German frequency bands, from the Leipzig Corpora Collection.

The sixth distribution, and the third carrying German data — under a third
licence. `denckring-de-data` is CC0 Wikidata, `denckring-de-wiktionary` is
CC BY-SA Wiktionary, and this is CC BY Leipzig. ADR 0013 quarantines a data
licence in its own distribution, and CC BY cannot join the CC0 package: CC0
waives rights where CC BY requires attribution, so merging them would make that
package's own declaration false.

Registers no entry point. See the pyproject for why, and ADR 0038 for the case
rule the build turns on.
"""

from __future__ import annotations

import gzip
from collections.abc import Mapping
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from denckring_de_data import GermanDataPack

from denckring.lang.base import GRADED_WORDS

GRADED_WORDS_PATH = Path(str(files("denckring_de_frequency") / "data" / "graded_words.txt.gz"))


@lru_cache(maxsize=1)
def graded_words() -> Mapping[str, int]:
    """Word to frequency band, where **larger means less common**.

    SCOWL's direction, which `LanguagePack.graded_words` documents and `anagram`
    sorts ascending by. Not re-derived here: this is the third distribution to
    write the same six bands, and re-deriving them would be a third chance to
    get the direction backwards.

    Keys are lowercase, which is the capability's de-facto convention — English's
    77,078 and French's 125,343 carry 0 capitals between them, and `anagram`
    matches its covers against these keys, so a capitalised key would silently
    match nothing. German is the first language for which that loses
    information, since a noun's capital is part of its spelling; ADR 0038 records
    the cost rather than quietly changing a capability's contract.
    """
    table: dict[str, int] = {}
    with gzip.open(GRADED_WORDS_PATH, mode="rt", encoding="utf-8") as handle:
        for line in handle:
            word, _, band = line.rstrip("\n").partition("\t")
            if band:
                table[word] = int(band)
    return table


class GermanFrequencyPack(GermanDataPack):
    """German with a lexicon and frequency bands behind it."""

    data_distributions: ClassVar[tuple[str, ...]] = (
        "denckring-de-data",
        "denckring-de-frequency",
    )
    capabilities: ClassVar[frozenset[str]] = GermanDataPack.capabilities | {GRADED_WORDS}

    def graded_words(self) -> Mapping[str, int]:
        """A read-only view over the cached table, for the reason English gives:
        the module function is `lru_cache`d and shared, so handing the dict out
        would let one caller's mutation corrupt it for all the others."""
        return MappingProxyType(graded_words())


try:
    from denckring_de_wiktionary import GermanWiktionaryPack
except ImportError:  # pragma: no cover - depends on what is installed
    #: Without the Wiktionary distribution there is no richer pack to combine
    #: with, and the factory in `denckring-de-data` never reaches for this name.
    #: Bound anyway so the module's exports do not depend on an install.
    GermanWiktionaryFrequencyPack = GermanFrequencyPack
else:

    class GermanWiktionaryFrequencyPack(GermanWiktionaryPack):  # type: ignore[no-redef]
        """Everything German has: lexicon, pronunciations, and frequency.

        Declared here rather than in `denckring-de-wiktionary`, because that
        distribution must not learn about this one. Either is installable
        without the other, and a hard dependency in that direction would make
        one of those installs impossible. This package imports it optionally
        instead — the same shape `denckring-de-data`'s own factory uses, and for
        the same reason (ADR 0013, ADR 0030).
        """

        data_distributions: ClassVar[tuple[str, ...]] = (
            "denckring-de-data",
            "denckring-de-wiktionary",
            "denckring-de-frequency",
        )
        capabilities: ClassVar[frozenset[str]] = GermanWiktionaryPack.capabilities | {GRADED_WORDS}

        def graded_words(self) -> Mapping[str, int]:
            return MappingProxyType(graded_words())


#: Kept in step with `pyproject.toml` by hand, the way the four sibling data
#: distributions do. This one shipped without it (ADR 0038) and was the second
#: thing about the sixth distribution to be half-integrated — the release plan
#: had also counted five distributions, not six.
__version__ = "0.1.0"

__all__ = [
    "GRADED_WORDS_PATH",
    "GermanFrequencyPack",
    "GermanWiktionaryFrequencyPack",
    "graded_words",
]
