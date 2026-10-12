"""Per-row checker versions (ADR 0061)."""

from __future__ import annotations

import pytest

import denckring
from denckring.core.registry import get


def test_every_row_publishes_its_checker_version() -> None:
    for pid in denckring.all_procedures():
        assert denckring.describe(pid).checker_version == get(pid).checker_version >= 1


def test_history_ends_at_the_current_version() -> None:
    for pid in denckring.all_procedures():
        history = denckring.checker_history(pid)
        assert history, pid
        assert [c.version for c in history] == list(range(1, len(history) + 1)), pid
        assert history[-1].version == get(pid).checker_version, pid


def test_history_names_only_registered_rows() -> None:
    from denckring.eval.history import load

    assert set(load()) <= set(denckring.all_procedures())


def test_history_of_an_unknown_row_raises() -> None:
    with pytest.raises(denckring.UnknownProcedure):
        denckring.checker_history("no_such_row")


def test_a_report_names_the_checker_that_decided_it() -> None:
    report = denckring.check("lipogram", "abc", forbidden="e")
    assert report.provenance is not None
    assert report.provenance.checkers == {"lipogram": get("lipogram").checker_version}


def test_a_composite_names_each_row_once() -> None:
    report = denckring.check(
        "multiple_constraint",
        "abc",
        constraints=[
            {"id": "lipogram", "params": {"forbidden": "e"}},
            {"id": "lipogram", "params": {"forbidden": "z"}},
        ],
    )
    assert report.provenance is not None
    assert set(report.provenance.checkers) == {"multiple_constraint", "lipogram"}


def test_a_production_names_the_generator_row() -> None:
    production = denckring.produce("anagram", "listen")
    assert production.provenance is not None
    assert production.provenance.checkers == {"anagram": get("anagram").checker_version}
