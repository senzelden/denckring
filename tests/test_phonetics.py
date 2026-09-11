"""The phonetic distance the `paronomasia` band is measured in.

Every case here is a real pair from a pronouncing dictionary rather than an
invented phoneme string, because the property that matters is how the measure
behaves on the pairs a pun is actually made of.
"""

from __future__ import annotations

import pytest

from denckring.core.phonetics import (
    bare_phonemes,
    cannot_be_within,
    distance_prepared,
    fold_equivalents,
    phoneme_distance,
    prepared,
    symbol_counts,
)


def test_a_word_is_no_distance_from_itself() -> None:
    assert phoneme_distance(["B", "R", "EH", "D"], ["B", "R", "EH", "D"]) == 0.0


def test_two_empty_sequences_are_no_distance_apart() -> None:
    """Not a division by zero, and not 1.0 either: nothing differs."""
    assert phoneme_distance([], []) == 0.0


def test_a_sequence_is_wholly_distant_from_nothing() -> None:
    assert phoneme_distance(["B", "R", "EH", "D"], []) == 1.0


def test_disjoint_sequences_of_equal_length_are_wholly_distant() -> None:
    assert phoneme_distance(["B"], ["K"]) == 1.0


def test_one_substitution_in_four_is_a_quarter() -> None:
    """`bread` against `brad` — the pun in *Bread Pitt*, one vowel apart."""
    assert phoneme_distance(["B", "R", "EH", "D"], ["B", "R", "AE", "D"]) == 0.25


def test_one_insertion_is_measured_against_the_longer_sequence() -> None:
    """Normalising by the longer side keeps the result inside [0, 1]."""
    assert phoneme_distance(["HH", "EH", "R"], ["HH", "EH", "R", "IY"]) == 0.25


def test_the_measure_is_symmetric() -> None:
    a, b = ["HH", "EH", "R"], ["EH", "R", "IY"]
    assert phoneme_distance(a, b) == phoneme_distance(b, a)


def test_the_measure_stays_inside_the_unit_interval() -> None:
    pairs: tuple[tuple[list[str], list[str]], ...] = (
        (["B", "R", "EH", "D"], ["P", "IH", "T"]),
        ([], ["AH"]),
        (["AH"], ["AH", "AH", "AH", "AH", "AH"]),
    )
    for a, b in pairs:
        assert 0.0 <= phoneme_distance(a, b) <= 1.0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (["B", "R", "EH1", "D"], ["B", "R", "EH", "D"]),
        (["AH0", "B", "AW1", "T"], ["AH", "B", "AW", "T"]),
        (["h", "aː", "ɐ̯"], ["h", "aː", "ɐ̯"]),
    ],
)
def test_arpabet_stress_digits_are_stripped_and_ipa_is_left_alone(
    raw: list[str], expected: list[str]
) -> None:
    """CMUdict marks stress on the vowel; IPA marks it as a separate symbol.

    Stripping a trailing digit touches only the first, which is the whole point:
    the German and French packs hand back IPA that carries no digits at all.
    """
    assert bare_phonemes(raw) == expected


def test_stress_alone_is_no_distance() -> None:
    """`the` unstressed against `the` stressed is one word, not a pun on itself."""
    assert phoneme_distance(["DH", "AH0"], ["DH", "AH1"]) == 0.0


def test_the_prefilter_only_ever_says_certainly_not() -> None:
    """The one property `cannot_be_within` must have: it may never exclude a pair
    the measure would have accepted.

    Checked exhaustively against the measure over short random sequences rather
    than on examples, because the prefilter it replaced looked right on examples
    and was wrong in general — German `Glas` and `klar` share neither first nor
    last phoneme and sit at exactly 0.500, so the old edge test hid a sign that
    was inside the band.
    """
    import random

    rng = random.Random(11)
    alphabet = "abcde"
    for _ in range(3000):
        a = [rng.choice(alphabet) for _ in range(rng.randint(0, 5))]
        b = [rng.choice(alphabet) for _ in range(rng.randint(0, 5))]
        for ceiling in (0.0, 0.25, 0.5, 0.75, 1.0):
            if cannot_be_within(a, b, ceiling, symbol_counts(a), symbol_counts(b)):
                assert phoneme_distance(a, b) > ceiling, (
                    f"{a} vs {b} was excluded at {ceiling} but is {phoneme_distance(a, b)} away"
                )


def test_the_prefilter_actually_excludes_something() -> None:
    """A filter that never fires is not a filter, and would pass the soundness
    property above vacuously."""
    a, b = ["B", "R", "EH", "D"], ["S", "IY"]
    assert cannot_be_within(a, b, 0.25, symbol_counts(a), symbol_counts(b))


def test_the_cheap_length_bound_works_without_counts() -> None:
    assert cannot_be_within(["A"], ["A", "B", "C", "D"], 0.5)
    assert not cannot_be_within(["A"], ["B"], 0.5)


def test_german_folds_its_vocalised_r_and_nothing_else() -> None:
    """`Haar` is `h aː ɐ̯` and `Harmonie` opens `h a ʁ`: the same segment."""
    assert fold_equivalents(["h", "aː", "ɐ̯"], "de") == fold_equivalents(["h", "aː", "ʁ"], "de")
    # Vowel length is contrastive — Staat against Stadt — and stays.
    assert fold_equivalents(["aː"], "de") != fold_equivalents(["a"], "de")
    # No table for English or French, so nothing moves.
    assert fold_equivalents(["ɐ̯"], "en") == ["ɐ̯"]
    assert fold_equivalents(["ɐ̯"], None) == ["ɐ̯"]


def test_a_prepared_comparison_agrees_with_the_normalising_one() -> None:
    a, b = ["h", "aː", "ɐ̯"], ["h", "a", "ʁ"]
    assert distance_prepared(prepared(a, "de"), prepared(b, "de")) == phoneme_distance(a, b, "de")


def test_a_ceiling_never_changes_a_verdict_inside_the_band() -> None:
    """The early exit may report a larger number for a pair that has already
    lost; it must never move one that has not."""
    import random

    rng = random.Random(5)
    for _ in range(2000):
        a = [rng.choice("abcd") for _ in range(rng.randint(1, 5))]
        b = [rng.choice("abcd") for _ in range(rng.randint(1, 5))]
        true = phoneme_distance(a, b)
        for ceiling in (0.25, 0.5, 0.75):
            capped = phoneme_distance(a, b, ceiling=ceiling)
            if true <= ceiling:
                assert capped == true
            else:
                assert capped > ceiling
