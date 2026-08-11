from denckring import check

BASHO = """an old silent pond
a frog jumps into the pond
splash silence again"""


def test_a_five_seven_five_poem_is_satisfied() -> None:
    assert check("haiku", BASHO).satisfied


def test_a_wrong_line_is_a_violation() -> None:
    report = check("haiku", "an old silent pond\na frog jumps in\nsplash silence again")
    assert not report.satisfied
    assert report.violations[0].expected == "7 syllables"


def test_the_report_says_how_many_words_were_estimated() -> None:
    assert check("haiku", BASHO).metrics["estimated_words"] == 0.0


def test_a_missing_line_is_a_violation() -> None:
    report = check("haiku", "an old silent pond")
    assert any(v.rule == "missing_line" for v in report.violations)
