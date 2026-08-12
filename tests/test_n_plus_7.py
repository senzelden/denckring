import pytest

from denckring import check

pytest.importorskip("denckring_en_data")

SOURCE = "the cat sat on the table"
DISPLACED = "the catafalque satchmo on the tablespoonful"


def test_a_correct_displacement_is_satisfied() -> None:
    assert check("n_plus_7", DISPLACED, source=SOURCE).satisfied


def test_leaving_a_noun_alone_is_readable_as_another_part_of_speech() -> None:
    """A word list cannot rule it out, so it is tolerated and counted."""
    report = check("n_plus_7", SOURCE, source=SOURCE)
    assert report.satisfied
    assert report.metrics["ambiguous_words"] > 0


def test_changing_a_non_noun_is_a_violation() -> None:
    report = check("n_plus_7", "a cat sat on the table", source=SOURCE)
    assert not report.satisfied
    assert report.violations[0].rule == "changed_a_non_noun"


def test_a_wrong_displacement_is_a_violation() -> None:
    wrong = DISPLACED.replace("catafalque", "zebra")
    assert not check("n_plus_7", wrong, source=SOURCE).satisfied


def test_a_different_word_count_is_a_violation() -> None:
    report = check("n_plus_7", "too short", source=SOURCE)
    assert report.violations[0].rule == "wrong_word_count"
