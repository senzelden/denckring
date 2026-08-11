from denckring import check

ALPHABET_LINES = "\n".join(f"{c}bc line" for c in "abcdefghijklmnopqrstuvwxyz")


def test_full_alphabet_of_lines_is_satisfied() -> None:
    assert check("abecedarian", ALPHABET_LINES).satisfied


def test_a_broken_run_is_not_satisfied() -> None:
    assert not check("abecedarian", "apple\ncherry\nbanana").satisfied


def test_a_partial_run_from_a_start_letter_is_satisfied() -> None:
    assert check("abecedarian", "apple\nberry\ncherry", start="a").satisfied


def test_word_unit_uses_word_initials() -> None:
    assert check("abecedarian", "apple berry cherry", unit="word").satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("abecedarian", "").satisfied
