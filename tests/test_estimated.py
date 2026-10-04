"""`Report.estimated`: whether a verdict rests on anything estimated (audit B8).

denckring-bench leaves a verdict unscored when it rests on a guess, and read
`metrics["estimated_words"]` to decide, a key outside the stability promise. The
metric and `evidence` each record cases the other misses, so the signal has to read
both; these tests hold it to one case of each kind, and to the rule that a row whose
reading is exact never reports one.
"""

from __future__ import annotations

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


def test_an_exact_row_never_rests_on_an_estimate() -> None:
    """No exceptions since 0.4.0. Until then the two `definitional_*` rows read `exact`
    while a source word no gloss resolves (`the`, `went`) made their reports
    `estimated` (U3 review M3); `describe` now reads them `heuristic` (ADR 0054)."""
    for case in denckring.golden_cases():
        if denckring.describe(case.procedure).reading.determinacy != "exact":
            continue
        try:
            report = check(case.procedure, case.text, lang=case.lang, **case.params)
        except denckring.DenckringError:
            continue
        assert not report.estimated, (case.procedure, case.name)


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
    carry that as well as the constraints' evidence. The verdict and score do not move.
    """
    text, params, lang = _estimated_golden(procedure)
    alone = check(procedure, text, lang=lang, **params)
    composite = check(
        "multiple_constraint",
        text,
        lang=lang,
        constraints=[procedure, "lipogram"],
        constraint_params={procedure: params, "lipogram": {"forbidden": "q"}},
    )
    assert composite.estimated
    assert composite.metrics[f"{procedure}_score"] == alone.score
    assert composite.satisfied == alone.satisfied
    assert composite.evidence == alone.evidence


def test_a_composite_of_exact_rows_reports_no_estimate() -> None:
    composite = check(
        "multiple_constraint",
        "the cat",
        constraints=["lipogram", "univocalic"],
        constraint_params={"lipogram": {"forbidden": "q"}},
    )
    assert not composite.estimated
    assert "estimated_words" not in composite.metrics
