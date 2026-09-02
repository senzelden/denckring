"""ADR 0033: the catalogue has two layers, and only one of them has a target.

Every test here that counts anything patches in a synthetic instrument row, because
the shipped catalogue has none and is expected to have none for some time — a counter
sitting at zero cannot tell you whether it is filtering correctly.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from denckring.core import catalogue
from denckring.core.protocol import LAYERS, Meta
from denckring.eval import harness


def _row(pid: str, **overrides: Any) -> Meta:
    """A valid row, taken from a shipped one so only the layer is under test."""
    return Meta.model_validate({**catalogue.get("lipogram").model_dump(), "id": pid, **overrides})


@pytest.fixture
def with_one_instrument(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shipped catalogue plus a single instrument row."""
    entries = {**catalogue.load(), "temurah": _row("temurah", layer="instrument")}
    monkeypatch.setattr(catalogue, "load", lambda: entries)


def test_a_row_that_names_no_layer_is_a_verfahren() -> None:
    """The default is what keeps every row written before the split meaning what it
    meant (D1)."""
    assert _row("lipogram").layer == "verfahren"


def test_an_instrument_row_is_accepted() -> None:
    assert _row("temurah", layer="instrument").layer == "instrument"


def test_an_unknown_layer_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _row("temurah", layer="device")


def test_the_two_layers_are_the_only_layers() -> None:
    assert LAYERS == ("verfahren", "instrument")


def test_the_layers_partition_the_catalogue() -> None:
    verfahren = set(catalogue.ids("verfahren"))
    instruments = set(catalogue.ids("instrument"))
    assert not verfahren & instruments
    assert verfahren | instruments == set(catalogue.ids())


def test_the_five_part_line_counts_verfahren_only(with_one_instrument: None) -> None:
    """D3: adding an instrument must not move the denominator every coverage figure in
    ADRs 0025 through 0032 was recorded against."""
    assert harness.status().catalogued == len(catalogue.ids("verfahren"))
    assert "instrument" not in harness.status().line()


def test_the_instrument_counter_is_a_line_of_its_own(with_one_instrument: None) -> None:
    coverage = harness.status()
    assert coverage.instruments == 1
    assert "1 instrument" in coverage.instrument_line()


def test_an_instrument_is_never_counted_as_implementable(with_one_instrument: None) -> None:
    """The synthetic row carries `checkability: self`, inherited from `lipogram`, so
    only the layer keeps it out of the implementable set."""
    assert "temurah" not in harness.implementable_ids()


def test_an_instrument_is_never_counted_as_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    """A registered procedure whose row is an instrument still leaves the five-part
    line, so `implemented` cannot drift away from `catalogued` by way of the registry."""
    entries = {**catalogue.load(), "lipogram": _row("lipogram", layer="instrument")}
    monkeypatch.setattr(catalogue, "load", lambda: entries)
    assert "lipogram" not in harness.implemented_ids()
    assert "lipogram" not in harness.validated_ids()
