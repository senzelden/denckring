"""The case rule — ADR 0038 D3, and the decision this chapter turns on.

German capitalises common nouns. A frequency source that keeps case therefore
tells German `Tag` from English `tag`; one that does not cannot, and no filter
recovers it afterwards. Both German word lists in this project have themselves
discarded case — `known_words()` is 0 capitalised of 668,580, and only `nouns()`
keeps it — so the rule has to be written into the build rather than inherited
from the data.

Tested against Leipzig-shaped fixture rows, never a download: the corpus is
219 MB, and a test that fetched it would be a test nobody runs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "packages/denckring-de-frequency/scripts"))

from build_frequency import bands

#: `Tag`, `List`, `Power` and `Tower` are German nouns whose lowercase forms are
#: English words. `gut` is not a noun and is genuinely lowercase German — `Gut`,
#: an estate, is a different word, which is why the rule keys on the noun list
#: rather than on the letters alone.
KNOWN = {"tag", "list", "power", "tower", "gut", "esel", "haus"}
NOUNS_LOWER = {"tag", "list", "power", "tower", "esel", "haus"}


def test_a_noun_is_counted_only_from_capitalised_rows() -> None:
    assert "tag" in bands([("Tag", 598)], KNOWN, NOUNS_LOWER)
    # 400 lowercase occurrences in a German corpus are English and are not this
    # word's evidence.
    assert bands([("tag", 400)], KNOWN, NOUNS_LOWER) == {}


def test_a_non_noun_is_counted_only_from_lowercase_rows() -> None:
    assert "gut" in bands([("gut", 900)], KNOWN, NOUNS_LOWER)
    assert bands([("Gut", 900)], KNOWN, NOUNS_LOWER) == {}


def test_a_word_the_lexicon_does_not_know_is_dropped() -> None:
    assert bands([("Blockchain", 500)], KNOWN, NOUNS_LOWER) == {}


def test_short_forms_are_dropped() -> None:
    """`cd`, `kg` and `PS` are unit symbols and abbreviations, not words worth
    ranking. Three letters, the same floor `calculator_word` chose."""
    assert bands([("PS", 900)], KNOWN | {"ps"}, NOUNS_LOWER | {"ps"}) == {}


def test_keys_are_lowercase_because_that_is_the_capability_s_convention() -> None:
    """English's 77,078 and French's 125,343 carry 0 capitals between them, and
    `anagram` matches its covers against these keys — a capitalised key would
    match nothing. ADR 0038 records the cost: German prints nouns uncapitalised."""
    table = bands([("Tag", 5), ("Haus", 9)], KNOWN, NOUNS_LOWER)
    assert table
    assert all(word == word.lower() for word in table)


def test_the_largest_count_wins_for_a_form_seen_twice() -> None:
    """A corpus can split one word across rows the tokeniser did not unify."""
    once = bands([("Haus", 9)], KNOWN, NOUNS_LOWER)
    twice = bands([("Haus", 9), ("Haus", 900)], KNOWN, NOUNS_LOWER)
    assert once == twice == {"haus": 10}


def test_bands_run_from_10_to_60_with_larger_meaning_rarer() -> None:
    # Alphabetic throughout: `bands` drops anything `isalpha()` rejects, so a
    # fixture numbered `Haus0`..`Haus59` produces an empty table and this test
    # would fail on a `min()` of nothing rather than on the bands.
    words = [f"Haus{a}{b}" for a in "abcdefghij" for b in "abcdef"]
    rows = [(word, 1000 - index) for index, word in enumerate(words)]
    known = {word.lower() for word in words}
    table = bands(rows, known, known)
    assert min(table.values()) == 10
    assert max(table.values()) == 60
    assert table[words[0].lower()] == 10, "the commonest word takes the lowest band"
