"""`Report.estimated`: whether a verdict rests on anything estimated (audit B8).

denckring-bench leaves a verdict unscored when it rests on a guess, and read
`metrics["estimated_words"]` to decide, a key outside the stability promise. The
metric and `evidence` each record cases the other misses, so the signal has to read
both; these tests hold it to one case of each kind, and to the rule that a row whose
reading is exact never reports one.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from typing import Any

import pytest

import denckring
from denckring import check
from denckring.core.protocol import Lang, Report

VOSS = "Sage mir, Muse, die Taten des vielgewanderten Mannes"
DAVY = "Sir Humphry Davy\nAbominated gravy.\nHe lived in the odium\nOf having discovered sodium."


def test_a_word_counted_from_spelling_without_evidence_is_estimated() -> None:
    """`proteus_verse` discloses its guesses only in the metric."""
    report = check("proteus_verse", VOSS, lang="de")
    assert report.metrics["estimated_words"] > 0
    assert not report.evidence
    assert report.estimated


def test_a_rhyme_ending_the_dictionary_lacks_is_estimated() -> None:
    """`clerihew` reports no metric, only the rhyme evidence."""
    report = check("clerihew", DAVY)
    assert "estimated_words" not in report.metrics
    assert any(item.basis == "estimated" for item in report.evidence)
    assert report.estimated


#: A composite whose first entry estimates: `glorbix` is in no dictionary, so
#: `syllable_count` guesses it. No golden case composes an estimating row.
GLORBIX: dict[str, Any] = {
    "constraints": [
        {"id": "syllable_count", "params": {"pattern": [4]}},
        {"id": "lipogram", "params": {"forbidden": "z"}},
    ]
}


def _calls() -> Iterator[tuple[str, str, Lang, dict[str, Any]]]:
    """Every golden case, then each estimated one again inside a composite.

    The golden corpus alone cannot hold the rule for `multiple_constraint`: its
    determinacy turns on what a call composes, and no golden composite composes a row
    that estimates (final 0.4.0 review, finding 1).
    """
    estimated: list[tuple[str, str, Lang, dict[str, Any]]] = []
    for case in denckring.golden_cases():
        yield case.procedure, case.text, case.lang, case.params
        with contextlib.suppress(denckring.DenckringError):
            if check(case.procedure, case.text, lang=case.lang, **case.params).estimated:
                estimated.append((case.procedure, case.text, case.lang, case.params))
    yield "multiple_constraint", "the glorbix sang", "en", GLORBIX
    for procedure, text, lang, params in estimated:
        if procedure == "multiple_constraint":
            continue
        composed = [
            {"id": procedure, "params": params},
            {"id": "lipogram", "params": {"forbidden": "q"}},
        ]
        yield "multiple_constraint", text, lang, {"constraints": composed}


def test_an_exact_row_never_rests_on_an_estimate() -> None:
    """No exceptions since 0.4.0. Until then the two `definitional_*` rows read `exact`
    while a source word no gloss resolves (`the`, `went`) made their reports
    `estimated` (U3 review M3); `describe` now reads them `heuristic` (ADR 0054), and
    `multiple_constraint`, whose entries may estimate, too (ruling R-F5)."""
    for procedure, text, lang, params in _calls():
        if denckring.describe(procedure).reading.determinacy != "exact":
            continue
        try:
            report = check(procedure, text, lang=lang, **params)
        except denckring.DenckringError:
            continue
        assert not report.estimated, (procedure, text, params)


def test_a_composite_of_an_estimating_row_is_described_heuristic() -> None:
    """The case the golden corpus lacks: `syllable_count` guesses `glorbix`, so the
    composite reports `estimated`, and its description has to allow for that."""
    assert check("multiple_constraint", "the glorbix sang", **GLORBIX).estimated
    assert denckring.describe("multiple_constraint").reading.determinacy == "heuristic"


def test_a_row_whose_params_name_its_requires_is_heuristic() -> None:
    """The rule, not the id: every row marked `requires_from_params` reads `heuristic`,
    and every row that delegates its rules to its entries is so marked."""
    from denckring.core.registry import all_procedures

    marked = [pid for pid, p in all_procedures().items() if p.requires_from_params]
    assert marked
    for pid, procedure in all_procedures().items():
        if procedure.delegates_rules:
            assert procedure.requires_from_params, pid
    for pid in marked:
        assert denckring.describe(pid).reading.determinacy == "heuristic", pid


def test_a_word_no_gloss_resolves_is_estimated() -> None:
    report = check("definitional_expansion", "the cat", source="the cat")
    assert report.metrics["estimated_words"] > 0
    assert report.estimated


def test_a_dictionary_read_is_not_estimated() -> None:
    report = check("haiku", "the evening rain\nis falling softly now\nsplash silence again")
    assert report.evidence
    assert all(item.basis == "dictionary" for item in report.evidence)
    assert not report.estimated


def test_it_reaches_json_and_is_added_beside_the_fields_already_promised() -> None:
    """A non-Python caller reads it from the JSON; the promised fields are all still there.

    Asserts the rule ("added, nothing removed"), not today's set: the README permits
    the next added field too. `tests/test_provenance.py` ties the set to the version.
    """
    report = check("proteus_verse", VOSS, lang="de")
    dumped = report.model_dump(mode="json")
    assert dumped["estimated"] is True
    promised = {"procedure", "satisfied", "score", "violations", "metrics", "provenance"}
    assert promised <= set(Report.model_fields)
    assert promised | {"estimated"} <= dumped.keys()


def _estimated_golden(procedure: str) -> tuple[str, dict[str, Any], Lang]:
    for case in denckring.golden_cases():
        if case.procedure == procedure:
            report = check(procedure, case.text, lang=case.lang, **case.params)
            if report.estimated:
                return case.text, case.params, case.lang
    raise AssertionError(f"no estimated golden case for {procedure}")


@pytest.mark.parametrize("procedure", ["ballade", "clerihew", "proteus_verse"])
def test_a_composite_rests_on_its_constraints_estimates(procedure: str) -> None:
    """A composite verdict is only as firm as its softest constraint (U3 review I1).

    `proteus_verse` discloses its guesses only in the metric, so the composite has to
    carry that as well as the constraints' evidence. The verdict does not move, and the
    constraint's own score is the composite's first delegate score.
    """
    text, params, lang = _estimated_golden(procedure)
    alone = check(procedure, text, lang=lang, **params)
    composite = check(
        "multiple_constraint",
        text,
        lang=lang,
        constraints=[
            {"id": procedure, "params": params},
            {"id": "lipogram", "params": {"forbidden": "q"}},
        ],
    )
    assert composite.estimated
    assert composite.metrics["delegates.0.score"] == alone.score
    assert composite.satisfied == alone.satisfied
    assert composite.evidence == alone.evidence


def test_a_composite_of_exact_rows_reports_no_estimate() -> None:
    composite = check(
        "multiple_constraint",
        "the cat",
        constraints=[{"id": "lipogram", "params": {"forbidden": "q"}}, {"id": "univocalic"}],
    )
    assert not composite.estimated
    assert "estimated_words" not in composite.metrics
