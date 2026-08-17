"""Rhyme and metre, and the honest limits of both."""

import pytest

from denckring import check
from denckring.core.errors import MissingCapability
from denckring.core.prosody import FREE, _fits, metre_violations, word_stress
from denckring.lang import get_pack
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


def test_an_unknown_word_no_longer_aborts_the_check() -> None:
    """Before this task, an out-of-dictionary word raised `MissingCapability`
    and aborted the whole check. Now it is scanned heuristically instead, so
    the check still runs and reports on the words it does understand."""
    report = check("iambic_pentameter", "zzzunknowncoinage and more words here now")
    assert not report.satisfied
    assert report.violations[0].rule == "wrong_line_length"


def test_metre_is_unavailable_without_the_data_package() -> None:
    """The first procedures a core-only install genuinely cannot run."""
    core = EnglishPack()
    with pytest.raises(MissingCapability):
        core.stress_pattern("cat")
    with pytest.raises(MissingCapability):
        core.rhyme_key("cat")


def test_anceps_in_the_pattern_accepts_any_mark() -> None:
    """`?` on the pattern side is the classical anceps: the position takes
    either. Before this, `?` was honoured only on the word side, so a pattern
    written with anceps rejected every fixed-stress word at that position."""
    assert _fits("1", "?")
    assert _fits("0", "?")
    assert _fits("101", "10?")


def test_a_free_monosyllable_still_takes_whatever_the_line_needs() -> None:
    """The pre-existing word-side meaning must not change."""
    assert _fits(FREE, "1")
    assert _fits(FREE, "0")


def test_fits_still_rejects_a_real_mismatch() -> None:
    assert not _fits("10", "01")
    assert not _fits("10", "100")


def test_a_known_word_reports_its_real_patterns() -> None:
    patterns, exact = word_stress("forest", get_pack("en"))
    assert exact
    assert "10" in patterns


def test_an_unknown_word_is_scanned_for_length_but_constrains_no_beat() -> None:
    """`hemlocks` is an ordinary English noun absent from CMUdict. Before this,
    it raised MissingCapability and aborted the whole check — naming a
    capability the pack actually provides."""
    patterns, exact = word_stress("hemlocks", get_pack("en"))
    assert not exact
    assert patterns == ["??"]


def test_a_pack_genuinely_lacking_phonemes_still_raises() -> None:
    """The repair must not swallow the real capability error it is named for."""
    with pytest.raises(MissingCapability):
        word_stress("forest", EnglishPack())


def test_metre_violations_reports_how_many_words_were_estimated() -> None:
    """`estimated_words` is what keeps a heuristic honest — the syllabic
    procedures already carry it, and the metrical ones must too."""

    pack = get_pack("en")
    known = metre_violations("the forest", pack, "?10", 0)
    assert known.estimated == 0

    unknown = metre_violations("the hemlocks", pack, "???", 0)
    assert unknown.estimated == 1
