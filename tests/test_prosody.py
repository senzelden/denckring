"""Rhyme and metre, and the honest limits of both."""

import pytest

from denckring import check
from denckring.core.errors import MissingCapability
from denckring.core.prosody import (
    FREE,
    _fits,
    feet,
    line_metre,
    metre_violations,
    stanza_violations,
    word_stress,
)
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


def test_a_guessed_word_is_reported_rather_than_hidden() -> None:
    """The old `test_an_unknown_word_raises_rather_than_guessing` refused to
    scan at all. Scanning is right — `hemlocks` is an ordinary word CMUdict
    lacks — but a report that says nothing about the guess is worse than the
    refusal it replaced."""
    report = check("iambic_pentameter", "the hemlocks stand beside the silent stream")
    assert report.metrics["estimated_words"] == 1.0


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


DACTYL = ("100", "11")
HEXAMETER = [DACTYL, DACTYL, DACTYL, DACTYL, ("100",), ("11", "10")]


def test_feet_expands_every_substitution() -> None:
    """A dactyl may be a spondee, so a metre is a set of readings, not one."""
    patterns = feet(HEXAMETER)
    assert len(patterns) == 32
    assert len(set(patterns)) == 32
    assert min(len(p) for p in patterns) == 13
    assert max(len(p) for p in patterns) == 17


def test_feet_of_a_single_option_is_one_pattern() -> None:
    assert feet([("100",), ("11",)]) == ["10011"]


def test_a_line_satisfies_if_it_fits_any_reading() -> None:
    pack = get_pack("en")
    # "the forest" is ?10 — fits the second option, not the first.
    result = line_metre("the forest", pack, ["111", "?10"], 0)
    assert not result.violations


def test_the_closest_reading_supplies_the_violations() -> None:
    """Reporting all thirty-two failures would tell a writer nothing. The
    candidate that matched most words is the one scansion worth showing."""
    pack = get_pack("en")
    # "the forest primeval" scans as `?10010`. Both options below are the right
    # length and both fail, so the result must carry ONE candidate's violations
    # rather than the two candidates' combined.
    result = line_metre("the forest primeval", pack, ["000000", "111111"], 0)
    assert result.violations
    assert len(result.violations) == 2


def test_each_line_is_checked_against_its_own_pattern() -> None:
    """Sapphics and alcaics change shape from line to line, which a single
    pattern applied to every line cannot express."""
    pack = get_pack("en")
    text = "the forest\nforest"
    result = stanza_violations(text, pack, [["?10"], ["10"]])
    assert not result.violations


def test_a_line_count_mismatch_is_reported_once() -> None:
    pack = get_pack("en")
    result = stanza_violations("the forest", pack, [["?10"], ["10"]])
    assert [v.rule for v in result.violations] == ["wrong_line_count"]
    assert not result.violations[0].offset


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    """No vacuous verdicts: a report with no violations behind it is a defect."""
    pack = get_pack("en")
    result = stanza_violations("", pack, [["?10"]])
    assert result.violations
    assert result.good < result.total
