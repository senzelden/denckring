from denckring import check


def test_text_avoiding_the_word_is_satisfied() -> None:
    assert check("liponym", "a cat sat", forbidden="dog").satisfied


def test_using_the_word_is_a_violation() -> None:
    report = check("liponym", "a dog sat", forbidden="dog")
    assert not report.satisfied
    assert report.violations[0].found == "dog"


def test_matching_ignores_case() -> None:
    assert not check("liponym", "A Dog sat", forbidden="dog").satisfied


def test_a_substring_is_not_a_match() -> None:
    assert check("liponym", "dogma sat", forbidden="dog").satisfied
