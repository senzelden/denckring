from denckring import check


def test_twelve_syllable_lines_are_satisfied() -> None:
    line = "the cat sat on the mat and thought of the wild mice"  # twelve
    assert check("alexandrine", line).satisfied


def test_a_short_line_is_a_violation() -> None:
    assert not check("alexandrine", "the cat sat").satisfied
