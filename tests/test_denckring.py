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
    product = 1
    for slot in RINGS.slots:
        product *= len(slot.alternatives)
    assert product == 97_372_800


def test_both_counts_of_the_parts_come_to_the_same_total() -> None:
    """Two independent counts disagree on a boundary, not on how many parts there are.

    The transcription reads 49/60/12/120/23; the other count reads 48/60/12/120/24.
    Both come to 264, so what is disputed is where the prefix ring ends and the
    suffix ring begins.
    """
    transcribed = [len(slot.alternatives) for slot in RINGS.slots]
    assert sum(transcribed) == 264
    assert sum([48, 60, 12, 120, 24]) == 264


def test_the_literatures_figure_cannot_be_a_product_of_any_rings() -> None:
    """97,209,600 factors as 2^8 x 3 x 5^2 x 61 x 83.

    Both 61 and 83 are prime and neither divides any ring size on either count, so
    the figure is not a product of any subset of the rings — a stronger statement
    than merely noting it is not divisible by 144.
    """
    assert 61 * 83 * 19_200 == 97_209_600
    every_count = {48, 49, 50, 60, 12, 120, 23, 24}
    for prime in (61, 83):
        assert all(size % prime for size in every_count)


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
