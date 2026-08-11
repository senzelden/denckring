import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_text_within_the_name_letters_is_satisfied() -> None:
    assert check("beau_present", "a rare cameo", name="Marcel Camoe").satisfied


def test_a_foreign_letter_is_a_violation() -> None:
    report = check("beau_present", "a zebra", name="Marcel")
    assert not report.satisfied
    assert {v.found for v in report.violations} == {"z", "b"}


def test_require_all_demands_every_name_letter_be_used() -> None:
    assert check("beau_present", "arc", name="arc").satisfied
    assert not check("beau_present", "arc", name="arch", require_all=True).satisfied


def test_missing_name_is_an_invalid_params_error() -> None:
    with pytest.raises(InvalidParams):
        check("beau_present", "text")
