import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_text_without_the_letter_is_satisfied() -> None:
    report = check("lipogram", "This is a small conforming bit of writing.", forbidden="z")
    assert report.satisfied
    assert report.score == 1.0
    assert report.violations == []


def test_default_forbidden_letter_is_e() -> None:
    assert not check("lipogram", "Here is an example.").satisfied


def test_violations_carry_offsets() -> None:
    report = check("lipogram", "abc e", forbidden="e")
    assert [v.offset for v in report.violations] == [4]
    assert report.violations[0].rule == "forbidden_letter"


def test_accented_forms_count_as_the_bare_letter() -> None:
    assert not check("lipogram", "café", forbidden="e").satisfied


def test_score_falls_as_violations_rise() -> None:
    few = check("lipogram", "aaaaaaaaae", forbidden="e").score
    many = check("lipogram", "aaaaaeeeee", forbidden="e").score
    assert few > many


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("lipogram", "").satisfied


def test_bad_parameter_raises_invalid_params() -> None:
    with pytest.raises(InvalidParams):
        check("lipogram", "text", forbidden="ee")
