from denckring import check


def test_classic_pangram_is_satisfied() -> None:
    assert check("pangram", "The quick brown fox jumps over the lazy dog.").satisfied


def test_missing_letters_are_reported_and_scored() -> None:
    report = check("pangram", "abc")
    assert not report.satisfied
    assert report.score == 3 / 26
    assert {v.expected for v in report.violations} >= {"z"}


def test_perfect_pangram_requires_each_letter_exactly_once() -> None:
    perfect = "Mr Jock, TV quiz PhD, bags few lynx"
    assert check("pangram", perfect, perfect=True).satisfied
    ordinary = "The quick brown fox jumps over the lazy dog."
    assert not check("pangram", ordinary, perfect=True).satisfied


def test_empty_text_scores_zero() -> None:
    report = check("pangram", "")
    assert not report.satisfied
    assert report.score == 0.0
