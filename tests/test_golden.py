"""Level 1: every golden example must check exactly as recorded."""

from conftest import GOLDEN_DIR, GoldenCase, load_golden_cases
from denckring import check


def test_golden_case(golden_case: GoldenCase) -> None:
    report = check(
        golden_case.procedure, golden_case.text, lang=golden_case.lang, **golden_case.params
    )
    assert report.satisfied is golden_case.satisfied
    if golden_case.min_score is not None:
        assert report.score >= golden_case.min_score
    if golden_case.max_score is not None:
        assert report.score <= golden_case.max_score


def test_every_registered_procedure_has_a_golden_file(procedure_id: str) -> None:
    assert (GOLDEN_DIR / f"{procedure_id}.yaml").exists()


def test_every_procedure_has_a_positive_and_a_negative_case(procedure_id: str) -> None:
    cases = [c for c in load_golden_cases() if c.procedure == procedure_id]
    assert any(c.satisfied for c in cases)
    assert any(not c.satisfied for c in cases)
