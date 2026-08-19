"""One skeleton kept, the other class replaced. Two rows, one function."""

from denckring import check

SOURCE = "the cat sat"


def test_homoconsonantism_keeps_the_consonant_skeleton() -> None:
    """t-h-c-t-s-t preserved in order, every vowel free to change."""
    report = check("homoconsonantism", "the coat is out", source=SOURCE)
    assert report.satisfied is True


def test_homoconsonantism_rejects_a_changed_consonant() -> None:
    report = check("homoconsonantism", "the bat sat", source=SOURCE)
    assert report.satisfied is False
    violation = next(v for v in report.violations if v.rule == "wrong_consonant")
    assert violation.expected == "c"


def test_homovocalism_keeps_the_vowels() -> None:
    """e-a-a preserved in order, every consonant free to change."""
    report = check("homovocalism", "he ran back", source="the cat sat")
    assert report.satisfied is True


def test_homovocalism_rejects_a_changed_vowel() -> None:
    report = check("homovocalism", "the cot sat", source=SOURCE)
    assert report.satisfied is False
    assert any(v.rule == "wrong_vowel" for v in report.violations)
