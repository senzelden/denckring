from denckring import check


def test_doubled_words_are_satisfied() -> None:
    assert check("tautonym", "couscous tartar").satisfied


def test_an_ordinary_word_is_a_violation() -> None:
    report = check("tautonym", "couscous cat")
    assert not report.satisfied
    assert report.violations[0].found == "cat"


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("tautonym", "").satisfied
