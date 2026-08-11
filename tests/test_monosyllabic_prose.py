from denckring import check


def test_one_syllable_words_are_satisfied() -> None:
    assert check("monosyllabic_prose", "the cat sat on the mat").satisfied


def test_a_longer_word_is_a_violation() -> None:
    report = check("monosyllabic_prose", "the water sat")
    assert not report.satisfied
    assert report.violations[0].found == "water"


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("monosyllabic_prose", "").satisfied
