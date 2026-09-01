"""The machine-readable view of the catalogue."""

import pytest

from denckring import describe, summaries
from denckring.core.catalogue import get as meta_for
from denckring.core.describe import runnable
from denckring.core.errors import UnknownProcedure
from denckring.lang.en import EnglishPack


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


def test_the_generator_takes_its_own_schema() -> None:
    """`params` is the checker's model and does not carry `seed` — which is why
    a caller reading only `params` could not learn that `cut_up` takes one."""
    described = describe("cut_up")
    assert "seed" in described.apply_params["properties"]
    assert "seed" not in described.params["properties"]


def test_a_row_with_no_generator_has_no_apply_params() -> None:
    """Empty rather than absent or a copy of `params`: there is no `apply` to
    pass anything to, and saying so as `{}` keeps the field's type one thing."""
    assert describe("lipogram").apply_params == {}


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
    assert len(rows) == 121
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
    """A model offered a procedure it cannot run gets an error it cannot fix.

    On this install (data packs present), nothing is excluded — that state is
    worth covering too, but on its own it cannot prove the filter works; see
    `test_runnable_only_shrinks_under_a_core_only_pack` for that.
    """
    every = summaries()
    only = summaries(runnable_only=True)
    assert len(only) <= len(every)
    assert all(row.runnable for row in only)


def test_runnable_only_shrinks_under_a_core_only_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    """Capability-awareness is the point of `runnable()`. Force the install down to
    the core English pack (no lexicon, no phonemes, no stress) and check that
    `runnable_only` genuinely excludes rows, and only rows that are genuinely
    unrunnable."""
    monkeypatch.setattr("denckring.lang.get_pack", lambda lang="en": EnglishPack())
    every = summaries()
    only = summaries(runnable_only=True)
    assert len(every) == 121
    assert len(only) == 81
    assert len(only) < len(every)
    kept = {row.id for row in only}
    excluded = {row.id: row for row in every if row.id not in kept}
    assert excluded
    assert all(not row.runnable for row in excluded.values())


def test_runnable_reports_what_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("denckring.lang.get_pack", lambda lang="en": EnglishPack())
    ok, missing = runnable(meta_for("dactylic_hexameter"))
    assert not ok
    assert missing == ["stress"]


def test_describe_reports_the_languages_the_install_can_actually_run() -> None:
    """`meta.languages` is authored editorial scope; `runs_in` is computed from
    capabilities, so the two cannot drift into a false claim.

    `n_plus_7` was this test's original negative case, but chapter 6 gave French
    `lexicon.nouns`, so it now runs there and can no longer stand in for "still
    missing a capability". `haiku` needed `syllables.heuristic` next, but
    chapter 6 tranche B (Task 5, 2026-09-01) gave `fr` exactly that, so it runs
    too now. `sonnet` needs `stress`, which French has none of and never will
    (spec D2).
    """
    description = describe("anagram")
    assert "fr" in description.runs_in
    assert "fr" not in describe("sonnet").runs_in


def test_renga_and_haibun_match_haikus_catalogued_requirements() -> None:
    """Catalogue consistency, not capability coverage: renga and haibun declare
    the same `requires` as haiku, so nothing in the catalogue can silently gate
    two working procedures on a capability haiku doesn't need. (`runnable()`
    itself is exercised by the core-only-pack tests above.)"""
    assert runnable(meta_for("renga"))[0] == runnable(meta_for("haiku"))[0]
    assert runnable(meta_for("haibun"))[0] == runnable(meta_for("haiku"))[0]
