import pytest

from denckring import check
from denckring.procedures.s_plus_7 import SPlus7

pytest.importorskip("denckring_en_data")

GARDEN = ["aster", "bramble", "crocus", "dahlia", "elder", "fennel", "gorse", "hazel"]

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


def test_s_plus_7_inherits_the_dictionary() -> None:
    """It delegates to `NPlus7Params` and `displacement_report`, so it gets this
    free — asserted rather than assumed, because "free" is how a surface quietly
    diverges."""
    assert SPlus7().apply("aster", lang="en", dictionary=GARDEN, offset=2) == "crocus"
