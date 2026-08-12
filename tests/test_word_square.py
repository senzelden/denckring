import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

SQUARE = """heart
ember
abuse
resin
trend"""


def test_the_classic_square_is_satisfied() -> None:
    assert check("word_square", SQUARE).satisfied


def test_a_symmetric_grid_of_non_words_is_not_satisfied() -> None:
    """sator_square accepts this; word_square also asks whether the rows are words."""
    assert check("word_square", "sator\narepo\ntenet\nopera\nrotas").satisfied is False


def test_an_asymmetric_grid_is_not_satisfied() -> None:
    assert not check("word_square", "abc\ndef\nghi").satisfied


def test_empty_text_is_not_satisfied() -> None:
    assert not check("word_square", "").satisfied
