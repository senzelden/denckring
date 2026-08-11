from denckring import check

SATOR = "sator\narepo\ntenet\nopera\nrotas"


def test_the_pompeii_square_is_satisfied() -> None:
    assert check("sator_square", SATOR).satisfied


def test_a_broken_square_is_not_satisfied() -> None:
    assert not check("sator_square", "sator\narepo\ntenet\nopera\nrotax").satisfied


def test_a_ragged_grid_reports_row_length() -> None:
    report = check("sator_square", "abc\nde")
    assert not report.satisfied
    assert any(v.rule == "wrong_row_length" for v in report.violations)


def test_empty_text_is_not_satisfied() -> None:
    assert not check("sator_square", "").satisfied
