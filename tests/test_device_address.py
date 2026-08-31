"""A device is an address space, and it knows which of its readings are real.

Two schema additions from `docs/expansion_ideas/HANDOVER-denckring-method-zoo.md`,
its own top two by value per unit of change. Neither adds a catalogue entry; both
change what the devices already shipped can be asked.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

from denckring.core.base import ConstructiveProcedure
from denckring.core.device import DEVICE_PATH_ENV, load, segment
from denckring.core.errors import InvalidParams, MissingCapability
from denckring.core.registry import get

RINGS = load("harsdoerffer_1651")

#: A four-reading device: `Haus`, `Hand`, `Xqaus`, `Xqand` — two real German
#: words and two neglected forms. The shipped rings cannot stand in for it:
#: 20,000 random spins of them produced no attested word at all, which is
#: al-Khalīl's point about combinatorial devices and also a reason a device that
#: attests *sometimes* has to be built rather than found.
#: `tests/test_device.py` writes synthetic devices onto the search path the same
#: way.
#:
#: The neglected onset is `Xq` and not a plausible German one: ADR 0015 records
#: that the Wikidata lexicon answers "could this be a German word" rather than
#: "is this in a dictionary", and it knows `Baus` and `Band`, which were the
#: first pair tried here.
SYNTHETIC = {
    "id": "synthetic_mask",
    "name": "two words and two neglected forms",
    "source": "constructed for this test",
    "slots": [
        {"name": "onset", "alternatives": ["H", "Xq"]},
        {"name": "rest", "alternatives": ["aus", "and"]},
    ],
    "mask": {"kind": "lexicon", "source": "lexicon.words"},
}


def _install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **overrides: object) -> str:
    device = {**SYNTHETIC, **overrides}
    (tmp_path / "synthetic_mask.yaml").write_text(yaml.safe_dump(device), encoding="utf-8")
    monkeypatch.setenv(DEVICE_PATH_ENV, str(tmp_path))
    return str(device["id"])


def _generator() -> ConstructiveProcedure[Any, Any]:
    procedure = get("denckring")
    assert isinstance(procedure, ConstructiveProcedure)
    return procedure


# --- the address space --------------------------------------------------------


def test_the_radix_is_the_slot_lengths_with_a_skip_counted() -> None:
    """The mixed base the arithmetic runs in. Harsdörffer's transcription carries
    49, 60, 12, 120 and 23; the prefix and suffix rings are skippable, so each of
    those two can come up one more way than it has alternatives."""
    assert RINGS.radix == [50, 60, 12, 120, 24]
    assert RINGS.combinations == 50 * 60 * 12 * 120 * 24


@pytest.mark.parametrize("address", [0, 1, 12345, 52699, 103_679_999])
def test_address_and_at_are_inverse(address: int) -> None:
    """Piṅgala names both directions — `naṣṭa` address-to-pattern, `uddiṣṭa`
    pattern-to-address — and naming both is the claim that they are a pair."""
    assert RINGS.address(RINGS.at(address)) == address


def test_the_first_slot_is_the_most_significant_digit() -> None:
    """A choice, and stated as one: sources differ on which end of a prastāra row
    carries the low-order position. Incrementing turns the last ring, which is
    what an odometer does and what the reading order suggests."""
    first, second = RINGS.at(0), RINGS.at(1)
    assert first[:-1] == second[:-1]
    assert first[-1] != second[-1]


def test_address_zero_is_every_ring_at_its_first_alternative() -> None:
    """Rather than every optional ring skipped, which is the other place a `""`
    could have been made to sort."""
    assert RINGS.at(0) == [slot.alternatives[0] for slot in RINGS.slots]


def test_a_skipped_optional_ring_reads_as_empty_and_has_an_address() -> None:
    last = RINGS.at(RINGS.combinations - 1)
    assert last[0] == "" and last[-1] == ""
    assert RINGS.address(last) == RINGS.combinations - 1


def test_an_address_outside_the_space_is_refused() -> None:
    for address in (-1, RINGS.combinations):
        with pytest.raises(IndexError):
            RINGS.at(address)


def test_a_reading_the_device_cannot_produce_is_refused() -> None:
    """Rather than returning a nearby address, which a caller could not tell from
    a right one."""
    reading = RINGS.at(0)
    with pytest.raises(ValueError, match="does not carry"):
        RINGS.address([*reading[:-1], "zzz"])
    with pytest.raises(ValueError, match="slots"):
        RINGS.address(reading[:2])


def test_a_real_german_word_has_a_ring_address() -> None:
    """The two halves meeting: `segment` says the rings can spell `Abbildung`, and
    `address` says where. This is the whole protocol on one word."""
    reading = segment("Abbildung", RINGS)
    assert reading is not None
    assert reading == ["Ab", "B", "i", "ld", "ung"]
    assert RINGS.address(reading) == 52699
    assert RINGS.at(52699) == reading


# --- the muhmal mask ----------------------------------------------------------


def test_the_shipped_rings_declare_a_mask_that_holds_rather_than_drops() -> None:
    """Al-Khalīl does not discard the neglected forms; he enumerates and flags
    them, and that distinction is the content of the device."""
    assert RINGS.mask is not None
    assert RINGS.mask.source == "lexicon.words"
    assert RINGS.mask.unmarked_policy == "hold"


def test_the_disputed_totals_are_recorded_and_none_of_them_is_the_computed_one() -> None:
    """Three published figures, none reconciling with the inventory this device
    carries. Recorded rather than adjudicated, and not adopted: `combinations` is
    computed from the slots."""
    values = {total.value for total in RINGS.disputed_totals}
    assert len(values) == 3
    assert RINGS.combinations not in values
    # The figure that circulates most widely cannot be a product of rings of 12
    # and 120 at all, which is the arithmetic that makes it disputed rather than
    # merely different.
    assert 97_209_600 % 144 != 0
    assert all(total.source for total in RINGS.disputed_totals)


def test_a_line_of_a_device_keeps_the_mask_and_not_the_disputed_totals() -> None:
    """A mask is a claim about readings, which a line has; a disputed total is a
    claim about the whole device, and attaching it to one line would assert the
    literature disputed a number nobody published."""
    line = RINGS.for_line(0)
    assert line.mask == RINGS.mask
    assert line.disputed_totals == []


def test_the_mask_marks_every_reading_as_attested_or_neglected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Al-Khalīl's device: enumerate the space, then say which members are real.
    Two of these four are German words and two are not, and the generator says so
    about its own output rather than leaving a reader to check."""
    device = _install(tmp_path, monkeypatch)
    production = _generator().produce(
        "", lang="de", device=device, seed=3, max_results=4, attestation="mask"
    )
    marks = {candidate.text: candidate.metrics["attested"] for candidate in production.candidates}
    assert marks["Haus"] == 1.0
    assert marks["Hand"] == 1.0
    assert marks["Xqaus"] == 0.0
    assert marks["Xqand"] == 0.0


def test_holding_ranks_the_attested_first_without_discarding_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`hold` is the default because it is what the source does. The neglected
    forms stay in the result and stay flagged; what changes is the order, so
    `apply` — which reads `texts[0]` — hands back a real word."""
    device = _install(tmp_path, monkeypatch)
    production = _generator().produce(
        "", lang="de", device=device, seed=3, max_results=4, attestation="mask"
    )
    assert len(production.candidates) == 4
    assert production.candidates[0].metrics["attested"] == 1.0
    assert production.candidates[-1].metrics["attested"] == 0.0
    assert _generator().apply("", lang="de", device=device, seed=3, attestation="mask") in {
        "Haus",
        "Hand",
    }


def test_dropping_keeps_only_the_attested(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    device = _install(
        tmp_path,
        monkeypatch,
        mask={"kind": "lexicon", "source": "lexicon.words", "unmarked_policy": "drop"},
    )
    production = _generator().produce(
        "", lang="de", device=device, seed=3, max_results=4, attestation="mask"
    )
    assert {candidate.text for candidate in production.candidates} == {"Haus", "Hand"}


def test_the_mask_is_off_unless_asked_for(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """So a core-only install spins exactly as it always has, and nothing acquires
    a data dependency by accident."""
    device = _install(tmp_path, monkeypatch)
    production = _generator().produce("", lang="de", device=device, seed=3, max_results=4)
    assert all(candidate.metrics == {} for candidate in production.candidates)


def test_asking_a_device_with_no_mask_is_refused_rather_than_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = _install(tmp_path, monkeypatch, mask=None)
    with pytest.raises(InvalidParams, match="no validity mask"):
        _generator().produce("", lang="de", device=device, attestation="mask")


def test_asking_a_pack_that_cannot_answer_is_refused_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`lexicon.words` was this test's original subject, but chapter 6 gave
    French a lexicon, so it can say whether a reading is attested now and no
    longer illustrates a pack that cannot answer. `phonemes` still does — this
    chapter ships no phonetic data for French — and naming the capability is
    what ADR 0004 asks of every unmet requirement, whichever one it is."""
    device = _install(tmp_path, monkeypatch, mask={"kind": "lexicon", "source": "phonemes"})
    with pytest.raises(MissingCapability, match=r"phonemes"):
        _generator().produce("", lang="fr", device=device, attestation="mask")
