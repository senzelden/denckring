"""The four metrical licences, each its own switch and each off by default (ADR 0065)."""

from __future__ import annotations

from typing import Any

import pytest

from conftest import load_golden_cases
from denckring import check
from denckring.core import prosody
from denckring.core.base import LicenceParams
from denckring.core.prosody import NO_LICENCES, SHIFTABLE, Licences, licensed_forms, line_metre
from denckring.core.registry import all_procedures
from denckring.lang import get_pack

PENTAMETER = ["0101010101"]
SWITCHES = ("initial_inversion", "secondary_stress", "stress_shift", "diaeresis")

#: One constructed line per licence, each failing the bare pentameter for one reason
#: only. Every line is built so that no other licence alone could rescue it, which is
#: what lets the table below assert a switch admits its own licence and nothing else.
LINES = {
    # `Either` is 10 where the first foot wants 01.
    "initial_inversion": "Either the moon can see above the tree",
    # `disapproves` is 001 where the line wants 101, away from the line's start.
    "secondary_stress": "a cat that disapproves the moon at night",
    # `without` is 01 where the line wants 10, away from the line's start.
    "stress_shift": "the cat sat without the moon at the night",
    # `ambrosial` is three syllables in the dictionary; the line needs four.
    "diaeresis": "ambrosial light can fall on the tree",
}


def scans(line: str, licences: Licences = NO_LICENCES) -> bool:
    return not line_metre(line, get_pack("en"), PENTAMETER, 0, licences=licences).violations


@pytest.mark.parametrize("licence", SWITCHES)
def test_each_line_fails_with_every_switch_off(licence: str) -> None:
    assert not scans(LINES[licence])


@pytest.mark.parametrize("licence", SWITCHES)
@pytest.mark.parametrize("switch", SWITCHES)
def test_a_switch_admits_its_own_licence_and_no_other(licence: str, switch: str) -> None:
    """The whole table, not the diagonal: a switch that also admitted a neighbour's
    licence would pass every diagonal test and still be a leak."""
    assert scans(LINES[licence], Licences(**{switch: True})) is (switch == licence)


def test_two_licences_in_one_line_need_both_switches() -> None:
    """Milton's "When I consider" in miniature: an inverted first foot and a shifted
    `without`. Either switch alone leaves the other fault standing."""
    line = "Either the cat sat without moon at night"
    assert not scans(line, Licences(initial_inversion=True))
    assert not scans(line, Licences(stress_shift=True))
    assert scans(line, Licences(initial_inversion=True, stress_shift=True))


def test_inversion_is_line_initial_only() -> None:
    """A reversed foot mid-line is a different licence, and not one this admits."""
    assert not scans("the moon Either can see above the tree", Licences(initial_inversion=True))


def test_evidence_names_the_licence_a_word_was_read_through() -> None:
    """A writer told a line scans should be able to see that it scanned on a
    licence, and which; the dictionary's own reading carries no note."""
    pack = get_pack("en")
    every = Licences(True, True, True, True)
    read = line_metre(LINES["initial_inversion"], pack, PENTAMETER, 0, licences=every)
    assert read.evidence[0].value == "10 (initial_inversion)"
    assert read.evidence[0].basis == "dictionary"
    assert read.evidence[5].value == "01"
    read = line_metre(LINES["secondary_stress"], pack, PENTAMETER, 0, licences=every)
    assert [e.value for e in read.evidence if "(" in e.value] == ["101 (secondary_stress)"]


def test_a_line_that_scans_plainly_claims_no_licence() -> None:
    """Licences are a second pass, so a line the dictionary scans is never reported
    as needing one."""
    pack = get_pack("en")
    plain = "the cat can see the moon above the tree"
    read = line_metre(plain, pack, PENTAMETER, 0, licences=Licences(True, True, True, True))
    assert not read.violations
    assert not any("(" in e.value for e in read.evidence)


def test_secondary_stress_spares_short_words_and_the_primary_s_neighbours() -> None:
    pack = get_pack("en")
    on = Licences(secondary_stress=True)
    assert licensed_forms("disapproves", pack, ["001"], on) == [("101", "secondary_stress")]
    assert licensed_forms("lady", pack, ["10"], on) == []
    # `ambrosial` is 010: both of its unstressed syllables touch the primary.
    assert licensed_forms("ambrosial", pack, ["010"], on) == []


def test_two_promoted_syllables_are_never_adjacent() -> None:
    forms = [f for f, _ in licensed_forms("x", get_pack("en"), ["?01000"], Licences(True, True))]
    assert forms == ["?01010", "?01001"]


def test_the_shiftable_list_is_disyllables_the_dictionary_carries() -> None:
    """The list is editorial (ADR 0065); what is not editorial is that a word on it
    is one the dictionary stresses as two syllables, or the switch would be adding a
    reading to a word it cannot have."""
    pack = get_pack("en")
    for word in SHIFTABLE:
        assert 2 in {len(form) for form in pack.stress_patterns(word)}, word


def test_diaeresis_measured_on_the_two_words_that_asked_for_it() -> None:
    """`ambrosial` gains a fourth syllable whose last vowel is free; `superfluous`
    gains one too, but CMUdict stresses its first syllable, which no diaeresis
    moves, so Milton's "That with superfluous burden" still does not scan."""
    pack = get_pack("en")
    on = Licences(diaeresis=True)
    assert licensed_forms("ambrosial", pack, ["010"], on) == [("010?", "diaeresis")]
    assert licensed_forms("superfluous", pack, ["10?"], on) == [("100?", "diaeresis")]
    assert not scans("That with superfluous burden loads the day,", on)


@pytest.mark.parametrize("word", ["outward", "equal", "language", "volume", "argue"])
def test_diaeresis_leaves_glides_no_verse_splits(word: str) -> None:
    """The brief's bare phones rule fired on 135 of the 5,000 commonest words, most
    of them these shapes; each exclusion in `_diaereses` is here."""
    pack = get_pack("en")
    forms = pack.stress_patterns(word)
    assert licensed_forms(word, pack, forms, Licences(diaeresis=True)) == []


def test_the_dictionary_licences_are_english_only() -> None:
    """They read CMUdict or English spelling; a German word has neither."""
    pack = get_pack("de")
    every = Licences(True, True, True, True)
    assert licensed_forms("Wanderer", pack, pack.stress_patterns("Wanderer"), every) == []


#: Goethe, Iphigenie auf Tauris (1787), I.1, as in `test_feminine_ending.py`.
IPHIGENIE = """Heraus in eure Schatten, rege Wipfel
Des alten, heil'gen, dichtbelaubten Haines,
Wie in der Göttin stilles Heiligthum
Tret' ich noch jetzt mit schauderndem Gefühl,
Als wenn ich sie zum erstenmal beträte,
Und es gewöhnt sich nicht mein Geist hierher."""


def test_a_german_text_is_read_the_same_with_the_english_switches_on() -> None:
    off = check("blank_verse", IPHIGENIE, lang="de", feminine_ending=True)
    on = check(
        "blank_verse",
        IPHIGENIE,
        lang="de",
        feminine_ending=True,
        secondary_stress=True,
        stress_shift=True,
        diaeresis=True,
    )
    assert on.model_dump() == off.model_dump()


#: Rows that scan stress and take no licences, each for a stated reason. The four
#: switches are licences of English accentual-syllabic verse (ADR 0065); these rows scan
#: classical or dactylic patterns as sets of feet with substitutions and anceps already,
#: where a reversed first foot or a promoted syllable is not the licence the form takes.
OUTSIDE_THE_LICENCES = {
    "alcaic_stanza": "classical stanza, read accentually as fixed patterns",
    "dactylic_hexameter": "dactyl-or-spondee feet, enumerated as pattern sets",
    "double_dactyl": "dactylic dimeter, fixed patterns",
    "elegiac_couplet": "hexameter and pentameter as dactylic pattern sets",
    "sapphic_stanza": "classical stanza, fixed patterns with anceps",
}


def _licensed_rows() -> list[str]:
    return sorted(
        pid
        for pid, procedure in all_procedures().items()
        if issubclass(procedure.params_model(), LicenceParams)
    )


def test_every_row_that_can_fault_stress_takes_the_licences() -> None:
    """Found by behaviour, not by params: a row whose checker can raise `wrong_stress`
    scans stress, and a row that scans stress takes the four switches unless it is
    listed above with its reason. `alexandrine` counts syllables only and raises no
    `wrong_stress`, so it needs no entry."""
    missing = [
        pid
        for pid, procedure in all_procedures().items()
        if "wrong_stress" in procedure.rules
        and pid not in OUTSIDE_THE_LICENCES
        and not set(SWITCHES) <= set(procedure.params_model().model_fields)
    ]
    assert not missing, missing


def test_the_rows_outside_the_licences_are_still_rows_that_scan_stress() -> None:
    """An entry for a row that gained the switches, or stopped scanning stress, is an
    exemption nobody needs."""
    procedures = all_procedures()
    stale = [
        pid
        for pid in OUTSIDE_THE_LICENCES
        if "wrong_stress" not in procedures[pid].rules
        or issubclass(procedures[pid].params_model(), LicenceParams)
    ]
    assert not stale, stale


def test_a_trochaic_line_may_open_on_an_iamb() -> None:
    """The reversal is of the first foot, whatever the metre: 10 becomes 01 here."""
    line = "beneath the dark silver water"
    assert not check("trochaic_tetrameter", line).satisfied
    assert check("trochaic_tetrameter", line, initial_inversion=True).satisfied
    assert prosody.inverted("10101010") == "01101010"
    assert prosody.inverted("0101010101") == "1001010101"
    assert prosody.inverted("?101") is None


@pytest.mark.parametrize("procedure", _licensed_rows())
def test_every_row_passes_its_switches_to_the_scan(
    procedure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A row that took the params and dropped them would look wired and not be. The
    first line is replaced with one the dictionary cannot scan, so the scan reaches
    its licensed pass."""
    seen: list[Licences] = []
    real = prosody.metre_violations

    def spy(*args: Any, **kwargs: Any) -> prosody.MetreResult:
        seen.append(kwargs.get("licences", NO_LICENCES))
        return real(*args, **kwargs)

    monkeypatch.setattr(prosody, "metre_violations", spy)
    case = next(
        c
        for c in load_golden_cases()
        if c.procedure == procedure
        and c.satisfied
        and c.lang == "en"
        # A ballade with `metre` unset scans nothing, so it cannot reach the scan.
        and c.params.get("metre", "") is not None
    )
    lines = case.text.split("\n")
    text = "\n".join([LINES["initial_inversion"], *lines[1:]])
    every = dict.fromkeys(SWITCHES, True)
    check(procedure, text, lang="en", **{**case.params, **every})
    assert Licences(**every) in seen
