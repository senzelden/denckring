from denckring import check


def test_growing_sentences_are_satisfied() -> None:
    assert check("snowball_sentence", "Go. We go. We can go.").satisfied


def test_a_wrong_length_sentence_is_a_violation() -> None:
    report = check("snowball_sentence", "Go. We can go. We go.")
    assert not report.satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("snowball_sentence", "").satisfied
