"""German pronunciation data: the IPA arithmetic, the pack, and what it refuses.

Skipped in full when `denckring[de-wiktionary]` is not installed, exactly as the
English data tests skip without `denckring[en]`. The tests that assert what
happens *without* it run against `GermanDataPack` directly, which is the class
the factory returns in that install — so the absent case is covered here rather
than only in the core-only CI job.
"""

import gzip
import json
from pathlib import Path

import pytest

from denckring.core.errors import MissingCapability
from denckring.lang.base import (
    GLOSSES,
    PHONEMES,
    STRESS,
    SYLLABLES,
    SYLLABLES_DICTIONARY,
    SYLLABLES_HEURISTIC,
)
from denckring.lang.de import GermanPack

de_data = pytest.importorskip("denckring_de_data", reason="needs denckring[de]")
wiktionary = pytest.importorskip("denckring_de_wiktionary", reason="needs denckring[de-wiktionary]")

GermanDataPack = de_data.GermanDataPack
PACK = wiktionary.GermanWiktionaryPack()

DATA = (
    Path(__file__).resolve().parent.parent
    / "packages"
    / "denckring-de-wiktionary"
    / "src"
    / "denckring_de_wiktionary"
    / "data"
)


# --- the IPA arithmetic -------------------------------------------------------
#
# Every expected value here was read off the transcription by hand. They are the
# cases that distinguish the rules from a naive vowel count, so a rule quietly
# dropping out fails one of them rather than nothing.


@pytest.mark.parametrize(
    ("ipa", "syllables", "why"),
    [
        ("ˈkat͡sə", 2, "a final schwa is a syllable in German"),
        ("muˈzeːʊm", 3, "the sequence the spelling heuristic undercounts as 2"),
        ("haʊ̯s", 1, "a diphthong's glide carries the non-syllabic mark"),
        ("ˈfʁɔɪ̯ntʃaft", 2, "likewise, inside a longer word"),
        ("ˈliːbn̩", 2, "a syllabic consonant is a nucleus with no vowel at all"),
        ("ˌunivɛʁziˈtɛːt", 5, "length marks do not add syllables"),
        ("faˈmiːli̯ə", 3, "the phonetic count, which is not the orthographic one"),
    ],
)
def test_syllables_come_from_the_nuclei(ipa: str, syllables: int, why: str) -> None:
    assert wiktionary.syllables_of(ipa) == syllables, why


@pytest.mark.parametrize(
    ("ipa", "pattern"),
    [
        ("ˈkat͡sə", "10"),
        ("muˈzeːʊm", "010"),
        ("haʊ̯s", "?"),  # a monosyllable takes whatever beat the line needs
        ("ˈeːɐ̯tˌbeːʁə", "1?0"),  # secondary stress is free, as CMUdict's 2 is
        ("ˌunivɛʁziˈtɛːt", "?0001"),
    ],
)
def test_stress_is_read_off_the_transcription(ipa: str, pattern: str) -> None:
    """ADR 0030's D4: no stress data is sourced, so `stress` cannot be present
    while `phonemes` is absent."""
    assert wiktionary.stress_of(ipa) == pattern


def test_a_stress_mark_governs_the_syllable_after_it() -> None:
    """The mark precedes the onset, so a scan needs a pending mark rather than a
    lookup behind it. `muˈzeːʊm` is the case that catches the off-by-one: read
    backwards it would stress the first syllable."""
    assert wiktionary.nucleus_stress("muˈzeːʊm") == ["0", "1", "0"]


@pytest.mark.parametrize(
    ("ipa", "expected"),
    [
        ("ˈkat͡sə", ["k", "a", "t͡s", "ə"]),  # the tie makes an affricate one phoneme
        ("ˈliːbn̩", ["l", "iː", "b", "n̩"]),  # length attaches to its vowel
        ("haʊ̯s", ["h", "a", "ʊ̯", "s"]),
    ],
)
def test_phonemes_keep_ties_length_and_marks_with_their_segment(
    ipa: str, expected: list[str]
) -> None:
    assert wiktionary.phonemes_of(ipa) == expected


def test_a_rhyme_key_runs_from_the_last_primary_stressed_vowel() -> None:
    assert wiktionary.rhyme_of("ˈhɛʁt͡sn̩") == wiktionary.rhyme_of("ˈʃmɛʁt͡sn̩")
    assert wiktionary.rhyme_of("ˈhɛʁt͡sn̩") != wiktionary.rhyme_of("ˈkat͡sn̩")


def test_a_transcription_with_no_primary_stress_falls_back_to_its_last_syllable() -> None:
    """Clitics, mostly. The alternative is returning the whole word, which would
    rhyme every stressless word with every other one of the same length."""
    assert wiktionary.rhyme_of("dɐ") == "ɐ"


# --- the pack -----------------------------------------------------------------


def test_the_pack_declares_what_it_can_do_and_nothing_more() -> None:
    for capability in (PHONEMES, STRESS, SYLLABLES_DICTIONARY, SYLLABLES_HEURISTIC, GLOSSES):
        assert capability in PACK.capabilities
    # `syllables(word)` is a division of the *spelling*, which a transcription
    # does not carry. Claiming it is the defect this chapter found in the English
    # pack and did not repeat here. ADR 0030.
    assert SYLLABLES not in PACK.capabilities
    with pytest.raises(MissingCapability):
        PACK.syllables("Katze")


def test_stress_is_never_present_without_phonemes() -> None:
    """D4 again, as an invariant rather than as prose: they come off one string,
    so no install can have one and not the other."""
    assert (STRESS in PACK.capabilities) == (PHONEMES in PACK.capabilities)


def test_a_known_word_is_counted_exactly() -> None:
    assert PACK.syllable_count("Museum") == (3, True)
    # The heuristic gets this one wrong, which is why the dictionary is worth
    # shipping. tests/test_syllables_de.py pins the wrong answer as known.
    assert GermanPack().syllable_count("Museum") == (2, False)


def test_an_unknown_word_falls_back_to_the_heuristic_and_says_so() -> None:
    count, exact = PACK.syllable_count("Zwirbelquast")
    assert exact is False
    assert count == GermanPack().syllable_count("Zwirbelquast")[0]


def test_an_unknown_word_refuses_to_guess_a_pronunciation() -> None:
    """ADR 0004. `denckring.core.prosody.word_stress` catches this and turns it
    into a scan that measures the word's length while constraining no beat —
    which it can only do if the pack raises rather than inventing phonemes."""
    for call in (PACK.phonemes, PACK.rhyme_key, PACK.stress_pattern):
        with pytest.raises(MissingCapability):
            call("Zwirbelquast")


def test_several_readings_are_offered_where_wiktionary_lists_them() -> None:
    """`gehen` is `ˈɡeːən` and `ɡeːn` — two syllables or one, which is the
    difference between a line scanning and not."""
    assert PACK.stress_patterns("gehen") == ["10", "?"]


def test_words_that_rhyme_share_a_key_and_words_that_do_not_do_not() -> None:
    assert set(PACK.rhyme_keys("Herzen")) & set(PACK.rhyme_keys("Schmerzen"))
    assert not set(PACK.rhyme_keys("Herzen")) & set(PACK.rhyme_keys("Katzen"))


def test_a_sentence_opener_is_found_at_its_lowercase_title() -> None:
    """D5. German capitalises nouns *and* sentence openers, and Wiktionary titles
    are case-sensitive, so without the flip every line-initial function word is a
    miss. Measured worth 4.7 points of token coverage."""
    assert PACK.stress_pattern("Und") == PACK.stress_pattern("und")


def test_glosses_come_back_empty_rather_than_raising() -> None:
    """The English pack's contract, kept: an unresolvable word is "undefined
    here", which a definitional procedure can act on, not an error."""
    assert PACK.glosses("Hund")
    assert PACK.glosses("Zwirbelquast") == ()


def test_the_lexical_pack_alone_refuses_the_phonetic_questions() -> None:
    """What `denckring[de]` without `[de-wiktionary]` does. The factory returns
    this class in that install, so this is that install's behaviour."""
    lexical = GermanDataPack()
    assert PHONEMES not in lexical.capabilities
    assert GLOSSES not in lexical.capabilities
    with pytest.raises(MissingCapability) as raised:
        lexical.phonemes("Katze")
    assert PHONEMES in str(raised.value)


def test_the_factory_hands_back_the_richer_pack_when_its_data_is_installed() -> None:
    """One entry point, two distributions. `denckring/lang/__init__.py` refuses a
    second pack claiming `de`, so the choice is made here instead. ADR 0030."""
    assert isinstance(de_data.pack(), wiktionary.GermanWiktionaryPack)
    assert GermanDataPack.capabilities < PACK.capabilities


# --- the vendored data --------------------------------------------------------


def test_the_metadata_counts_match_the_files() -> None:
    """A silent corpus change fails here rather than drifting unnoticed. The
    gzip bytes alone do not diff cleanly enough to catch it by eye."""
    counts = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))["counts"]
    for name, expected in counts.items():
        with gzip.open(DATA / name, mode="rt", encoding="utf-8") as handle:
            assert sum(1 for _ in handle) == expected, name


def test_every_shipped_transcription_is_usable_german_ipa() -> None:
    """The build script's filter, asserted on the output rather than trusted from
    the input. A transcription carrying a space is a multi-word phrase and a
    transcription carrying `…` is a placeholder; either would make `phonemes`
    return something that is not a list of German phonemes.

    Sampled rather than exhaustive: 838,000 entries is slower than this suite
    should be, and a filter that leaks leaks broadly.
    """
    table = wiktionary.pronunciations()
    for index, (word, forms) in enumerate(table.items()):
        if index % 97:
            continue
        for form in forms:
            assert form.strip() == form, word
            assert " " not in form and "…" not in form, word
            assert wiktionary.syllables_of(form) >= 1, word
