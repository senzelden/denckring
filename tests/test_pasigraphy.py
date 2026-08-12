"""Kircher's universal writing, and what it costs to cross.

Every vocabulary here is synthetic. Kircher's own has not been transcribed into
anything this project could verify, so none ships and none is invented.
"""

import json
from typing import Any

import pytest

from denckring import check, get
from denckring.core import pasigraph
from denckring.core.errors import MalformedTable
from denckring.core.protocol import Constructive

TABLE = json.dumps(
    {
        "1": {"la": "deus", "de": "gott", "en": "god"},
        "2": {"la": "lux", "de": "licht", "en": "light"},
        "3": {"la": "aqua", "de": "wasser"},
        "4": {"la": "verbum", "de": "wort", "en": "word"},
        "5": {"la": "sermo", "de": "wort", "en": "word"},
    }
)
# Annotated so mypy does not try to bind the spread against `lang`.
ACROSS: dict[str, Any] = {"table": TABLE, "from_language": "la", "to_language": "en"}


def test_a_faithful_rendering_is_satisfied() -> None:
    assert check("pasigraphy", "god light word", source="deus lux verbum", **ACROSS).satisfied


def test_a_wrong_word_is_a_violation() -> None:
    report = check("pasigraphy", "god light stone", source="deus lux verbum", **ACROSS)
    assert not report.satisfied
    assert report.violations[0].rule == "wrong_rendering"


def test_a_rendering_that_shows_its_gaps_is_still_the_rendering() -> None:
    """The crossing lost something; the rendering is still correct."""
    report = check("pasigraphy", "god — light", source="deus aqua lux", **ACROSS)
    assert report.satisfied
    assert report.metrics["stranded"] == 1.0


def test_requiring_a_complete_crossing_fails_on_a_gap() -> None:
    report = check(
        "pasigraphy", "god — light", source="deus aqua lux", require_complete=True, **ACROSS
    )
    assert not report.satisfied
    assert any(v.rule == "no_word_at_number" for v in report.violations)


def test_a_word_the_table_does_not_number_is_counted() -> None:
    report = check("pasigraphy", "god —", source="deus fulmen", **ACROSS)
    assert report.metrics["unnumbered"] == 1.0
    strict = check("pasigraphy", "god —", source="deus fulmen", require_complete=True, **ACROSS)
    assert any(v.rule == "no_number_for_word" for v in strict.violations)


def test_two_words_arriving_as_one_is_the_loss_worth_naming() -> None:
    """verbum and sermo are distinct in Latin and the same word in English."""
    report = check("pasigraphy", "word word", source="verbum sermo", **ACROSS)
    assert report.satisfied
    assert report.metrics["colliding_numbers"] == 1.0


def test_collisions_are_words_reachable_from_several_numbers() -> None:
    table = pasigraph.parse(TABLE)
    assert table.collisions("en") == {"word": ["4", "5"]}
    assert table.collisions("la") == {}


def test_the_table_reports_the_languages_it_carries() -> None:
    assert pasigraph.parse(TABLE).languages == ["de", "en", "la"]


def test_sending_produces_what_the_checker_accepts() -> None:
    procedure = get("pasigraphy")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply("deus lux verbum", **ACROSS)
    assert check("pasigraphy", produced, source="deus lux verbum", **ACROSS).satisfied


def test_the_crossing_runs_in_either_direction() -> None:
    both: dict[str, Any] = {"table": TABLE, "from_language": "la", "to_language": "de"}
    procedure = get("pasigraphy")
    assert isinstance(procedure, Constructive)
    assert procedure.apply("deus lux", **both) == "gott licht"


@pytest.mark.parametrize(
    ("text", "reason"), [("", "empty"), ("{not json", "JSON"), ("{}", "no numbered")]
)
def test_a_table_that_cannot_be_read_says_why(text: str, reason: str) -> None:
    with pytest.raises(MalformedTable, match=reason):
        pasigraph.parse(text)


def test_no_historical_vocabulary_ships() -> None:
    """The mechanism is Kircher's; the words must be the reader's."""
    from denckring.core import catalogue

    assert "travels with this package" in (catalogue.get("pasigraphy").notes or "")
