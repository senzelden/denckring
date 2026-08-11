import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the fox will hide beneath the fallen stone
the fish will swim beneath the frozen lake
the owl will call across the dark alone
the deer will wake before the morning break
the moon will rise and fill the sky with light
the horse will stand beside the gate so still
the stars will burn until the end of night
the mouse will hide behind the open till
the clock will mark the passing of the time
the bell will ring and slowly start to chime"""

VIOLATING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may
the fox will hide beneath the fallen stone
the birds will sing before the break of day"""


def test_shakespearean_sonnet_accepts_a_conforming_text() -> None:
    report = check("shakespearean_sonnet", CONFORMING)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_shakespearean_sonnet_rejects_a_violating_text() -> None:
    assert not check("shakespearean_sonnet", VIOLATING).satisfied
