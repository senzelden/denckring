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


def test_a_changed_vowel_beside_its_twin_aligns_as_a_gap_pair() -> None:
    """The cost ADR 0056 admits. `SequenceMatcher` takes the longest matching
    block first, not the fewest edits: e-o-a against e-a-a keeps `e` and the
    last `a`, so the `o` is an insertion and one `a` a deletion. Two units, not
    one, so this text scores 0.5 where index by index it scored 0.667."""
    report = check("homovocalism", "the cot sat", source=SOURCE)
    assert report.satisfied is False
    assert [v.rule for v in report.violations] == ["extra_letters", "missing_letter"]
    assert report.score == 0.5
