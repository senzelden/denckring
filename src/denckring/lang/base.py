"""Capability constants and the shared pack implementation."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import ClassVar

from denckring.core.errors import MissingCapability
from denckring.core.protocol import Lang

TOKENS = "tokens"
ALPHABET = "alphabet"
FOLD_DIACRITICS = "fold_diacritics"
LETTER_SHAPES = "letter_shapes"
SYLLABLES = "syllables"
#: An estimate from spelling alone, available with no data.
SYLLABLES_HEURISTIC = "syllables.heuristic"
#: Exact counts from a pronouncing dictionary.
SYLLABLES_DICTIONARY = "syllables.dictionary"
NOUNS = "lexicon.nouns"
WORDS = "lexicon.words"
GLOSSES = "lexicon.glosses"
PHONEMES = "phonemes"
STRESS = "stress"

# Both apostrophes are intentional: real text uses the typographic one.
WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)  # noqa: RUF001

#: Stands in for the procedure name when a pack method is called directly rather
#: than through `BaseProcedure.check`, which knows what it is checking.
DIRECT_CALL = "<direct call>"


class BasePack:
    """Shared behaviour. A method whose capability is undeclared must raise."""

    lang: ClassVar[Lang]
    capabilities: ClassVar[frozenset[str]] = frozenset()
    word_re: ClassVar[re.Pattern[str]] = WORD_RE

    def tokenize(self, text: str) -> list[str]:
        return [word for _, word in self.word_spans(text)]

    def word_spans(self, text: str) -> list[tuple[int, str]]:
        return [(m.start(), m.group()) for m in self.word_re.finditer(text)]

    def fold_diacritics(self, ch: str) -> str:
        """Case-fold and strip combining marks.

        Case-folding rather than lower-casing, so that `ß` becomes `ss` — which
        means the result may be longer than one character, and callers must not
        assume otherwise.
        """
        decomposed = unicodedata.normalize("NFKD", ch.casefold())
        return "".join(c for c in decomposed if not unicodedata.combining(c))

    def alphabet(self) -> str:
        raise MissingCapability(DIRECT_CALL, self.lang, ALPHABET)

    def vowels(self) -> frozenset[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, ALPHABET)

    def ascenders(self) -> frozenset[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, LETTER_SHAPES)

    def descenders(self) -> frozenset[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, LETTER_SHAPES)

    def exceeds_x_height(self, ch: str) -> bool:
        """True when the written glyph rises above or drops below the x-height.

        Two independent reasons a character can fail: its base letter is an
        ascender or descender, or it carries a mark above. The second half is
        orthography-general — it catches ä, ö, ü and é without any pack naming
        them — so a pack only declares the letters its own alphabet adds.
        """
        if LETTER_SHAPES not in self.capabilities:
            raise MissingCapability(DIRECT_CALL, self.lang, LETTER_SHAPES)
        lowered = ch.lower()
        if lowered in self.ascenders() | self.descenders():
            return True
        return any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", lowered))

    def syllable_count(self, word: str) -> tuple[int, bool]:
        """The word's syllable count, and whether it was looked up or estimated.

        The second element is what keeps an estimate honest: a caller that needs
        certainty checks it, and every syllabic procedure reports how many of its
        words were guessed.
        """
        raise MissingCapability(DIRECT_CALL, self.lang, SYLLABLES_HEURISTIC)

    def syllables(self, word: str) -> list[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, SYLLABLES)

    def phonemes(self, word: str) -> list[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, PHONEMES)

    def rhyme_key(self, word: str) -> str:
        """Phonemes from the last primary-stressed vowel to the end of the word."""
        raise MissingCapability(DIRECT_CALL, self.lang, PHONEMES)

    def rhyme_keys(self, word: str) -> list[str]:
        """Every pronunciation's rhyme key."""
        raise MissingCapability(DIRECT_CALL, self.lang, PHONEMES)

    def stress_patterns(self, word: str) -> list[str]:
        """Every pronunciation's stress pattern."""
        raise MissingCapability(DIRECT_CALL, self.lang, STRESS)

    def stress_pattern(self, word: str) -> str:
        """One character per syllable: '0', '1', or '?' where either will do.

        A monosyllable is always '?': English gives it whatever stress the line
        needs. Secondary stress is '?' for the same reason.
        """
        raise MissingCapability(DIRECT_CALL, self.lang, STRESS)

    def is_word(self, word: str) -> bool:
        """Whether the lexicon knows this word at all."""
        raise MissingCapability(DIRECT_CALL, self.lang, WORDS)

    def glosses(self, word: str) -> Sequence[str]:
        """Every definition the lexicon carries for this word.

        Every sense, not the first: which sense a writer meant is not knowable
        from the text, so a caller that accepts any of them is the honest reader.
        An empty sequence means the lexicon could not resolve the word at all.
        """
        raise MissingCapability(DIRECT_CALL, self.lang, GLOSSES)

    def nouns(self) -> Sequence[str]:
        """Every noun the lexicon knows, in dictionary order.

        A sequence rather than an iterable because N+7 indexes into it.
        """
        raise MissingCapability(DIRECT_CALL, self.lang, NOUNS)

    def noun_index(self, word: str) -> int | None:
        """The word's position in `nouns()`, or None if it is not a noun."""
        raise MissingCapability(DIRECT_CALL, self.lang, NOUNS)
