from denckring import check


def test_sentences_of_the_target_length_are_satisfied() -> None:
    assert check("sentence_length_constraint", "one two three. four five six.", words=3).satisfied


def test_a_long_sentence_is_a_violation() -> None:
    report = check("sentence_length_constraint", "one two three. four five six seven.", words=3)
    assert not report.satisfied
    assert report.violations[0].found == "4 words"


def test_tolerance_widens_the_bound() -> None:
    text = "one two three. four five six seven."
    assert check("sentence_length_constraint", text, words=3, tolerance=1).satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("sentence_length_constraint", "", words=3).satisfied
