"""What is checkable here is the constraint, not the translation."""

from denckring import check


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
