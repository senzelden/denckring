from denckring import check


def test_numerals_summing_to_the_year_are_satisfied() -> None:
    assert check("chronogram", "LVX", year=65).satisfied


def test_a_wrong_total_is_a_violation() -> None:
    report = check("chronogram", "LVX", year=100)
    assert not report.satisfied
    assert report.violations[0].found == "65"


def test_score_rises_as_the_total_approaches_the_year() -> None:
    near = check("chronogram", "LVX", year=70).score
    far = check("chronogram", "LVX", year=1000).score
    assert near > far


def test_text_without_numerals_scores_zero() -> None:
    assert check("chronogram", "ashen", year=50).score == 0.0
