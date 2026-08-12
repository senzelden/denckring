import pytest

from denckring import check

pytest.importorskip("denckring_en_data")


def test_a_word_dividing_into_words_is_satisfied() -> None:
    assert check("charade", "carpet").satisfied


def test_an_indivisible_word_is_a_violation() -> None:
    report = check("charade", "zzzq")
    assert not report.satisfied
    assert report.violations[0].rule == "does_not_divide"


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("charade", "").satisfied
