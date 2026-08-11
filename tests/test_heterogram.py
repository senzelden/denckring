from denckring import check


def test_text_with_no_repeated_letter_is_satisfied() -> None:
    assert check("heterogram", "Mr Jock, TV quiz PhD, bags few lynx").satisfied


def test_repeats_are_violations_with_offsets() -> None:
    report = check("heterogram", "abca")
    assert not report.satisfied
    assert report.violations[0].offset == 3


def test_word_scope_allows_repeats_across_words() -> None:
    assert check("heterogram", "cat dog", scope="word").satisfied
    assert not check("heterogram", "cat dot", scope="text").satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("heterogram", "").satisfied
