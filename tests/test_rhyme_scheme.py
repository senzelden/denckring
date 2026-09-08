import pytest

from denckring import check
from denckring.lang import get_pack
from denckring.procedures.rhyme_scheme import form_report

pytest.importorskip("denckring_en_data")

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may"""

VIOLATING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at noon
the sun will set behind the hill at nine"""

#: Gryphius, "Es ist alles eitel" (1643), l.4 — an alexandriner closing feminine
#: on "Herden", thirteen syllables where the bare metre wants twelve.
GRYPHIUS_L4 = "Auff der ein Schäfers-Kind wird spielen mit den Herden."


def test_rhyme_scheme_accepts_a_conforming_text() -> None:
    report = check("rhyme_scheme", CONFORMING, scheme="ABAB")
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_rhyme_scheme_rejects_a_violating_text() -> None:
    assert not check("rhyme_scheme", VIOLATING, scheme="ABAB").satisfied


def test_a_feminine_line_fails_the_bare_metre() -> None:
    """The default must not move (ADR 0040 D6)."""
    result = form_report(GRYPHIUS_L4, get_pack("de"), metre="01" * 6)
    assert result.violations


def test_a_feminine_line_scans_when_the_ending_is_allowed() -> None:
    result = form_report(GRYPHIUS_L4, get_pack("de"), metre="01" * 6, feminine_ending=True)
    assert not result.violations
