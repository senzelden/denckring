from denckring import check


def test_final_letters_spell_the_target() -> None:
    assert check("telestich", "beta\nzero\nomen", target="aon").satisfied


def test_wrong_final_letter_is_a_violation() -> None:
    assert not check("telestich", "beta\nzero", target="ab").satisfied
