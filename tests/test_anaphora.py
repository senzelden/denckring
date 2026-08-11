from denckring import check


def test_shared_opening_is_satisfied() -> None:
    assert check("anaphora", "I came\nI saw\nI won").satisfied


def test_a_different_opening_is_a_violation() -> None:
    report = check("anaphora", "I came\nWe saw")
    assert not report.satisfied
    assert report.violations[0].found == "we"


def test_opening_can_be_forced() -> None:
    assert not check("anaphora", "I came\nI saw", opening="we").satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("anaphora", "").satisfied
