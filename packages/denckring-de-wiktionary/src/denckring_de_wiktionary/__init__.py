"""German pronunciation and gloss data for denckring.

This distribution registers no entry point. `denckring/lang/__init__.py` refuses
two claiming one language, so a fourth distribution cannot register `de` beside
`denckring-de-data`; that package's `pack()` factory imports the subclass below
when this distribution is installed, and returns its own lexical pack when it is
not. ADR 0030.

What lives here is the data, the IPA arithmetic that reads it — a transcription
into a syllable count, a stress pattern, a phoneme list and a rhyme key — and the
pack that puts the two together. All three sit in the CC BY-SA distribution
because all three exist only for CC BY-SA data.

The data is German Wiktionary, CC BY-SA 4.0. See LICENSE-WIKTIONARY.
"""

from __future__ import annotations

import gzip
import unicodedata
from collections.abc import Mapping, Sequence
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import ClassVar, TypeVar

from denckring_de_data import GermanDataPack

from denckring.core.errors import MissingCapability
from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    GLOSSES,
    LETTER_SHAPES,
    NOUNS,
    PHONEMES,
    STRESS,
    SYLLABLES_DICTIONARY,
    SYLLABLES_HEURISTIC,
    TOKENS,
    WORDS,
)

#: What `look_up` returns is whatever the table holds — a list of transcriptions
#: or a tuple of glosses — and the caller must get its own type back.
_V = TypeVar("_V", bound=Sequence[str])

PRONUNCIATIONS_PATH = Path(str(files("denckring_de_wiktionary") / "data" / "pronunciations.txt.gz"))
GLOSSES_PATH = Path(str(files("denckring_de_wiktionary") / "data" / "glosses.txt.gz"))

__version__ = "0.1.0"

#: Primary stress. Precedes the onset of the syllable it marks, so the syllable
#: it governs is the next nucleus after it, not the previous one.
PRIMARY = "ˈ"
#: Secondary stress, reported as free for the reason English reports its own
#: `2` that way: a secondary-stressed syllable takes either beat in verse.
SECONDARY = "ˌ"
#: Combining inverted breve below. Marks the glide of a diphthong — `aɪ̯` is one
#: syllable, and without this every German diphthong would count as two.
NON_SYLLABIC = "̯"
#: Combining vertical line below and above. Mark a syllabic consonant: `ˈliːbn̩`
#: is two syllables whose second nucleus is a consonant, not a vowel.
SYLLABIC_BELOW = "̩"
SYLLABIC_ABOVE = "̍"
#: Modifier letter triangular colon: length. Part of the vowel it follows.
LENGTH = "ː"
#: Combining double inverted breve: the tie joining an affricate, `t͡s`.
TIE = "͡"

#: Every base symbol that can be a syllable nucleus. Length, nasality and
#: devoicing are combining marks on these rather than members.
_VOWELS = frozenset("aɐɑæeɛəiɪoɔøœuʊyʏʌɜɒ")

_STRESS_MARKS = {PRIMARY: "1", SECONDARY: "2"}

#: What a monosyllable's stress is: whatever the line needs. Mirrors
#: `denckring.core.prosody.FREE`, which is where the convention is documented,
#: but is not imported from there — this module is data, and core's prosody
#: module is free to move without breaking a distribution that only ever needed
#: the character.
FREE = "?"


def _read(path: Path) -> dict[str, list[str]]:
    """A `key\\tvalue|value` table, or `key\\tvalue | value` for glosses.

    Read whole rather than streamed: both tables are wanted in full by the first
    caller that touches them, and holding them is what makes lookup a dict hit.
    """
    table: dict[str, list[str]] = {}
    with gzip.open(path, mode="rt", encoding="utf-8") as handle:
        for line in handle:
            key, _, values = line.rstrip("\n").partition("\t")
            if values:
                table[key] = values.split("|")
    return table


@lru_cache(maxsize=1)
def pronunciations() -> dict[str, list[str]]:
    """Headword to every transcription Wiktionary lists, in its order.

    Order is load-bearing: `stress_pattern` and `rhyme_key` answer with the
    first, which is the reading a writer is most likely to have had in mind, and
    `stress_patterns` offers the rest to the scansion search.
    """
    return _read(PRONUNCIATIONS_PATH)


@lru_cache(maxsize=1)
def gloss_table() -> dict[str, tuple[str, ...]]:
    """Headword to every sense's definition.

    Split on `" | "` rather than `"|"`, because a definition may contain a bare
    pipe and the build script rejects any that contains the spaced separator.
    """
    with gzip.open(GLOSSES_PATH, mode="rt", encoding="utf-8") as handle:
        return {
            key: tuple(values.split(" | "))
            for key, _, values in (line.rstrip("\n").partition("\t") for line in handle)
            if values
        }


def look_up(table: Mapping[str, _V], word: str) -> _V | None:
    """The token as written, then case-flipped.

    German capitalises nouns *and* sentence openers, and Wiktionary titles are
    case-sensitive, so a sentence-initial `Und` has no entry while `und` does.
    Trying the flipped case recovers those; the reverse direction recovers a
    noun someone lowercased. Measured over 341,000 tokens of literary German,
    the flip is worth 4.7 points of coverage.

    Never folded to ASCII: `Bär` and `Bar` are different words, and ADR 0009
    makes folding a decision of the procedure rather than of the lexicon.
    """
    for candidate in (word, word.capitalize(), word.lower(), word.upper()):
        found = table.get(candidate)
        if found:
            return found
    return None


def _segments(ipa: str) -> list[tuple[str, str]]:
    """The transcription as (base character, combining marks) pairs.

    Decomposed first, so `ç` — which the dump writes both ways — is one shape
    here whichever way it arrived.
    """
    decomposed = unicodedata.normalize("NFD", ipa)
    out: list[tuple[str, str]] = []
    index = 0
    while index < len(decomposed):
        base = decomposed[index]
        index += 1
        marks = ""
        while index < len(decomposed) and unicodedata.combining(decomposed[index]):
            marks += decomposed[index]
            index += 1
        out.append((base, marks))
    return out


def _is_nucleus(base: str, marks: str) -> bool:
    """Whether this segment carries a syllable.

    Two ways to be one and one way not to be: a vowel is a nucleus unless it is
    marked non-syllabic, which is how German writes the second element of a
    diphthong, and any consonant is a nucleus if it is marked syllabic.
    """
    if base in _VOWELS:
        return NON_SYLLABIC not in marks
    return SYLLABIC_BELOW in marks or SYLLABIC_ABOVE in marks


def nucleus_stress(ipa: str) -> list[str]:
    """One `0`, `1` or `2` per syllable, in order.

    A stress mark applies to the next nucleus rather than the previous one,
    which is what makes this a scan with a pending mark rather than a lookup.
    """
    marks_out: list[str] = []
    pending = "0"
    for base, marks in _segments(ipa):
        if base in _STRESS_MARKS:
            pending = _STRESS_MARKS[base]
        elif _is_nucleus(base, marks):
            marks_out.append(pending)
            pending = "0"
    return marks_out


def syllables_of(ipa: str) -> int:
    """How many syllables the transcription has.

    This is the *phonetic* count, and it is not always the count a metrist
    wants: `Familie` is `faˈmiːli̯ə`, three syllables, where the orthographic
    reading and much of German verse take four. The transcription is the source
    of truth here because it is the source that was measured; a poem that wants
    the other reading is asking a question this data cannot answer.
    """
    return len(nucleus_stress(ipa))


def stress_of(ipa: str) -> str:
    """One character per syllable: `1` primary, `0` unstressed, `?` free.

    A monosyllable is all `?`, and so is a secondary-stressed syllable, for the
    same reason the English pack reports CMUdict's `2` that way: verse assigns
    both whatever beat it needs.
    """
    marks = nucleus_stress(ipa)
    if len(marks) <= 1:
        return FREE * len(marks)
    return "".join(FREE if mark == "2" else mark for mark in marks)


def phonemes_of(ipa: str) -> list[str]:
    """The transcription as a list of phonemes.

    Stress marks are dropped — they are properties of a syllable, not segments
    — and length, nasality, devoicing and the non-syllabic mark stay attached
    to the segment they belong to. An affricate written with a tie (`t͡s`) is one
    phoneme, because that is what the tie says.
    """
    out: list[str] = []
    pending_tie = False
    for base, marks in _segments(ipa):
        if base in _STRESS_MARKS:
            continue
        if base == LENGTH:
            if out:
                out[-1] += base
            continue
        piece = unicodedata.normalize("NFC", base + marks)
        if pending_tie and out:
            out[-1] += piece
        else:
            out.append(piece)
        pending_tie = TIE in marks
    return out


def rhyme_of(ipa: str) -> str:
    """Phonemes from the last primary-stressed vowel to the end of the word.

    The same rule the English pack applies to CMUdict, and for the same reason:
    a German rhyme is stressed vowel onwards, so `Herzen` and `Schmerzen` share
    a key while `Herzen` and `Katzen` do not. A transcription with no primary
    stress at all — a clitic, mostly — falls back to its last syllable, which is
    what the English pack does with its own stressless entries.
    """
    pieces = phonemes_of(ipa)
    nucleus_at = [
        index
        for index, piece in enumerate(pieces)
        if any(_is_nucleus(base, marks) for base, marks in _segments(piece))
    ]
    if not nucleus_at:
        return " ".join(pieces)
    marks = nucleus_stress(ipa)
    primary = [i for i, mark in enumerate(marks) if mark == "1"]
    which = primary[-1] if primary else len(marks) - 1
    return " ".join(pieces[nucleus_at[which] :])


class GermanWiktionaryPack(GermanDataPack):
    """German with pronunciations, stress and glosses behind it.

    A subclass of the lexical pack rather than a sibling: this install has both
    distributions, so it has both sets of data, and inheritance is what lets
    `is_word`, `nouns` and `noun_index` keep answering from Wikidata while the
    five methods below answer from Wiktionary.

    Every capability here is a fixed `ClassVar`, exactly as on every other pack in
    the project. An earlier draft of ADR 0030 computed `GermanDataPack.capabilities`
    from a probe for this distribution and accepted, as a stated cost, that a
    reader could no longer see what the class could do. The factory removed the
    cost rather than paying it: which class you get depends on the install, which
    is unavoidable and now readable in one place, but what each class can do is
    written on the class.
    """

    data_distributions: ClassVar[tuple[str, ...]] = ("denckring-de-data", "denckring-de-wiktionary")
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {
            TOKENS,
            ALPHABET,
            FOLD_DIACRITICS,
            LETTER_SHAPES,
            SYLLABLES_HEURISTIC,
            SYLLABLES_DICTIONARY,
            PHONEMES,
            STRESS,
            NOUNS,
            WORDS,
            GLOSSES,
        }
    )

    # Each method below raises `MissingCapability` for a word the table does not
    # carry, which is what `denckring.core.prosody.word_stress` and
    # `word_rhyme_keys` catch and turn into an unconstrained scan. Guessing a
    # pronunciation is the silent wrongness ADR 0004 forbids.

    def syllable_count(self, word: str) -> tuple[int, bool]:
        """Exact when the dictionary knows the word, estimated otherwise.

        The only one of these that falls back rather than raising: a syllable
        count has an honest estimate behind it — tranche A's vowel-run heuristic,
        inherited from `GermanPack` — and the `exact` flag says which was used. A
        phoneme list has no honest estimate at all.
        """
        forms = self._forms(word)
        if forms is None:
            return super().syllable_count(word)
        return syllables_of(forms[0]), True

    def phonemes(self, word: str) -> list[str]:
        return phonemes_of(self._forms_or_raise(word)[0])

    def is_vowel_phoneme(self, phoneme: str) -> bool:
        """A vowel symbol not marked non-syllabic, or a syllabic consonant.

        The same test `syllables_of` counts with, asked of one segment: a
        diphthong's glide is written with a vowel symbol and carries no syllable,
        so `ʊ̯` in `haʊ̯s` is not a vowel here and `haʊ̯s` has the onset `h`.
        """
        return any(_is_nucleus(base, marks) for base, marks in _segments(phoneme))

    def rhyme_key(self, word: str) -> str:
        """The first transcription's rhyme key."""
        return rhyme_of(self._forms_or_raise(word)[0])

    def rhyme_keys(self, word: str) -> list[str]:
        """Every transcription's rhyme key. Two words rhyme if any pair matches."""
        return list(dict.fromkeys(rhyme_of(form) for form in self._forms_or_raise(word)))

    def stress_pattern(self, word: str) -> str:
        """The first transcription's stress pattern."""
        return stress_of(self._forms_or_raise(word)[0])

    def stress_patterns(self, word: str) -> list[str]:
        """Every transcription's stress pattern, longest first.

        A line scans if some combination of listed pronunciations fits, and German
        Wiktionary lists genuinely different readings — `gehen` is both `ˈɡeːən`
        and `ɡeːn`, two syllables or one, which is the difference between a line
        scanning and not. Longest first for the reason the English pack sorts the
        same way: `denckring.core.prosody._scan` takes the first fit, and the
        fuller reading is the one a writer wrote.
        """
        found = dict.fromkeys(stress_of(form) for form in self._forms_or_raise(word))
        return sorted(found, key=len, reverse=True)

    def glosses(self, word: str) -> tuple[str, ...]:
        """Every sense the dictionary carries, or nothing.

        Nothing rather than a raise, matching the English pack: `glosses` is
        documented to return an empty sequence for a word it cannot resolve, and a
        definitional procedure reads that as "undefined here" rather than as an
        error.
        """
        return look_up(gloss_table(), word) or ()

    def _forms(self, word: str) -> list[str] | None:
        """Every transcription for the word, or None if the table has none."""
        return look_up(pronunciations(), word)

    def _forms_or_raise(self, word: str) -> list[str]:
        forms = self._forms(word)
        if not forms:
            raise MissingCapability(f"<word {word!r}>", self.lang, PHONEMES)
        return forms


__all__ = [
    "GLOSSES_PATH",
    "PRONUNCIATIONS_PATH",
    "GermanWiktionaryPack",
    "gloss_table",
    "look_up",
    "nucleus_stress",
    "phonemes_of",
    "pronunciations",
    "rhyme_of",
    "stress_of",
    "syllables_of",
]
