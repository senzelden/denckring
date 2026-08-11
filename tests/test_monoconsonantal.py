from denckring import check


def test_one_consonant_is_satisfied() -> None:
    assert check("monoconsonantal", "no one anon").satisfied


def test_two_consonants_are_not_satisfied() -> None:
    assert not check("monoconsonantal", "no one atom").satisfied


def test_explicit_consonant_is_respected() -> None:
    assert check("monoconsonantal", "no one", consonant="n").satisfied
    assert not check("monoconsonantal", "no one", consonant="t").satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("monoconsonantal", "").satisfied
