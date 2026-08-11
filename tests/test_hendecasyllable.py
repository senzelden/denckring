from denckring import check


def test_eleven_syllable_lines_are_satisfied() -> None:
    line = "the cat sat on the mat and thought of the mice"  # eleven
    assert check("hendecasyllable", line + "\n" + line).satisfied


def test_a_short_line_is_a_violation() -> None:
    assert not check("hendecasyllable", "the cat sat").satisfied
