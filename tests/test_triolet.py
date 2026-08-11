import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the cat can see the moon above the tree
the cat can see the moon above the tree
the sun will set behind the hill in may
the cat can see the moon above the tree
the dog will run across the field today"""

VIOLATING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the cat can see the moon above the tree
the sun will set behind the hill in may
the cat can see the moon above the tree
the dog will run across the field today"""


def test_triolet_accepts_a_conforming_text() -> None:
    report = check("triolet", CONFORMING)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_triolet_rejects_a_violating_text() -> None:
    assert not check("triolet", VIOLATING).satisfied
