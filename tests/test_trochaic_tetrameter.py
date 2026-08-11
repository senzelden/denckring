import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

CONFORMING = """never having any water
seldom eating apple butter"""

VIOLATING = """the cat can see the moon above the tree"""


def test_trochaic_tetrameter_accepts_a_conforming_text() -> None:
    report = check("trochaic_tetrameter", CONFORMING)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_trochaic_tetrameter_rejects_a_violating_text() -> None:
    assert not check("trochaic_tetrameter", VIOLATING).satisfied
