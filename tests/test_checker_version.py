"""Per-row checker versions (ADR 0061)."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

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


def test_a_composite_names_the_rows_its_entries_delegate_to() -> None:
    """`telestich` inherits `acrostic`, so an `acrostic` bump moves this verdict while
    neither `telestich`'s nor the composite's own version moves: the closure over
    `composes` is what keeps the report naming every row that decided it (ADR 0061)."""
    report = denckring.check(
        "multiple_constraint",
        "abc",
        constraints=[
            {"id": "telestich", "params": {"target": "c"}},
            {"id": "lipogram", "params": {"forbidden": "e"}},
        ],
    )
    assert report.provenance is not None
    assert "acrostic" in report.provenance.checkers
    assert report.provenance.checkers["acrostic"] == get("acrostic").checker_version


def test_a_composite_names_everything_its_entry_names_alone() -> None:
    """`sestina` runs `quenina`: embedded in a composite, it must bring `quenina` with
    it, as the bare `sestina` report does."""
    alone = denckring.check("sestina", "abc")
    composite = denckring.check(
        "multiple_constraint",
        "abc",
        constraints=[{"id": "sestina"}, {"id": "lipogram", "params": {"forbidden": "e"}}],
    )
    assert alone.provenance is not None
    assert composite.provenance is not None
    assert "quenina" in alone.provenance.checkers
    assert set(alone.provenance.checkers) <= set(composite.provenance.checkers)


def test_a_production_names_the_generator_row() -> None:
    production = denckring.produce("anagram", "listen")
    assert production.provenance is not None
    assert production.provenance.checkers == {"anagram": get("anagram").checker_version}


def _referenced_rows(path: Path, classes: dict[str, str]) -> set[str]:
    """Ids of registered rows a procedure module calls through or subclasses.

    Finds `get("<id>")` with a literal id, a registered class instantiated and then
    `check`/`_check`/`produce`/`_produce`d, and a registered class used as a base.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Name)
                and func.id == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                found.add(node.args[0].value)
            if (
                isinstance(func, ast.Attribute)
                and func.attr in {"check", "_check", "produce", "_produce"}
                and isinstance(func.value, ast.Call)
                and isinstance(func.value.func, ast.Name)
                and func.value.func.id in classes
            ):
                found.add(classes[func.value.func.id])
        elif isinstance(node, ast.ClassDef):
            found |= {b.id for b in node.bases if isinstance(b, ast.Name)} & set(classes)
    return {classes.get(name, name) for name in found}


def test_a_row_names_every_other_row_it_runs() -> None:
    """The next delegating row cannot forget: a static call or subclass of another
    registered row must appear in that row's `composes` (ADR 0061)."""
    rows = denckring.all_procedures()
    classes = {type(p).__name__: pid for pid, p in rows.items()}
    by_module: dict[str, list[str]] = {}
    for pid, p in rows.items():
        by_module.setdefault(type(p).__module__, []).append(pid)
    missing: list[str] = []
    for module, ids in by_module.items():
        path = Path(importlib.import_module(module).__file__ or "")
        referenced = _referenced_rows(path, classes) - set(ids)
        for pid in ids:
            # Subclassing counts only for the class that subclasses, but a module with
            # one row per class makes the module-level reading exact.
            missing += [
                f"{pid} -> {other}"
                for other in sorted(referenced - set(get(pid).composes))
                if other in rows
            ]
    assert not missing, missing
