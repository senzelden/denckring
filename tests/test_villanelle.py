import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the cat can see the moon above the tree
the sun will set behind the hill in may
the cat can see the moon above the tree
the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the cat can see the moon above the tree
the sun will set behind the hill in may
the cat can see the moon above the tree
the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the cat can see the moon above the tree
the sun will set behind the hill in may
the cat can see the moon above the tree
a bird can fly around the house at three"""

VIOLATING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the fox will hide beneath the fallen stone
the birds will sing before the break of day"""


def test_villanelle_accepts_a_conforming_text() -> None:
    report = check("villanelle", CONFORMING)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_villanelle_rejects_a_violating_text() -> None:
    assert not check("villanelle", VIOLATING).satisfied
