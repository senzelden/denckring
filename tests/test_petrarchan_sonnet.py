import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
the sun will set behind the hill in may
a bird can fly around the house at three
the boat will drift below the open sea
the wind will move the grass and blow away
the light will fade before the end of day
the child will run across the field so free
the fox will hide beneath the fallen stone
the fish will swim beneath the frozen lake
the moon will rise and fill the sky with light
the owl will call across the dark alone
the deer will wake before the morning break
the stars will burn until the end of night"""

VIOLATING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the fox will hide beneath the fallen stone
the birds will sing before the break of day"""


def test_petrarchan_sonnet_accepts_a_conforming_text() -> None:
    report = check("petrarchan_sonnet", CONFORMING)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_petrarchan_sonnet_rejects_a_violating_text() -> None:
    assert not check("petrarchan_sonnet", VIOLATING).satisfied
