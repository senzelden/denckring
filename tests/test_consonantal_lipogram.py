from denckring import check


def test_text_avoiding_the_set_is_satisfied() -> None:
    assert check("consonantal_lipogram", "a real one", forbidden="bcd").satisfied


def test_one_forbidden_consonant_is_a_violation() -> None:
    report = check("consonantal_lipogram", "a bad one", forbidden="bcd")
    assert not report.satisfied
    assert {v.found for v in report.violations} == {"b", "d"}


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("consonantal_lipogram", "", forbidden="bcd").satisfied
