from denckring import check


def test_lines_matching_the_pattern_are_satisfied() -> None:
    assert check("syllable_count", "the cat sat\nthe dog", pattern=[3, 2]).satisfied


def test_a_wrong_line_is_a_violation() -> None:
    assert not check("syllable_count", "the cat sat\nthe dog ran fast", pattern=[3, 2]).satisfied


def test_an_extra_line_is_a_violation() -> None:
    report = check("syllable_count", "the cat sat\nthe dog\nmore", pattern=[3, 2])
    assert any(v.rule == "extra_line" for v in report.violations)
