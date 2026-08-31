"""Proteus verse: the count, the guard, and what the count is a count of."""

from typing import Any

import pytest

from denckring import check
from denckring.core.base import ConstructiveProcedure
from denckring.core.errors import InputTooLong, InvalidParams
from denckring.core.registry import get
from denckring.procedures.proteus_verse import METRES, _count, _orderings

#: Spelled out at every call rather than splatted from a dict: `check` takes
#: `lang` as an explicit keyword, so `**{"metre": ...}` is a `dict[str, str]`
#: mypy has to consider binding to it.
PENTAMETER = "iambic_pentameter"
LINE = "the cat can see the moon above the tree"


def generator() -> ConstructiveProcedure[Any, Any]:
    """`get` is typed as the base class, which has no `apply`. The same narrowing
    `tests/test_apply_spine.py` does, for the same reason."""
    procedure = get("proteus_verse")
    assert isinstance(procedure, ConstructiveProcedure)
    return procedure


def test_a_line_that_scans_and_permutes_satisfies() -> None:
    report = check("proteus_verse", LINE, metre=PENTAMETER)
    assert report.satisfied
    assert report.metrics["variants"] == 201600
    assert report.metrics["words"] == 9


def test_the_two_conditions_are_scored_separately() -> None:
    """A line that holds the metre and does not permute far enough is half right,
    and a writer can act on which half. Collapsing both into one boolean would
    make those two failures indistinguishable in the report."""
    report = check("proteus_verse", LINE, metre=PENTAMETER, minimum=1_000_000)
    assert not report.satisfied
    assert report.score == 0.5
    assert [v.rule for v in report.violations] == ["too_few_variants"]


def test_a_line_that_does_not_scan_says_so_and_not_that_it_permutes_badly() -> None:
    report = check("proteus_verse", "the cat sat on the mat")
    assert {v.rule for v in report.violations} == {"does_not_scan", "too_few_variants"}


def test_a_long_line_is_refused_rather_than_searched() -> None:
    """Ten words is 3.6 million orderings. The refusal names words, because that
    is what this row rearranges — `InputTooLong` says letters for `anagram`."""
    with pytest.raises(InputTooLong) as raised:
        check("proteus_verse", "one two three four five six seven eight nine ten")
    assert "words" in str(raised.value)
    assert raised.value.detail()["unit"] == "words"


def test_a_longer_line_can_be_searched_if_the_caller_says_so() -> None:
    """The limit is the caller's, because the historical counts are of lines this
    row would otherwise refuse: Bauhusius's hexameter is eight words, but
    Harsdörffer's eleven-word claim is not."""
    report = check("proteus_verse", "the cat can see the moon above the small tree", max_words=10)
    assert report.metrics["words"] == 10


def test_an_unknown_metre_is_refused_by_name() -> None:
    with pytest.raises(InvalidParams) as raised:
        check("proteus_verse", LINE, metre="hendecasyllable")
    assert "hendecasyllable" in str(raised.value)


def test_more_than_one_line_is_not_a_verse() -> None:
    report = check("proteus_verse", f"{LINE}\n{LINE}", metre=PENTAMETER)
    assert [v.rule for v in report.violations] == ["wrong_line_count"]


def test_the_count_counts_orderings_and_not_readings() -> None:
    """Two readings of one word at the same length put it in the same place in the
    same ordering. Counting them twice would inflate the total by an artefact of
    how the dictionary is written — a word Wiktionary lists twice identically
    would double the count of every line it appears in."""
    one_length_twice = (("01", "01"), ("01",))
    assert _count(one_length_twice, "0101") == 2


def test_a_word_readable_at_two_lengths_reaches_what_one_reading_cannot() -> None:
    """`gehen` is `ˈɡeːən` and `ɡeːn`, two syllables or one. Offering only the
    longer reading makes the line unscannable in every order; offering both makes
    four orders scan. This is the difference the multiple-pronunciation lookup
    exists for, and it is why the walk branches on length rather than on word."""
    both = (("10", "?"), ("?",), ("01",))
    longer_only = (("10",), ("?",), ("01",))
    assert _count(longer_only, "0101") == 0
    assert _count(both, "0101") == 4


def test_the_orderings_are_the_ones_the_count_counted() -> None:
    """The two searches answer the same question by different means — a walk that
    forgets which words reached a state, and a walk that remembers — so on a line
    small enough to enumerate they must agree exactly."""
    forms = (("10",), ("01",), ("?",), ("?",))
    pattern = "010101"
    found = _orderings(forms, pattern, 1000)
    assert len(found) == _count(forms, pattern)
    assert len(set(found)) == len(found)


def test_produce_returns_orderings_of_the_words_it_was_given() -> None:
    words = LINE.split()
    production = generator().produce(LINE, max_results=5, metre=PENTAMETER)
    assert production.texts
    for text in production.texts:
        assert sorted(text.split()) == sorted(words)
        assert check("proteus_verse", text, metre=PENTAMETER).satisfied


def test_produce_does_not_hand_back_the_line_it_was_given() -> None:
    """The spine's degeneracy guard, doing its job on a row whose output is by
    construction a rearrangement of the input — the line as written is normally
    among the valid orderings, and returning it says nothing about what ran."""
    assert generator().apply(LINE, metre=PENTAMETER) != LINE


def test_german_scans_under_the_same_search() -> None:
    """Voß's opening hexameter, unmodified. The search never learns what language
    it is in; the pack answers the stress and the rest is arithmetic."""
    report = check(
        "proteus_verse", "Sage mir, Muse, die Taten des vielgewanderten Mannes", lang="de"
    )
    assert report.satisfied
    assert report.metrics["variants"] == 1728


@pytest.mark.parametrize("metre", sorted(METRES))
def test_every_named_metre_has_at_least_one_reading(metre: str) -> None:
    assert METRES[metre]
    assert all(set(pattern) <= {"0", "1", "?"} for pattern in METRES[metre])
