from denckring import check


def test_shared_final_letter_is_satisfied() -> None:
    assert check("homoteleuton", "many funny sunny").satisfied


def test_a_different_ending_is_a_violation() -> None:
    report = check("homoteleuton", "many funny cat")
    assert not report.satisfied
    assert report.violations[0].found == "cat"


def test_final_is_inferred_from_the_first_word() -> None:
    assert check("homoteleuton", "cats dogs bats").satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("homoteleuton", "").satisfied
