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
    report = check("homovocalism", "the cat sit", source=SOURCE)
    assert report.satisfied is False
    assert [(v.rule, v.found, v.expected) for v in report.violations] == [("wrong_vowel", "i", "a")]


def test_a_changed_vowel_beside_its_twin_is_one_substitution() -> None:
    """Ruling R-U8b. e-o-a against e-a-a is one substituted vowel, and scores
    2/3, as index by index did. `SequenceMatcher`, which keeps the longest
    matching block first, read it as an inserted `o` and a deleted `a` and
    scored 0.5: the alignment has to be the fewest edits (ADR 0056)."""
    report = check("homovocalism", "the cot sat", source=SOURCE)
    assert report.satisfied is False
    assert [(v.rule, v.found, v.expected) for v in report.violations] == [("wrong_vowel", "o", "a")]
    assert report.score == 2 / 3
