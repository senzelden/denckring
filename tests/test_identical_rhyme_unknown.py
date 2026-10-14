"""A word does not rhyme with itself, whether or not the dictionary carries it.

`scheme_violations` once tested an unknown line ending before it tested
identity, so a pair ending on the same word the pronouncing dictionary lacks
never reached the `identical_rhyme` test: under `undecidable` it went unscored,
under `free` it matched, and under `strict` it was reported as an unknown word.
Lear's limerick that ends twice on "Ryde" passed as a result, while his "beard"
limerick, the same fault on a word the dictionary carries, failed. Whether two
endings are the same word is read off the spelling, so it needs no pronunciation.
"""

from typing import get_args

import pytest

from denckring import check
from denckring.core.prosody import UnknownRhyme, scheme_violations
from denckring.lang import get_pack

pytest.importorskip("denckring_en_data")

READINGS = get_args(UnknownRhyme)

# "Ryde" is the point: a place name the pronouncing dictionary does not carry.
RYDE = """There was a Young Lady of Ryde,
Whose shoe-strings were seldom untied;
She purchased some clogs,
And some small spotty dogs,
And frequently walked about Ryde."""


def test_ryde_is_unknown_to_the_dictionary() -> None:
    """The premise: if the dictionary learns "Ryde", these tests stop testing it."""
    keys = scheme_violations(RYDE, get_pack("en"), "AABBA", allow_identical=False).evidence
    assert [e.value for e in keys if e.subject == "Ryde"] == ["no rhyme key"] * 2


@pytest.mark.parametrize("reading", READINGS)
def test_an_unknown_word_repeated_as_a_rhyme_is_identical(reading: UnknownRhyme) -> None:
    result = scheme_violations(
        "the lady went to Ryde\nand frequently walked about Ryde",
        get_pack("en"),
        "AA",
        allow_identical=False,
        unknown_rhyme=reading,
    )
    assert [v.rule for v in result.violations] == ["identical_rhyme"]
    # The pair was decided, so it counts as a check: not vacuous, not a match.
    assert (result.good, result.total) == (0, 1)


@pytest.mark.parametrize("reading", READINGS)
def test_lears_ryde_limerick_fails_on_its_repeated_word(reading: UnknownRhyme) -> None:
    report = check("limerick", RYDE, unknown_rhyme=reading)
    assert not report.satisfied
    identical = [v for v in report.violations if v.rule == "identical_rhyme"]
    assert [v.found for v in identical] == ["Ryde"]


def test_allow_identical_still_leaves_an_unknown_pair_to_the_reading() -> None:
    """The fix reaches only the identity test: a permitted repeat of an unknown
    word is still a pair the dictionary cannot decide."""
    text = "the lady went to Ryde\nand frequently walked about Ryde"
    pack = get_pack("en")
    undecidable = scheme_violations(text, pack, "AA", allow_identical=True)
    assert [v.rule for v in undecidable.violations] == ["rhyme_undecidable"]
    free = scheme_violations(text, pack, "AA", allow_identical=True, unknown_rhyme="free")
    assert free.violations == [] and (free.good, free.total) == (1, 1)
    strict = scheme_violations(text, pack, "AA", allow_identical=True, unknown_rhyme="strict")
    assert [v.rule for v in strict.violations] == ["unknown_rhyme"]


def test_an_unwanted_pair_is_not_judged_identical() -> None:
    """Identity is a fault only where the scheme asks for a rhyme; lines on
    different letters keep the unknown-word reading they had."""
    result = scheme_violations(
        "the lady went to Ryde\nand frequently walked about Ryde",
        get_pack("en"),
        "AB",
        allow_identical=False,
    )
    assert [v.rule for v in result.violations] == ["rhyme_undecidable"]


BALLADE_REFRAIN_UNKNOWN = """a cat can climb a tall old tree
the dog will run and play all day
the kestrel flies out to the sea
the sun will shine and light the way
the sky will clear by first of may
the wall was built of gray old stone
the birds will call what they all say
until the wind went off to Ryde
the clock will chime at half past three
the boys will laugh and run to play
a fish will leap and swim so free
the guests will come and wish to stay
the storm clouds turn both dark and gray
the barn stood dark and stayed alone
the goats will roam and love to stray
until the wind went off to Ryde
he holds the door shut with a key
the trees will bend then start to sway
the priest will grant the poor his plea
the child will shape the wet soft clay
the light comes down in one long ray
the truth at last to all was known
the hens will rest then soon they lay
until the wind went off to Ryde
the men will come at dusk to pay
the corn stood tall for it had grown
the ships will sail out past the bay
until the wind went off to Ryde"""


@pytest.mark.parametrize("reading", READINGS)
def test_a_ballade_refrain_on_an_unknown_word_stays_exempt(reading: UnknownRhyme) -> None:
    """The refrain is the same line four times; `ballade` exempts those pairs
    itself, and now that an unknown word's repeat is judged identical, the
    exemption must reach a refrain ending on a word the dictionary lacks."""
    report = check("ballade", BALLADE_REFRAIN_UNKNOWN, unknown_rhyme=reading)
    assert not any(v.rule == "identical_rhyme" for v in report.violations)


def test_a_ballade_refrain_on_an_unknown_word_satisfies_by_default() -> None:
    report = check("ballade", BALLADE_REFRAIN_UNKNOWN)
    assert report.satisfied, report.violations


def test_an_english_contraction_is_not_split_into_its_ending() -> None:
    """Splitting past an apostrophe is French elision (ADR 0036). An English
    apostrophe elides inside a word, and splitting there made Shakespeare's
    `dimm'd` and `vntrim'd` the same word `d` once identity reached words the
    dictionary lacks."""
    result = scheme_violations(
        "And often is his gold complexion dimm'd\nBy chance, or natures changing course vntrim'd",
        get_pack("en"),
        "AA",
        allow_identical=False,
    )
    assert not any(v.rule == "identical_rhyme" for v in result.violations)


def test_an_english_contraction_repeated_is_still_identical() -> None:
    result = scheme_violations(
        "his gold complexion dimm'd\nhis gold complexion dimm'd",
        get_pack("en"),
        "AA",
        allow_identical=False,
    )
    assert [v.rule for v in result.violations] == ["identical_rhyme"]


@pytest.mark.parametrize("reading", READINGS)
def test_a_french_unknown_word_is_identical_past_its_elision(reading: UnknownRhyme) -> None:
    """French is the one language read past an elided proclitic (ADR 0036), and
    the identity test now comes before the dictionary there too: `ozorbaque`
    and `l'ozorbaque` are one word the dictionary lacks, rhymed with itself."""
    pytest.importorskip("denckring_fr_data")
    pack = get_pack("fr")
    text = "Il marche vers ozorbaque\nIl pense à l'ozorbaque"
    assert [
        e.value for e in scheme_violations(text, pack, "AA", allow_identical=True).evidence
    ] == ["no rhyme key"] * 2
    result = scheme_violations(text, pack, "AA", allow_identical=False, unknown_rhyme=reading)
    assert [v.rule for v in result.violations] == ["identical_rhyme"]
