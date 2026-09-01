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
import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar, TypeVar

from denckring.core.errors import MissingCapability
from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    GLOSSES,
    GRADED_WORDS,
    LETTER_SHAPES,
    NOUNS,
    PHONEMES,
    SYLLABLES,
    SYLLABLES_DICTIONARY,
    SYLLABLES_HEURISTIC,
    TOKENS,
    WORDS,
)
from denckring.lang.fr import FrenchPack
from denckring_fr_data.elision import count_line
from denckring_fr_data.sampa import IPA_VOWELS, to_phonemes

#: Orthographic vowel runs, for the estimate a word outside Lexique gets.
#: Answers "roughly how long is this unknown word" from spelling alone --
#: deliberately not shared with `elision.py`'s pattern (Task 6), which answers
#: "does this known word end in a mute e" over a different alphabet of
#: concerns entirely.
_VOWEL_RUN = re.compile(r"[aeiouyàâäéèêëîïôöùûüÿœæ]+")

#: What `look_up` returns is whatever the table holds, and the caller must get
#: its own type back. The same shape as `denckring_de_wiktionary.look_up`.
_V = TypeVar("_V", bound=Sequence[str])

WORDS_PATH = Path(str(files("denckring_fr_data") / "data" / "words.txt.gz"))
NOUNS_PATH = Path(str(files("denckring_fr_data") / "data" / "nouns.txt.gz"))
GRADED_WORDS_PATH = Path(str(files("denckring_fr_data") / "data" / "graded_words.txt.gz"))
GLOSSES_PATH = Path(str(files("denckring_fr_data") / "data" / "glosses.txt.gz"))
SYLLABLES_PATH = Path(str(files("denckring_fr_data") / "data" / "syllables.txt.gz"))
H_ASPIRE_PATH = Path(str(files("denckring_fr_data") / "data" / "h_aspire.txt.gz"))

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


@lru_cache(maxsize=1)
def syllable_table() -> Mapping[str, tuple[int, str, str]]:
    """spelling -> (citation syllables, Lexique SAMPA, orthographic syllabation).

    The third element is the segmented spelling (`car-ros-se`), which serves two
    callers: `syllables()` returns its segments, and the mute-e rules compare
    its segment count against `nbsyll` to judge a final `-ent`.
    """
    table: dict[str, tuple[int, str, str]] = {}
    for line in _read(SYLLABLES_PATH):
        ortho, nbsyll, phon, osyll = line.split("\t")
        table[ortho] = (int(nbsyll), phon, osyll)
    return MappingProxyType(table)


def _table_entry(word: str) -> tuple[int, str, str] | None:
    """The table entry for `word`, falling back past a leading elision.

    Task 6's tokeniser (`elision._TOKEN_RE`) deliberately keeps an
    apostrophe-bearing token whole -- `aujourd'hui` and `prud'homme` are 94
    real Lexique entries, and splitting every apostrophe unconditionally
    would silently misread those as a proclitic plus a word. So the whole
    lowercased form is tried first, exactly as before.

    But not every apostrophe-bearing form is one of those 94: `d'espoir`,
    `l'amour`, `qu'un` are ordinary elision, the proclitic written onto the
    following word, and were never table entries themselves. A whole-form-only
    lookup made `phonemes`/`rhyme_key`/`rhyme_keys`/`syllable_count` fail on
    them with `MissingCapability`, which is a routine event elsewhere but
    silently starved `rhyme_scheme` and `ghazal` of exactly the line-ending
    words French verse ends on most often (fix round 2). The rhyme- and
    syllable-bearing unit of an elided form is what follows the apostrophe,
    so a whole-form miss retries there -- the segment after the LAST
    apostrophe, in case of a chained elision -- before giving up.
    """
    table = syllable_table()
    lower = word.casefold()
    entry = table.get(lower)
    if entry is not None:
        return entry
    if "'" not in lower and "’" not in lower:  # noqa: RUF001
        return None
    tail = re.split(r"['’]", lower)[-1]  # noqa: RUF001
    return table.get(tail)


@lru_cache(maxsize=1)
def h_aspire() -> frozenset[str]:
    """Words whose initial h blocks elision. Lexique cannot answer this."""
    return frozenset(_read(H_ASPIRE_PATH))


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
        {
            TOKENS,
            ALPHABET,
            FOLD_DIACRITICS,
            LETTER_SHAPES,
            NOUNS,
            WORDS,
            GLOSSES,
            GRADED_WORDS,
            SYLLABLES,
            SYLLABLES_DICTIONARY,
            SYLLABLES_HEURISTIC,
            PHONEMES,
        }
    )

    def is_word(self, word: str) -> bool:
        return self._lemma(word) in known_words()

    def syllable_count(self, word: str) -> tuple[int, bool]:
        """Lexique's citation count, or a vowel-run estimate outside it.

        The count is the *citation* one: `femme` is one syllable here and
        frequently two in verse. The line rules, not this method, are where
        verse is answered -- spec D3.

        `_table_entry` tries the whole form first and only then falls back
        past a leading elision (`d'espoir` -> `espoir`), so `aujourd'hui`
        still resolves whole and an ordinary elided form no longer falls
        through to the vowel-run estimate for no reason (fix round 2).
        """
        entry = _table_entry(word)
        if entry is not None:
            return entry[0], True
        return max(len(_VOWEL_RUN.findall(word.casefold())), 1), False

    def line_syllables(self, line: str) -> tuple[int, int]:
        """French counts a line, not a bag of words. Spec D3, ADR 0034."""
        return count_line(line, syllable_table(), h_aspire())

    def syllables(self, word: str) -> list[str]:
        """The orthographic segments, or `MissingCapability` for a word
        Lexique does not carry.

        Not `KeyError`: nothing in `core/` calls this yet, so the choice is
        latent, but Task 6's line rules will call it the same way
        `core/prosody.py` already calls `rhyme_keys` -- catching only
        `MissingCapability` on an out-of-vocabulary word, which is a routine
        event in real verse rather than an edge case. `KeyError` here would
        repeat exactly the crash fix-round 1 found in `phonemes` and
        `rhyme_key`/`rhyme_keys`.
        """
        entry = syllable_table().get(word.casefold())
        if entry is None:
            raise MissingCapability(f"<word {word!r}>", self.lang, SYLLABLES)
        return entry[2].split("-")

    def phonemes(self, word: str) -> list[str]:
        """The IPA transcription, or `MissingCapability` for a word Lexique
        does not carry.

        Not `KeyError`: `core/prosody.py`'s `word_rhyme_keys` and
        `assonance_constraint`/`spoonerism`'s own lookups catch only
        `MissingCapability` around a pack call, reading it as "this word is
        undecidable" rather than letting it propagate. A plain `KeyError`
        went uncaught there -- `check('assonance_constraint', ..., lang='fr')`
        crashed outright on the first unknown word, which is routine in real
        French text, not an edge case. Matches the convention
        `denckring-en-data` and `denckring-de-wiktionary` already established
        for exactly this call.

        `_table_entry` tries the whole form first and only then falls back
        past a leading elision (fix round 2) -- see its docstring. `rhyme_key`
        and `rhyme_keys` both call this method, so the fallback reaches them
        for free.
        """
        entry = _table_entry(word)
        if entry is None:
            raise MissingCapability(f"<word {word!r}>", self.lang, PHONEMES)
        return to_phonemes(entry[1])

    def is_vowel_phoneme(self, phoneme: str) -> bool:
        return phoneme in IPA_VOWELS

    def rhyme_key(self, word: str) -> str:
        """Phonemes from the last vowel to the end of the word.

        The base definition says "from the last primary-stressed vowel", but
        French has no lexical stress (spec D2), so the final vowel is the
        rhyme-bearing one -- the *rime suffisante* every French prosodist
        assumes. Feminine/masculine alternation is NOT modelled here; this
        project's `rhyme_scheme` models it in no language, and that stays a
        separate, recorded gap rather than something this method papers over.

        Raises `MissingCapability` for a word Lexique does not carry, via
        `phonemes()` -- a guessed rhyme is worse than an unknown one, and
        `core.prosody.word_rhyme_keys` catches exactly that exception around
        `rhyme_keys` and reads it as "this word is undecidable", which is what
        makes an unknown word in a French poem non-fatal rather than an
        uncaught crash (fix-round 1: it was `KeyError` and unhandled there).
        """
        phones = self.phonemes(word)
        for index in range(len(phones) - 1, -1, -1):
            if self.is_vowel_phoneme(phones[index]):
                return "".join(phones[index:])
        return "".join(phones)

    def rhyme_keys(self, word: str) -> list[str]:
        """Every pronunciation's rhyme key -- one, since the table holds a
        single transcription per spelling (ADR 0034 records the homograph
        cost that comes with that)."""
        return [self.rhyme_key(word)]

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
