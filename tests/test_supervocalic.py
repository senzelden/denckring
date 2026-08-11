from denckring import check


def test_each_vowel_exactly_once_is_satisfied() -> None:
    # "facetious" is the canonical example: a, e, i, o, u each once, in order.
    assert check("supervocalic", "facetious").satisfied
    assert check("supervocalic", "ab ec id of ug").satisfied


def test_a_repeated_vowel_is_a_violation() -> None:
    assert not check("supervocalic", "ab ec id of uga").satisfied


def test_a_missing_vowel_is_a_violation() -> None:
    report = check("supervocalic", "ab ec id of")
    assert not report.satisfied
    assert any(v.expected == "u" for v in report.violations)


def test_empty_text_is_not_satisfied() -> None:
    assert not check("supervocalic", "").satisfied
