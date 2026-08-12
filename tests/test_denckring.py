"""The device the package is named after."""

import pytest

from denckring import check, get
from denckring.core import device as devices
from denckring.core.errors import UnknownDevice
from denckring.core.protocol import Constructive

RINGS = devices.load("harsdoerffer_1651")


def test_the_rings_are_the_shape_harsdoerffer_describes() -> None:
    assert [len(slot.alternatives) for slot in RINGS.slots] == [49, 60, 12, 120, 23]
    assert [slot.optional for slot in RINGS.slots] == [True, False, False, False, True]


def test_the_transcribed_rings_give_their_own_product() -> None:
    """Not Harsdörffer's stated 82,944,000, and not the literature's figure either."""
    product = 1
    for slot in RINGS.slots:
        product *= len(slot.alternatives)
    assert product == 97_372_800
    # The number the literature repeats cannot be a product of rings of 12 and 120.
    assert 97_209_600 % 144 != 0


def test_real_german_words_come_off_the_rings() -> None:
    assert check("denckring", "verlangen", lang="de").satisfied
    assert check("denckring", "beschreiben", lang="de").satisfied


def test_the_word_denckring_is_not_itself_on_the_rings() -> None:
    """Harsdörffer's device cannot spell its own name."""
    report = check("denckring", "Denckring", lang="de")
    assert not report.satisfied
    assert report.violations[0].rule == "not_on_the_rings"


def test_nonsense_is_not_on_the_rings() -> None:
    assert not check("denckring", "xyzzy", lang="de").satisfied


def test_segmentation_reads_inward_to_outward() -> None:
    assert devices.segment("verlangen", RINGS) == ["ver", "L", "a", "ng", "en"]


def test_spinning_produces_a_word_the_rings_accept() -> None:
    procedure = get("denckring")
    assert isinstance(procedure, Constructive)
    for seed in range(8):
        word = procedure.apply("", seed=seed)
        assert procedure.check(word, lang="de").satisfied, word


def test_spinning_is_deterministic_under_a_seed() -> None:
    procedure = get("denckring")
    assert isinstance(procedure, Constructive)
    assert procedure.apply("", seed=5) == procedure.apply("", seed=5)


def test_requiring_every_ring_rejects_a_skipped_one() -> None:
    # "Lang" needs no prefix and no suffix, so the optional rings contribute nothing.
    assert check("denckring", "Lang", lang="de").satisfied
    strict = check("denckring", "Lang", lang="de", require_all_rings=True)
    assert not strict.satisfied
    assert strict.violations[0].rule == "ring_skipped"


def test_an_unknown_device_names_what_is_available() -> None:
    with pytest.raises(UnknownDevice, match="harsdoerffer_1651"):
        check("denckring", "wort", lang="de", device="no_such_device")
