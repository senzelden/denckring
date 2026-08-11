"""Rhyme and metre, and the honest limits of both."""

import pytest

from denckring import check
from denckring.core.errors import MissingCapability
from denckring.lang.en import EnglishPack

pytest.importorskip("denckring_en_data")

PENTAMETER = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may"""


def test_regular_lines_scan_as_iambic_pentameter() -> None:
    assert check("iambic_pentameter", PENTAMETER).satisfied


def test_a_short_line_is_a_violation() -> None:
    report = check("iambic_pentameter", "the cat sat on the mat")
    assert not report.satisfied
    assert report.violations[0].rule == "wrong_line_length"


def test_a_rhyme_scheme_checks_both_directions() -> None:
    assert check("rhyme_scheme", PENTAMETER, scheme="ABAB").satisfied
    # Everything rhyming is not ABAB either.
    assert not check(
        "rhyme_scheme",
        "\n".join(
            ["the cat can see the moon above the tree", "a bird can fly around the house at three"]
            * 2
        ),
        scheme="ABAB",
    ).satisfied


def test_a_word_does_not_rhyme_with_itself_by_default() -> None:
    doubled = "the cat can see the moon above the tree\nthe cat can see the moon above the tree"
    assert not check("rhyme_scheme", doubled, scheme="AA").satisfied
    assert check("rhyme_scheme", doubled, scheme="AA", allow_identical=True).satisfied


def test_monosyllables_take_whatever_stress_the_line_needs() -> None:
    """The whole metre design rests on this: dictionary stress would reject it."""
    assert check("iambic_pentameter", "the cat can see the moon above the tree").satisfied


def test_pronunciation_variants_are_searched() -> None:
    """CMUdict lists temperate as two syllables first and three second."""
    from denckring.lang import get_pack

    assert get_pack("en").stress_patterns("temperate") == ["100", "10"]


def test_an_unknown_word_raises_rather_than_guessing() -> None:
    with pytest.raises(MissingCapability):
        check("iambic_pentameter", "zzzunknowncoinage and more words here now")


def test_metre_is_unavailable_without_the_data_package() -> None:
    """The first procedures a core-only install genuinely cannot run."""
    core = EnglishPack()
    with pytest.raises(MissingCapability):
        core.stress_pattern("cat")
    with pytest.raises(MissingCapability):
        core.rhyme_key("cat")
