from denckring import check


def test_single_vowel_text_is_satisfied() -> None:
    assert check("univocalic", "Persever, ye perfect men, ever keep these precepts ten").satisfied


def test_mixed_vowels_are_not_satisfied() -> None:
    assert not check("univocalic", "the cat sat").satisfied


def test_explicit_vowel_parameter_is_respected() -> None:
    assert check("univocalic", "a lad", vowel="a").satisfied
    assert not check("univocalic", "a lad", vowel="o").satisfied


def test_vowel_is_inferred_from_the_majority_when_unset() -> None:
    report = check("univocalic", "peer deed")
    assert report.satisfied
    assert report.metrics["vowel_count"] == 4.0


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("univocalic", "").satisfied
