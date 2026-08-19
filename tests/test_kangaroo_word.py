"""The synonym is the caller's claim; the letters are the program's business."""

from denckring import check


def test_a_hidden_synonym_in_order_is_accepted() -> None:
    """encourage hides u-r-g-e, scattered but ordered."""
    assert check("kangaroo_word", "encourage", synonym="urge").satisfied is True


def test_letters_out_of_order_are_rejected() -> None:
    report = check("kangaroo_word", "encourage", synonym="rug")
    assert report.satisfied is False
    violation = next(v for v in report.violations if v.rule == "synonym_not_in_order")
    assert violation.found == "rug"


def test_a_synonym_the_lexicon_does_not_know_is_rejected() -> None:
    report = check("kangaroo_word", "encourage", synonym="urg")
    assert report.satisfied is False
    assert any(v.rule == "not_a_word" for v in report.violations)


def test_the_word_may_not_be_its_own_synonym() -> None:
    """Every word trivially contains itself; that is not a kangaroo word."""
    assert check("kangaroo_word", "encourage", synonym="encourage").satisfied is False


def test_fold_diacritics_changes_the_verdict() -> None:
    """cafés folds to cafes, which hides cafe in order; unfolded, the accented
    e is not the plain e the synonym needs at that position."""
    folded = check("kangaroo_word", "cafés", synonym="cafe", fold_diacritics=True)
    assert folded.satisfied is True

    unfolded = check("kangaroo_word", "cafés", synonym="cafe", fold_diacritics=False)
    assert unfolded.satisfied is False
    violation = next(v for v in unfolded.violations if v.rule == "synonym_not_in_order")
    assert violation.found == "cafe"
