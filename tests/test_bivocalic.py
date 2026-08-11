from denckring import check


def test_two_vowels_are_satisfied() -> None:
    assert check("bivocalic", "a bad tea seat").satisfied


def test_three_vowels_are_not_satisfied() -> None:
    assert not check("bivocalic", "a bad tea sit").satisfied


def test_explicit_vowels_are_respected() -> None:
    assert check("bivocalic", "a bad tea", vowels="ae").satisfied
    assert not check("bivocalic", "a bad tea", vowels="io").satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("bivocalic", "").satisfied
