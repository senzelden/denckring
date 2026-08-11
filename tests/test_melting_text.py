from denckring import check


def test_a_subsequence_of_the_source_is_satisfied() -> None:
    assert check("melting_text", "a c", source="a b c").satisfied


def test_reordering_is_a_violation() -> None:
    assert not check("melting_text", "c a", source="a b c").satisfied


def test_an_invented_word_is_a_violation() -> None:
    report = check("melting_text", "a z", source="a b c")
    assert report.violations[0].found == "z"
