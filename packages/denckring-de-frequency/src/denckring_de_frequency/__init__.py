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


__all__ = ["GRADED_WORDS_PATH", "graded_words"]
