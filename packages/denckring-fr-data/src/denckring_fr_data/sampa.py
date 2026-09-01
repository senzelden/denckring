"""Lexique 3.82's SAMPA, in the IPA this project uses everywhere else.

Lexique's alphabet is its own: `@` is the nasal /ɑ̃/ rather than a schwa, `§`
is /ɔ̃/, and `2`/`9` split /ø/ from /œ/. Reading `@` as a schwa costs fifteen
points of line accuracy and looks like a plausible one-syllable undercount, so
this table is tested against hand-checked words before anything reads it
(spec F0).
"""

from __future__ import annotations

#: Two-character sequences do not occur in Lexique's phon column, so a
#: character-by-character walk is complete.
SAMPA_TO_IPA: dict[str, str] = {
    # Oral vowels
    "a": "a",
    "A": "ɑ",
    "e": "e",
    "E": "ɛ",
    "i": "i",
    "o": "o",
    "O": "ɔ",
    "u": "u",
    "y": "y",
    "2": "ø",
    "9": "œ",
    "°": "ə",
    # Nasal vowels
    "@": "ɑ̃",
    "5": "ɛ̃",
    "1": "œ̃",
    "§": "ɔ̃",
    # Glides
    "j": "j",
    "w": "w",
    "8": "ɥ",
    # Consonants
    "b": "b",
    "d": "d",
    "f": "f",
    "g": "g",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "N": "ŋ",
    "J": "ɲ",
    "p": "p",
    "R": "ʁ",
    "s": "s",
    "S": "ʃ",
    "t": "t",
    "v": "v",
    "z": "z",
    "Z": "ʒ",
    "G": "ɡ",
    "x": "x",
}

#: A glide is written with a vowel symbol in some schemes but carries no
#: syllable of its own, so it is not here. ADR 0030 is the reason this is a
#: property of the transcription rather than of the phoneme string.
IPA_VOWELS: frozenset[str] = frozenset(
    {"a", "ɑ", "e", "ɛ", "i", "o", "ɔ", "u", "y", "ø", "œ", "ə", "ɑ̃", "ɛ̃", "œ̃", "ɔ̃"}
)


def to_ipa(sampa: str) -> str:
    """Convert one Lexique transcription. An unmapped symbol raises.

    Passing an unknown symbol through would let a scheme leak silently into a
    syllable count, which is the defect ADR 0030 fixed twice in one day.
    """
    return "".join(SAMPA_TO_IPA[ch] for ch in sampa)


def to_phonemes(sampa: str) -> list[str]:
    """The transcription as a list of IPA phonemes.

    Lexique writes one symbol per phoneme, so the split is the walk itself and
    no re-segmentation of the IPA string is needed -- `d@` is ["d", "ɑ̃"], and
    the nasal stays one phoneme rather than a vowel plus a combining tilde.
    """
    return [SAMPA_TO_IPA[ch] for ch in sampa]
