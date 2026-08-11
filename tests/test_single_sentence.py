from denckring import check


def test_one_sentence_is_satisfied() -> None:
    assert check("single_sentence", "One long clause and then an end.").satisfied


def test_two_sentences_are_a_violation() -> None:
    report = check("single_sentence", "One. Two.")
    assert not report.satisfied
    assert report.violations[0].rule == "interior_terminator"


def test_no_terminator_at_all_is_satisfied() -> None:
    assert check("single_sentence", "a clause running on").satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("single_sentence", "").satisfied
