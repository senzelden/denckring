"""The machine-readable view of the catalogue."""

import pytest

from denckring import describe, summaries
from denckring.core.catalogue import get as meta_for
from denckring.core.describe import runnable
from denckring.core.errors import UnknownProcedure


def test_describe_carries_what_the_loop_needs() -> None:
    described = describe("lipogram")
    assert described.id == "lipogram"
    assert described.name
    assert described.definition
    assert described.kind in {"restrictive", "constructive", "both"}
    assert "properties" in described.params


def test_the_param_schema_is_the_real_one() -> None:
    """Free from Pydantic, and the descriptions are already written."""
    described = describe("serial_lipogram")
    assert "unit" in described.params["properties"]
    assert described.params["properties"]["unit"]["enum"] == ["paragraph", "line"]


def test_scholarly_is_absent_unless_asked_for() -> None:
    """Browsing eighty procedures must not silently cost eighty provenance records."""
    assert describe("lipogram").scholarly is None
    assert describe("lipogram", scholarly=True).scholarly is not None


def test_scholarly_carries_the_apparatus() -> None:
    apparatus = describe("lipogram", scholarly=True).scholarly
    assert apparatus is not None
    assert apparatus.source


def test_an_unknown_id_raises_with_suggestions() -> None:
    with pytest.raises(UnknownProcedure):
        describe("lipogramm")


def test_summaries_lists_every_implemented_procedure() -> None:
    rows = summaries()
    assert len(rows) == 86
    assert all(row.id and row.name for row in rows)


def test_query_matches_ids_names_and_aliases() -> None:
    found = {row.id for row in summaries(query="lipogram")}
    assert "lipogram" in found
    assert "serial_lipogram" in found


def test_family_filters() -> None:
    rows = summaries(family="form")
    assert rows
    assert all(row.family == "form" for row in rows)


def test_runnable_only_hides_what_this_install_cannot_run() -> None:
    """A model offered a procedure it cannot run gets an error it cannot fix."""
    every = summaries()
    only = summaries(runnable_only=True)
    assert len(only) <= len(every)
    assert all(row.runnable for row in only)


def test_runnable_reports_what_is_missing() -> None:
    ok, missing = runnable(meta_for("dactylic_hexameter"))
    if not ok:
        assert "stress" in missing


def test_renga_is_runnable_wherever_haiku_is() -> None:
    """The syllabic batch's last defect: renga and haibun were gated on a
    capability nothing calls, which would have hidden two working procedures
    from every model on a core-only install."""
    assert runnable(meta_for("renga"))[0] == runnable(meta_for("haiku"))[0]
    assert runnable(meta_for("haibun"))[0] == runnable(meta_for("haiku"))[0]
