from denckring import check


def test_word_for_word_rearrangement_is_satisfied() -> None:
    assert check("transposal", "silent tar", source="listen rat").satisfied


def test_a_word_that_is_not_a_rearrangement_is_a_violation() -> None:
    report = check("transposal", "silent cat", source="listen rat")
    assert not report.satisfied
    assert report.violations[0].found == "cat"


def test_a_missing_word_is_reported() -> None:
    report = check("transposal", "silent", source="listen rat")
    assert any(v.rule == "missing_word" for v in report.violations)
