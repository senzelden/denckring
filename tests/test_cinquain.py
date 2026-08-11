from denckring import check

CINQUAIN = """the cat
sat on the mat
the dog ran past the cat
the cat sat on the mat and thought
of mice"""

WRONG_SECOND_LINE = """the cat
sat
the dog ran past the cat
the cat sat on the mat and thought
of mice"""


def test_the_crapsey_measure_is_satisfied() -> None:
    report = check("cinquain", CINQUAIN)
    assert report.satisfied, [v.found for v in report.violations]


def test_a_wrong_line_is_not_satisfied() -> None:
    assert not check("cinquain", WRONG_SECOND_LINE).satisfied
