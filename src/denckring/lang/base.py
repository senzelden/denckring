"""Capability constants and the shared pack implementation."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
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
GRADED_WORDS = "lexicon.graded_words"
PHONEMES = "phonemes"
STRESS = "stress"

# Both apostrophes are intentional: real text uses the typographic one.
WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)  # noqa: RUF001

#: Stands in for the procedure name when a pack method is called directly rather
#: than through `BaseProcedure.check`, which knows what it is checking.
DIRECT_CALL = "<direct call>"

#: Letters that are vowels in some positions and consonants in others, so they
#: belong to no inventory: `y` in all three languages, and French's `ÿ` which
#: folds to it. `supervocalic` publishes "each of the five vowels", and `y` is
#: not one of the five in any of them — French lists it among its vowels but
#: writes `yeux` with it as /j/. ADR 0035, D1.
#:
#: Deliberately NOT the same set as a pack's glide inventory, which is wider
#: (English `y w u i o`): removing those from the inventory would leave English
#: requiring `a` and `e` alone.
_AMBIGUOUS = frozenset("yÿ")


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

    def vowel_inventory(self) -> frozenset[str]:
        """The base vowel letters, one of each of which a supervocalic needs.

        Distinct from `vowels()`, which answers which characters are written as
        vowels and therefore carries the accented forms — the reading
        `word_ladder` needs to widen an alphabet. `supervocalic` publishes "each
        of the five vowels exactly once" and folded text can never contain an
        umlaut, so requiring the accented forms made the row unsatisfiable in
        German and French (ADR 0035, D1).

        Folds *before* removing the ambiguous letters, and the order is
        load-bearing: measured, removing `y` without folding first answers eight
        for German and nineteen for French. All three packs inherit `aeiou` and
        none overrides.
        """
        return (
            frozenset({folded for ch in self.vowels() for folded in self.fold_diacritics(ch)})
            - _AMBIGUOUS
        )

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

    def line_syllables(self, line: str) -> tuple[int, int]:
        """How many syllables the line has, and how many words were estimated.

        On the pack because the answer is a property of the language: French
        counts a final mute e as a syllable before a consonant and elides it
        before a vowel, so summing citation forms word by word undercounts
        systematically, and French verse is entirely syllable-counting. English
        and German want exactly this sum and inherit it unchanged (spec D3).
        """
        total = 0
        estimated = 0
        for word in self.tokenize(line):
            count, exact = self.syllable_count(word)
            total += count
            if not exact:
                estimated += 1
        return total, estimated

    def syllables(self, word: str) -> list[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, SYLLABLES)

    def phonemes(self, word: str) -> list[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, PHONEMES)

    def is_vowel_phoneme(self, phoneme: str) -> bool:
        """Whether one phoneme from `phonemes()` is a syllable's vowel.

        On the pack because the answer is a property of the transcription
        scheme, not of the phoneme string. `assonance_constraint` and
        `spoonerism` both used to test it as "carries a stress digit", which is
        CMUdict's convention and true of no other source — so when German gained
        `phonemes` from IPA, both rows ran and found no vowels in any German word
        at all. They ran, they were reported as running, and they were silently
        wrong. ADR 0030.

        A glide is not a vowel by this test even though it is written with a
        vowel symbol: the second element of a German diphthong carries no
        syllable of its own, so `haʊ̯s` has one vowel and an onset of `h`.
        """
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

    def graded_words(self) -> Mapping[str, int]:
        """Every word the lexicon knows, with how common it is.

        A `Mapping`, where `nouns()` is a `Sequence`: N+7 indexes into the noun
        list positionally, so its order is load-bearing, while nothing indexes
        into this one. The anagram search needs band *lookup* and builds its own
        letter-keyed index over the keys, so a mapping is the shape that matches
        the question being asked.

        Values are SCOWL size bands, and **larger means less common** — 60 is the
        largest band SCOWL is confident carries no misspellings. A caller ranking
        by this sorts ascending.

        Separate from `lexicon.words` because ADR 0015's rule is one capability
        per question, and "is this a word" is answerable by a pack that cannot
        answer this one.
        """
        raise MissingCapability(DIRECT_CALL, self.lang, GRADED_WORDS)
