import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_both_margins_spelling_their_targets_is_satisfied() -> None:
    assert check("double_acrostic", "Apple\nBerry", first="ab", last="ey").satisfied


def test_a_wrong_final_letter_is_a_violation() -> None:
    report = check("double_acrostic", "Apple\nBerra", first="ab", last="ey")
    assert not report.satisfied
    assert any(v.rule == "wrong_final" for v in report.violations)


def test_a_missing_line_is_a_violation() -> None:
    report = check("double_acrostic", "Apple", first="ab", last="ey")
    assert any(v.rule == "missing_line" for v in report.violations)


def test_missing_targets_are_an_invalid_params_error() -> None:
    with pytest.raises(InvalidParams):
        check("double_acrostic", "Apple")
