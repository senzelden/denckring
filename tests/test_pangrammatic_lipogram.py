from denckring import check

WITHOUT_E = "Zqx jack ymbol quiz-graph, vwd fun; supply hot back."


def test_missing_letters_are_reported() -> None:
    report = check("pangrammatic_lipogram", "abc", forbidden="e")
    assert not report.satisfied
    assert any(v.rule == "missing_letter" for v in report.violations)


def test_the_forbidden_letter_appearing_is_a_violation() -> None:
    report = check("pangrammatic_lipogram", "the quick brown fox", forbidden="e")
    assert any(v.rule == "forbidden_letter" for v in report.violations)


def test_all_other_letters_present_and_the_forbidden_absent_is_satisfied() -> None:
    text = "".join(c for c in "abcdefghijklmnopqrstuvwxyz" if c != "e")
    assert check("pangrammatic_lipogram", text, forbidden="e").satisfied


def test_empty_text_is_not_satisfied() -> None:
    assert not check("pangrammatic_lipogram", "", forbidden="e").satisfied
