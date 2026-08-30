"""German. A built-in default, exactly like English (ADR 0022).

Batch 1 needs no lexicon and no hyphenation, so this pack carries no data and
core stays permissive. `denckring-de-data` overrides this default with
`lexicon.words` and `lexicon.nouns` the same way `denckring-en-data` overrides
English — not through a separate registration path, but through the same
default/override precedence English has always used.
"""

from __future__ import annotations

import re
from typing import ClassVar

from denckring.core.protocol import Lang
from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    LETTER_SHAPES,
    SYLLABLES_HEURISTIC,
    TOKENS,
    BasePack,
)

#: The 26 base letters. Traditional German pangrams satisfy exactly these — the
#: umlauts and ß count as decorated forms, not as alphabet members.
_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_VOWELS = frozenset("aeiouäöü")
#: ß is named here because its written form carries an ascender. ä, ö and ü need
#: no entry: BasePack.exceeds_x_height catches any character with a mark above.
_ASCENDERS = frozenset("bdfhklt") | {"ß"}
_DESCENDERS = frozenset("fgjpqy")
#: Diphthongs need no entry here — au, ei, ai, eu, äu, oi and the less common
#: y-spellings (ey, ay, oy, as in Meyer, Bayern, Boykott) are all just a run of
#: adjacent vowels that this pattern already counts as a single nucleus, so
#: naming any of them would be a list that changes no result. y itself is in
#: the class for those spellings and for loanwords (Physik, Typ), not because
#: it is a vowel in native German spelling.
_VOWEL_GROUP = re.compile(r"[aeiouy]+")


class GermanPack(BasePack):
    """German, with no data files and the same five capabilities as core English."""

    lang: ClassVar[Lang] = "de"
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES, SYLLABLES_HEURISTIC}
    )

    def alphabet(self) -> str:
        return _ALPHABET

    def vowels(self) -> frozenset[str]:
        return _VOWELS

    def ascenders(self) -> frozenset[str]:
        return _ASCENDERS

    def descenders(self) -> frozenset[str]:
        return _DESCENDERS

    def syllable_count(self, word: str) -> tuple[int, bool]:
        """Estimate syllables from spelling. Never reports itself as exact.

        Count vowel groups, and stop. English's two other rules are deliberately
        not carried over, because both are wrong for German: a final "e" is
        pronounced (`Katze` is `kat.sə`, two syllables), so there is no silent-e
        subtraction — and with no silent-e rule there is nothing for a `-le` rule
        to compensate for.

        The cost, and why the second element is always False: a vowel sequence
        spanning a morpheme boundary is one nucleus to this pattern and two to a
        speaker. `Museum` gives 2 where German says 3, `Familie` gives 3 where
        German says 4. ADR 0012's `exact` flag is what keeps that honest, and
        unlike English there is not yet a `denckring[de]` dictionary to replace it.
        """
        letters = "".join(ch for ch in self.fold_diacritics(word) if ch.isalpha())
        if not letters:
            return 0, False
        return max(len(_VOWEL_GROUP.findall(letters)), 1), False
