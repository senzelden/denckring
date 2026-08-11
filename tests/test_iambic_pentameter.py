import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

CONFORMING = """the cat can see the moon above the tree
the dog will run across the field today
a bird can fly around the house at three
the sun will set behind the hill in may"""

VIOLATING = """the cat sat on the mat"""


def test_iambic_pentameter_accepts_a_conforming_text() -> None:
    report = check("iambic_pentameter", CONFORMING)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_iambic_pentameter_rejects_a_violating_text() -> None:
    assert not check("iambic_pentameter", VIOLATING).satisfied
