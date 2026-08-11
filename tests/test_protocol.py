import pytest
from pydantic import ValidationError

from denckring.core.protocol import Meta, Report, Violation


def test_report_rejects_out_of_range_score() -> None:
    with pytest.raises(ValidationError):
        Report(procedure="lipogram", satisfied=False, score=1.5)


def test_report_defaults_are_empty() -> None:
    report = Report(procedure="lipogram", satisfied=True, score=1.0)
    assert report.violations == []
    assert report.metrics == {}


def test_violation_offset_is_optional() -> None:
    assert Violation(rule="forbidden_letter", found="e", expected="").offset is None


def test_meta_round_trips_through_json() -> None:
    meta = Meta(
        id="lipogram",
        names={"en": "Lipogram"},
        definitions={"en": "A text omitting a chosen letter."},
        source="Georges Perec, La Disparition (1969)",
        kind="restrictive",
        languages=["en"],
        requires=["tokens"],
        deterministic=True,
        prompt_hints={"en": "Write without using the letter e."},
    )
    assert Meta.model_validate(meta.model_dump()) == meta
