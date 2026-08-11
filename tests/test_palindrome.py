from denckring import check


def test_classic_palindrome_is_satisfied() -> None:
    assert check("palindrome", "A man, a plan, a canal: Panama").satisfied


def test_non_palindrome_is_not_satisfied() -> None:
    assert not check("palindrome", "not a palindrome at all").satisfied


def test_word_unit_compares_whole_words() -> None:
    assert not check("palindrome", "you can cage a swallow", unit="word").satisfied
    assert check("palindrome", "bird sings bird", unit="word").satisfied


def test_score_reflects_how_close_the_text_is() -> None:
    assert 0.0 < check("palindrome", "abcdba").score < 1.0


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("palindrome", "").satisfied
