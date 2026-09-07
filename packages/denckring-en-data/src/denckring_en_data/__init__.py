"""English pronunciation data for denckring.

Installing this package replaces the core pack's spelling heuristic with lookups
in the CMU Pronouncing Dictionary. Nothing branches on whether it is present: the
same procedures answer the same calls, more accurately, and the `estimated_words`
metric on every syllabic report shows how much was still guessed.
"""

from __future__ import annotations

import gzip
from collections.abc import Mapping
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    GLOSSES,
    GRADED_WORDS,
    LETTER_SHAPES,
    NOUNS,
    PHONEMES,
    STRESS,
    SYLLABLES_DICTIONARY,
    SYLLABLES_HEURISTIC,
    TOKENS,
    WORDS,
)
from denckring.lang.en import EnglishPack

DICTIONARY_PATH = Path(str(files("denckring_en_data") / "data" / "cmudict.dict"))
NOUNS_PATH = Path(str(files("denckring_en_data") / "data" / "nouns.txt"))
GLOSSES_PATH = Path(str(files("denckring_en_data") / "data" / "glosses.txt.gz"))
GRADED_WORDS_PATH = Path(str(files("denckring_en_data") / "data" / "graded_words.txt.gz"))

__version__ = "0.1.0"


@lru_cache(maxsize=1)
def variants() -> dict[str, list[list[str]]]:
    """Word to every pronunciation CMUdict lists for it.

    Variants are written `word(2)`, `word(3)` and so on. They matter: Shakespeare
    needs the three-syllable `tem-per-ate`, which CMUdict lists second because the
    compressed modern form comes first.
    """
    entries: dict[str, list[list[str]]] = {}
    for line in DICTIONARY_PATH.read_text(encoding="utf-8").splitlines():
        head, _, rest = line.partition(" ")
        if not rest:
            continue
        word = head.split("(")[0].lower()
        entries.setdefault(word, []).append(rest.split())
    return entries


@lru_cache(maxsize=1)
def pronunciations() -> dict[str, list[str]]:
    """Word to its first listed pronunciation, for callers wanting one answer."""
    return {word: forms[0] for word, forms in variants().items()}


@lru_cache(maxsize=1)
def noun_list() -> tuple[str, ...]:
    """WordNet's single-word noun lemmas, in dictionary order.

    Order is the point: N+7 walks this list, so the seventh noun after a given
    one has to be well defined. Restricted to purely alphabetic lemmas, because
    a displacement must be a word the tokeniser gives back whole — `cat's-paw`
    comes back as three tokens and would break the correspondence.
    """
    return tuple(NOUNS_PATH.read_text(encoding="utf-8").split())


@lru_cache(maxsize=1)
def noun_positions() -> dict[str, int]:
    return {word: index for index, word in enumerate(noun_list())}


@lru_cache(maxsize=1)
def gloss_table() -> dict[str, tuple[str, ...]]:
    """Lemma to every sense's definition, from the gzip-compressed extract.

    Each line is `lemma\\tgloss | gloss | gloss`; no definition in the corpus
    contains the `" | "` separator, so splitting on it is unambiguous.
    """
    table: dict[str, tuple[str, ...]] = {}
    with gzip.open(GLOSSES_PATH, mode="rt", encoding="utf-8") as handle:
        for line in handle:
            lemma, _, glosses = line.rstrip("\n").partition("\t")
            if not glosses:
                continue
            table[lemma] = tuple(glosses.split(" | "))
    return table


@lru_cache(maxsize=1)
def graded_words() -> Mapping[str, int]:
    """Word to SCOWL size band, from the vendored graded list.

    Unlike `known_words()`, this is not a union of two lists built for other
    purposes: it is one list whose whole point is that its entries are ordered by
    commonness. `known_words()` stays exactly as it is — `semordnilap` and
    `charade` ask membership, and are right to keep asking the broad oracle ADR
    0015 describes.
    """
    table: dict[str, int] = {}
    with gzip.open(GRADED_WORDS_PATH, mode="rt", encoding="utf-8") as handle:
        for line in handle:
            word, _, band = line.rstrip("\n").partition("\t")
            if band:
                table[word] = int(band)
    return table


@lru_cache(maxsize=1)
def known_words() -> frozenset[str]:
    """Word membership, from the nouns and the pronouncing dictionary together.

    Neither alone is a general English word list: WordNet has no inflections of
    the kind CMUdict carries, and CMUdict has proper nouns and abbreviations
    WordNet omits.

    The union is deliberately broad, and broad in a way callers should know
    about: CMUdict lists `tac`, so `cat` reverses into something this oracle
    calls a word. It answers "could this be a word" rather than "is this in a
    dictionary of standard English", and procedures resting on it inherit that.
    """
    return frozenset(noun_list()) | frozenset(pronunciations())


class EnglishDataPack(EnglishPack):
    """English with a pronouncing dictionary behind it."""

    lang: ClassVar[str] = "en"  # type: ignore[assignment]
    data_distributions: ClassVar[tuple[str, ...]] = ("denckring-en-data",)
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {
            TOKENS,
            ALPHABET,
            FOLD_DIACRITICS,
            LETTER_SHAPES,
            SYLLABLES_HEURISTIC,
            SYLLABLES_DICTIONARY,
            # `SYLLABLES` is deliberately absent, and used to be here. That
            # capability is `syllables(word)`, the written syllables of a word,
            # and this pack has never implemented it — the inherited method
            # raised `MissingCapability` naming a capability the pack declared,
            # which is the one contradiction the error exists to rule out. A
            # pronouncing dictionary carries phonemes, not a division of the
            # spelling, so the claim was never true. Nothing required it, so
            # nothing broke; but `runs_in` (ADR 0029) computes from this set, so
            # the first row to require it would have been reported as running in
            # `en` and would then have raised. ADR 0030.
            PHONEMES,
            STRESS,
            NOUNS,
            WORDS,
            GLOSSES,
            GRADED_WORDS,
        }
    )

    def syllable_count(self, word: str) -> tuple[int, bool]:
        """Exact when the dictionary knows the word, estimated otherwise."""
        letters = "".join(ch for ch in self.fold_diacritics(word) if ch.isalpha())
        phones = pronunciations().get(letters)
        if phones is None:
            return super().syllable_count(word)
        return sum(1 for phone in phones if phone[-1].isdigit()), True

    def is_word(self, word: str) -> bool:
        return self._lemma(word) in known_words()

    def nouns(self) -> tuple[str, ...]:
        return noun_list()

    def noun_index(self, word: str) -> int | None:
        return noun_positions().get(self._lemma(word))

    def graded_words(self) -> Mapping[str, int]:
        """A read-only view over the cached table.

        `graded_words()` (the module function) is `@lru_cache`d and shared by
        every caller in the process; handing that dict out directly would let
        one caller's mutation corrupt it for all the others. `nouns()` and
        `glosses()` avoid the same risk by returning tuples; `MappingProxyType`
        is the mapping equivalent — a view, not a copy, so it costs nothing per
        call.
        """
        return MappingProxyType(graded_words())

    def glosses(self, word: str) -> tuple[str, ...]:
        table = gloss_table()
        lemma = self._lemma(word)
        for candidate in (lemma, *_inflections(lemma)):
            found = table.get(candidate)
            if found:
                return found
        return ()

    @staticmethod
    def _lemma(word: str) -> str:
        return "".join(ch for ch in word.lower() if ch.isalpha())

    def phonemes(self, word: str) -> list[str]:
        """The word's phonemes, or raise if the dictionary does not know it."""
        return _phones_or_raise(self, word)

    def is_vowel_phoneme(self, phoneme: str) -> bool:
        """A CMU-style vowel carries a stress digit; a consonant does not.

        This test used to live in `assonance_constraint` and `spoonerism`, where
        it was a rule about English wearing the name of a rule about phonemes.
        """
        return phoneme[-1:].isdigit()

    def rhyme_key(self, word: str) -> str:
        """The first pronunciation's rhyme key."""
        return _rhyme_of(_phones_or_raise(self, word))

    def rhyme_keys(self, word: str) -> list[str]:
        """Every pronunciation's rhyme key. Two words rhyme if any pair matches."""
        return list(dict.fromkeys(_rhyme_of(f) for f in _forms_or_raise(self, word)))

    def stress_pattern(self, word: str) -> str:
        """The first pronunciation's stress pattern."""
        return _stress_of(_phones_or_raise(self, word))

    def stress_patterns(self, word: str) -> list[str]:
        """Every pronunciation's stress pattern, longest first.

        A line scans if some combination of listed pronunciations fits, which is
        the same satisfiability principle the free monosyllable rests on.
        """
        found = dict.fromkeys(_stress_of(f) for f in _forms_or_raise(self, word))
        return sorted(found, key=len, reverse=True)


def _inflections(lemma: str) -> tuple[str, ...]:
    """Plain plural stripping only (R5). `ed`/`ing` were tried and dropped: measured
    over a sample sentence they resolved two extra words (`cared` -> `car`, `poled`
    -> `pol`) and both were wrong — a verb's stem collides with an unrelated noun
    often enough that the fallback is not worth it. `s`/`es` earns its keep on the
    case it exists for, plural nouns (`birds` -> `bird`), and was not observed to
    misresolve.

    This is still best-effort, not proof: even `s`/`es` stripping can in principle
    collide with an unrelated headword, so a resolution here is not a guarantee of
    correctness. What the caller can rely on is the other direction: a word this
    cannot resolve at all comes back as nothing, disclosed, never guessed at.
    """
    candidates = []
    for suffix in ("s", "es"):
        if lemma.endswith(suffix) and len(lemma) > len(suffix) + 2:
            candidates.append(lemma[: -len(suffix)])
    return tuple(candidates)


def _forms_or_raise(pack: EnglishDataPack, word: str) -> list[list[str]]:
    from denckring.core.errors import MissingCapability

    letters = "".join(ch for ch in pack.fold_diacritics(word) if ch.isalpha())
    forms = variants().get(letters)
    if not forms:
        # Guessing a pronunciation is the silent wrongness ADR 0004 forbids.
        raise MissingCapability(f"<word {word!r}>", pack.lang, PHONEMES)
    return forms


def _phones_or_raise(pack: EnglishDataPack, word: str) -> list[str]:
    return _forms_or_raise(pack, word)[0]


def _stress_of(phones: list[str]) -> str:
    marks = [p[-1] for p in phones if p[-1].isdigit()]
    if len(marks) <= 1:
        return "?" * len(marks)
    return "".join("?" if mark == "2" else mark for mark in marks)


def _rhyme_of(phones: list[str]) -> str:
    primary = [i for i, p in enumerate(phones) if p.endswith("1")]
    if not primary:
        primary = [i for i, p in enumerate(phones) if p[-1].isdigit()]
    if not primary:
        return " ".join(phones)
    return " ".join(phones[primary[-1] :])


__all__ = [
    "DICTIONARY_PATH",
    "GLOSSES_PATH",
    "GRADED_WORDS_PATH",
    "NOUNS_PATH",
    "EnglishDataPack",
    "gloss_table",
    "graded_words",
    "known_words",
    "noun_list",
    "pronunciations",
    "variants",
]
