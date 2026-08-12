import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

SOURCE = "the cat sat on the table"
DISPLACED_BY_THREE = "the catacala satanism on the tablefork"


def test_a_configurable_offset_is_respected() -> None:
    assert check(
        "s_plus_7", "the catacala satanism on the tablefork", source=SOURCE, offset=3
    ).satisfied


def test_the_wrong_offset_is_not_satisfied() -> None:
    assert not check(
        "s_plus_7", "the catacala satanism on the tablefork", source=SOURCE, offset=7
    ).satisfied
