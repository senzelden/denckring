from denckring import check


def test_reordered_sentences_are_satisfied() -> None:
    assert check("recombination", "B. A.", source="A. B.").satisfied


def test_a_dropped_sentence_is_a_violation() -> None:
    report = check("recombination", "A.", source="A. B.")
    assert not report.satisfied
    assert any(v.rule == "sentence_dropped" for v in report.violations)


def test_an_invented_sentence_is_a_violation() -> None:
    report = check("recombination", "A. B. C.", source="A. B.")
    assert any(v.rule == "sentence_not_in_source" for v in report.violations)
