import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may"""

VIOLATING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at noon
the sun will set behind the hill at nine"""


def test_rhyme_scheme_accepts_a_conforming_text() -> None:
    report = check("rhyme_scheme", CONFORMING, scheme="ABAB")
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_rhyme_scheme_rejects_a_violating_text() -> None:
    assert not check("rhyme_scheme", VIOLATING, scheme="ABAB").satisfied
