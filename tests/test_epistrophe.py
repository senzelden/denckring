from denckring import check


def test_shared_closing_is_satisfied() -> None:
    assert check("epistrophe", "we go home\nthey go home").satisfied


def test_a_different_closing_is_a_violation() -> None:
    report = check("epistrophe", "we go home\nthey go away")
    assert not report.satisfied
    assert report.violations[0].found == "away"


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("epistrophe", "").satisfied
