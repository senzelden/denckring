from denckring import check


def test_words_in_alphabetical_order_are_satisfied() -> None:
    assert check("alphabetical_sentence", "all bad cats dance eagerly").satisfied


def test_an_out_of_order_word_is_a_violation() -> None:
    report = check("alphabetical_sentence", "all cats bad")
    assert not report.satisfied
    assert report.violations[0].found == "bad"


def test_equal_words_do_not_break_the_order() -> None:
    assert check("alphabetical_sentence", "all all bad").satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("alphabetical_sentence", "").satisfied
