"""Rings filled from a text of the reader's own.

The one shape in `docs/expansion_ideas/HANDOVER-denckring-method-zoo.md` with no
historical precedent, and so the one that is a device constructor rather than a
catalogue row — see `from_text`'s docstring for why that distinction is load-bearing
in a catalogue whose `attribution` field has no value meaning "invented here".
"""

from pathlib import Path

import pytest
import yaml

from denckring.core.device import DEVICE_PATH_ENV, Device, from_text, load, select, spin
from denckring.core.errors import InputTooShort
from denckring.lang import get_pack

PACK = get_pack("en")
#: Twenty-four distinct words, `the` much the commonest, and no word repeated
#: across the sentences except `the` — so what lands where is checkable by eye.
TEXT = (
    "the moon the river the stone the ember the ash the wind\n"
    "silver copper amber golden iron leaden\n"
    "turning falling waiting burning drifting settling\n"
    "slowly quickly gently harshly softly loudly\n"
)


def build(slots: int = 4, per_slot: int = 6, drop_commonest: int = 0) -> Device:
    return from_text(
        TEXT,
        PACK,
        device_id="sample",
        name="a sample",
        slots=slots,
        per_slot=per_slot,
        drop_commonest=drop_commonest,
    )


def test_the_same_text_always_gives_the_same_rings() -> None:
    """`check` and `apply` derive the device separately from the same text. If the
    derivation were not total — a set iteration, a tie broken arbitrarily — a
    generator would produce output its own checker rejects, which is the drift ADR
    0025 made `apply` inherit `check`'s spine to prevent."""
    assert build() == build()


def test_ties_are_broken_by_first_appearance() -> None:
    """Every word here but `the` occurs once, so the whole order below rank 0 is
    decided by the tiebreak, and `moon` precedes `river` because it is written
    first. Without a total order this test is a coin flip."""
    device = build(slots=1, per_slot=4)
    assert device.slots[0].alternatives == ["the", "moon", "river", "stone"]


def test_the_commonest_can_be_dropped() -> None:
    """The whole stoplist this package has, and naming it that is more honest than
    shipping one: a real stoplist is per-language data."""
    kept = build(slots=1, per_slot=3, drop_commonest=1)
    assert kept.slots[0].alternatives == ["moon", "river", "stone"]


def test_words_are_dealt_round_robin_so_every_ring_spans_the_range() -> None:
    """In blocks the first ring would hold the commonest words and the last the
    rarest, and every reading would be one register sliding into another."""
    device = build(slots=2, per_slot=3)
    first, second = (slot.alternatives for slot in device.slots)
    assert first == ["the", "river", "ember"]
    assert second == ["moon", "stone", "ash"]


def test_a_text_too_thin_to_fill_the_rings_is_refused() -> None:
    """Rather than returning short rings, which would make `combinations` a lie."""
    with pytest.raises(InputTooShort) as raised:
        from_text("one two three", PACK, device_id="thin", name="thin", slots=3, per_slot=4)
    assert raised.value.detail()["found"] == "3 distinct words"


def test_the_derived_device_is_an_address_space_like_any_other() -> None:
    """ADR 0031's arithmetic does not care where the alternatives came from, which
    is the point of putting the derivation behind `Device` rather than beside it."""
    device = build()
    assert device.radix == [6, 6, 6, 6]
    assert device.combinations == 1296
    for address in (0, 1, 999, 1295):
        assert device.address(device.at(address)) == address


def test_it_reaches_a_shipped_procedure_through_the_cartridge_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reason this needs no new catalogue row. A derived device is written out
    and read back by `load` exactly as a hand-written one is, and the rows that
    already select one alternative per slot then run on it unchanged."""
    device = build()
    (tmp_path / "sample.yaml").write_text(
        yaml.safe_dump(device.model_dump(exclude_none=True), allow_unicode=True),
        encoding="utf-8",
    )
    monkeypatch.setenv(DEVICE_PATH_ENV, str(tmp_path))
    reloaded = load("sample")
    assert reloaded == device
    turned = spin(reloaded, seed=5)
    assert all(select(turned, reloaded))


def test_the_source_records_how_the_rings_were_derived() -> None:
    """A `Device.source` is provenance, and a derived device's provenance is its
    derivation. Saying "the 24 most frequent words" is a fact about this device;
    it is not a claim that anyone historically made one."""
    device = build(slots=3, drop_commonest=2)
    assert "18 most frequent" in device.source
    assert "after the 2" in device.source
