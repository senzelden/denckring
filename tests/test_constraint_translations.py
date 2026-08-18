"""What is checkable here is the constraint, not the translation."""

from denckring import check
from denckring.core.registry import get


def test_univocalic_translation_checks_the_vowel_in_the_result() -> None:
    report = check("univocalic_translation", "the letters were her tenders", source="x", vowel="e")
    assert report.satisfied is True


def test_univocalic_translation_rejects_a_second_vowel() -> None:
    report = check("univocalic_translation", "the cat sat", source="x", vowel="e")
    assert report.satisfied is False


def test_lipogrammatic_translation_checks_the_missing_letter() -> None:
    report = check("lipogrammatic_translation", "brown fox", source="x", forbidden="e")
    assert report.satisfied is True


def test_lipogrammatic_translation_rejects_the_forbidden_letter() -> None:
    report = check(
        "lipogrammatic_translation", "the letter appears here", source="x", forbidden="e"
    )
    assert report.satisfied is False


def test_reports_carry_their_own_procedure_id_not_the_delegates() -> None:
    uni = check("univocalic_translation", "the cat sat", source="x", vowel="e")
    lipo = check("lipogrammatic_translation", "the letter appears here", source="x", forbidden="e")
    assert uni.procedure == "univocalic_translation"
    assert lipo.procedure == "lipogrammatic_translation"


def test_violations_are_surfaced_from_the_delegate() -> None:
    report = check("univocalic_translation", "the cat sat", source="x", vowel="e")
    assert report.violations
    assert all(v.rule == "foreign_vowel" for v in report.violations)


def test_univocalic_publishes_the_metric_keys_we_depend_on() -> None:
    """`univocalic_translation` reads `metrics["vowel_count"]`/`["foreign"]` from the
    delegate instead of reconstructing counts from `score`. If `univocalic` ever
    renames those keys, this must fail loudly here rather than as a `KeyError`
    inside `univocalic_translation`'s `_check`."""
    report = get("univocalic").check("the cat sat", vowel="e")
    assert "vowel_count" in report.metrics
    assert "foreign" in report.metrics


def test_lipogram_publishes_the_metric_keys_we_depend_on() -> None:
    """Same guard as above, for `lipogrammatic_translation` and `lipogram`'s
    `metrics["letters"]`/`["hits"]`."""
    report = get("lipogram").check("the letter appears here", forbidden="e")
    assert "letters" in report.metrics
    assert "hits" in report.metrics


def test_univocalic_translation_score_matches_the_delegate_exactly() -> None:
    """The reconstruction used to round-trip through `score` inversion, which was
    only approximately lossless. Reading the delegate's own `metrics` counts
    directly should make the row's score identical to the delegate's, not merely
    close."""
    for text, vowel in [
        ("the cat sat", "e"),
        ("the letters were her tenders", "e"),
        ("a very awkward assertion", "a"),
        ("", "e"),
    ]:
        delegate = get("univocalic").check(text, vowel=vowel)
        row = check("univocalic_translation", text, source="x", vowel=vowel)
        assert row.score == delegate.score
        assert row.satisfied == delegate.satisfied


def test_lipogrammatic_translation_score_matches_the_delegate_exactly() -> None:
    for text, forbidden in [
        ("brown fox", "e"),
        ("the letter appears here", "e"),
        ("a quick sly fox", "q"),
        ("", "e"),
    ]:
        delegate = get("lipogram").check(text, forbidden=forbidden)
        row = check("lipogrammatic_translation", text, source="x", forbidden=forbidden)
        assert row.score == delegate.score
        assert row.satisfied == delegate.satisfied
