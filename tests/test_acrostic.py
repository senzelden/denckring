import pytest

from denckring import check
from denckring.core.errors import InvalidParams

CARROLL = """A boat beneath a sunny sky
Lingering onward dreamily
In an evening of July
Children three that nestle near
Eager eye and willing ear"""


def test_carroll_acrostic_is_satisfied() -> None:
    assert check("acrostic", CARROLL, target="ALICE").satisfied


def test_wrong_initial_is_a_violation() -> None:
    report = check("acrostic", "Apple\nZebra", target="AB")
    assert not report.satisfied
    assert report.violations[0].found == "z"
    assert report.violations[0].expected == "b"


def test_too_few_lines_is_a_violation() -> None:
    report = check("acrostic", "Apple", target="AB")
    assert not report.satisfied
    assert any(v.rule == "missing_unit" for v in report.violations)


def test_extra_lines_are_a_violation() -> None:
    report = check("acrostic", "Apple\nBerry\nCherry", target="AB")
    assert not report.satisfied
    assert any(v.rule == "extra_unit" for v in report.violations)


def test_word_unit_uses_word_initials() -> None:
    assert check("acrostic", "alpha bravo", target="ab", unit="word").satisfied


def test_missing_target_is_an_invalid_params_error() -> None:
    with pytest.raises(InvalidParams):
        check("acrostic", "text")
