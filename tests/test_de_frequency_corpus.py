"""The figures ADR 0038 argues from, pinned so they cannot drift into prose.

The same guard `tests/test_calculator_corpus.py` carries, and for the same
reason: a data package can be rebuilt, and a number in a document cannot notice.
"""

import denckring_de_frequency as freq

from denckring.lang import get_pack


def test_the_table_is_the_size_the_adr_claims() -> None:
    """101,296, measured 2026-09-04 on `deu_news_2023_1M`.

    A tolerance of 200 absorbs a corpus revision without absorbing a change to
    the case rule, which would move this by tens of thousands: without the rule
    the same corpus yields about 150,000, because every English token in German
    news comes back in.
    """
    assert abs(len(freq.graded_words()) - 101_296) <= 200


def test_it_sits_between_english_and_french() -> None:
    """77,078 and 125,343. Not a coincidence worth pinning for its own sake — it
    is the claim that German is now a first-class language for `anagram`."""
    import denckring_en_data as en
    import denckring_fr_data as fr

    assert len(en.graded_words()) < len(freq.graded_words()) < len(fr.graded_words())


def test_bands_run_the_direction_the_capability_documents() -> None:
    table = freq.graded_words()
    assert set(table.values()) <= {10, 20, 30, 40, 50, 60}
    assert table["und"] == 10, "a commonest-band German function word"


def test_the_case_rule_survived_the_build() -> None:
    """The regression that matters, and the one already made twice.

    Each of these is a German noun whose lowercase form is an English word. Each
    must be present — from its *capitalised* German rows — which is what the
    rejected OpenSubtitles source could not deliver, having lowercased 1,157,685
    rows into one bucket.

    The assertion is presence rather than rarity on purpose: `Power` measured
    band 10 at 1M scale, because it is genuinely common in news German. The
    claim is that it is here on German evidence, not on English.
    """
    table = freq.graded_words()
    for word in ("tag", "list", "power", "tower", "esel"):
        assert word in table, word


def test_german_nouns_are_lowercased_in_the_keys() -> None:
    """The cost ADR 0038 accepts, asserted so it is not mistaken for a bug.

    `graded_words` keys are lowercase by the capability's convention, and
    `anagram` matches its covers against them — a capitalised key would match
    nothing. So German output prints nouns uncapitalised: `list power` where
    German writes `List Power`.
    """
    assert all(word == word.lower() for word in freq.graded_words())
    assert "Esel" not in freq.graded_words()


def test_the_pack_offers_the_same_table() -> None:
    assert len(get_pack("de").graded_words()) == len(freq.graded_words())
