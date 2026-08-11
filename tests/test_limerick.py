import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

CONFORMING = """there was an old man with a beard
who said it is just as i feared
two owls and a hen
four larks and a wren
have all flown away and disappeared"""

VIOLATING = """there was an old man with a beard
who said it is just as i feared
two owls and a hen
four larks and a wren
have all built their nests in my beard"""


def test_limerick_accepts_a_conforming_text() -> None:
    report = check("limerick", CONFORMING)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_limerick_rejects_a_violating_text() -> None:
    assert not check("limerick", VIOLATING).satisfied
