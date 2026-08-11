import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_text_drawn_from_the_bank_is_satisfied() -> None:
    assert check("letter_bank", "meander named", bank="meander").satisfied


def test_a_letter_outside_the_bank_is_a_violation() -> None:
    report = check("letter_bank", "meander zoo", bank="meander")
    assert not report.satisfied
    assert "z" in {v.found for v in report.violations}


def test_every_bank_letter_must_be_used() -> None:
    report = check("letter_bank", "mad", bank="meander")
    assert not report.satisfied
    assert any(v.rule == "unused_bank_letter" for v in report.violations)


def test_missing_bank_is_an_invalid_params_error() -> None:
    with pytest.raises(InvalidParams):
        check("letter_bank", "text")
