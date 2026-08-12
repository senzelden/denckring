"""Kircher's box, kept to the part that is about writing.

Every tablet here is synthetic. Kircher's own runs to pages of Musurgia
Universalis book VIII and has not been transcribed into anything verifiable, so
none ships and none is invented.
"""

import json
from typing import Any

import pytest

from denckring import check, get
from denckring.core import arca
from denckring.core.errors import MalformedTable, UnsettablePhrase
from denckring.core.protocol import Constructive

PINAKES = json.dumps(
    {
        "source": "synthetic, in the shape of a pinax",
        "tones": ["I", "II", "III"],
        "syntagmata": {
            "1": {"4": ["5 3 1 3", "1 3 5 3"], "6": ["5 5 3 1 3 5", "1 1 3 5 3 1"]},
            "2": {"4": ["5 4 3 2", "3 2 1 2"]},
        },
    }
)
TEXT = "the cat sat down\nthe dog ran home to eat"
BOX: dict[str, Any] = {"pinakes": PINAKES}


def test_a_setting_drawn_from_the_tablet_is_satisfied() -> None:
    setting = "5 3 1 3\n5 5 3 1 3 5"
    assert check("arca_musarithmica", setting, source=TEXT, **BOX).satisfied


def test_a_pattern_the_tablet_does_not_offer_is_a_violation() -> None:
    report = check("arca_musarithmica", "9 9 9 9\n5 5 3 1 3 5", source=TEXT, **BOX)
    assert not report.satisfied
    assert report.violations[0].rule == "pattern_not_on_the_tablet"


def test_a_pattern_from_the_wrong_length_is_a_violation() -> None:
    """The tablet is indexed by syllable count; a four-syllable pattern will not do."""
    report = check("arca_musarithmica", "5 3 1 3\n5 3 1 3", source=TEXT, **BOX)
    assert any(v.rule == "pattern_not_on_the_tablet" for v in report.violations)


def test_a_phrase_the_box_cannot_set_is_reported() -> None:
    report = check(
        "arca_musarithmica", "5 3 1 3", source="a phrase far too long for this box", **BOX
    )
    assert any(v.rule == "no_tablet_for_length" for v in report.violations)


def test_the_florid_syntagma_offers_different_patterns() -> None:
    assert check(
        "arca_musarithmica", "3 2 1 2", source="the cat sat down", syntagma="2", **BOX
    ).satisfied
    assert not check("arca_musarithmica", "3 2 1 2", source="the cat sat down", **BOX).satisfied


def test_a_tone_the_table_does_not_name_is_counted_against_the_score() -> None:
    """A violation the score never saw would let the report say yes and list faults."""
    good = check("arca_musarithmica", "5 3 1 3", source="the cat sat down", tonus="II", **BOX)
    assert good.satisfied and not good.violations
    bad = check("arca_musarithmica", "5 3 1 3", source="the cat sat down", tonus="XI", **BOX)
    assert not bad.satisfied
    assert bad.violations[0].rule == "unknown_tone"


def test_setting_produces_what_the_checker_accepts() -> None:
    procedure = get("arca_musarithmica")
    assert isinstance(procedure, Constructive)
    for seed in range(6):
        setting = procedure.apply(TEXT, seed=seed, **BOX)
        assert check("arca_musarithmica", setting, source=TEXT, **BOX).satisfied


def test_setting_refuses_a_phrase_the_box_cannot_hold() -> None:
    procedure = get("arca_musarithmica")
    assert isinstance(procedure, Constructive)
    with pytest.raises(UnsettablePhrase, match="covers: 4, 6"):
        procedure.apply("a phrase far too long for this box", **BOX)


def test_a_bare_tablet_needs_no_syntagma_wrapper() -> None:
    tablets = arca.parse(json.dumps({"4": ["a b c d"]}))
    assert tablets.patterns(4) == ["a b c d"]
    assert tablets.lengths() == [4]


def test_the_patterns_are_never_read() -> None:
    """Put stress patterns in the same table and the machine still works."""
    metrical = json.dumps({"4": ["0101"], "6": ["010101"]})
    procedure = get("arca_musarithmica")
    assert isinstance(procedure, Constructive)
    setting = procedure.apply(TEXT, pinakes=metrical, seed=0)
    assert setting.split("\n") == ["0101", "010101"]


@pytest.mark.parametrize(
    ("text", "reason"), [("", "empty"), ("{not json", "JSON"), ('{"4": []}', "no patterns")]
)
def test_a_tablet_that_cannot_be_read_says_why(text: str, reason: str) -> None:
    with pytest.raises(MalformedTable, match=reason):
        arca.parse(text)
