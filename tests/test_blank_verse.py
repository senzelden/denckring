import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
the fox will hide beneath the fallen stone
the moon will rise behind the hill at nine"""

VIOLATING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may"""


def test_blank_verse_accepts_a_conforming_text() -> None:
    report = check("blank_verse", CONFORMING)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_blank_verse_rejects_a_violating_text() -> None:
    assert not check("blank_verse", VIOLATING).satisfied
