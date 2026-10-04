"""Two form rows that constrain sound inside the line rather than across lines."""

import os
import subprocess
import sys

from denckring import check

ALLITERATIVE = """in a summer season when soft was the sun
i shaped me in shrouds as a shepherd were
bright was the bank where the birds were bold
in a wide wild wood i wandered west"""


def test_alliterative_verse_accepts_three_in_four() -> None:
    assert check("alliterative_verse", ALLITERATIVE, minimum=3).satisfied is True


def test_alliterative_verse_names_the_line_that_fails() -> None:
    broken = ALLITERATIVE.replace(
        "in a wide wild wood i wandered west", "the quiet evening came down slowly"
    )
    report = check("alliterative_verse", broken, minimum=3)
    assert report.satisfied is False
    assert any(v.rule == "too_few_alliterating" for v in report.violations)


def test_assonance_repeats_a_vowel_across_the_line() -> None:
    report = check("assonance_constraint", "the rain in spain stays mainly plain")
    assert report.satisfied is True


def test_assonance_rejects_a_line_with_no_repeated_vowel() -> None:
    # "the dog runs" was the brief's sample, but "the" (AH0) and "runs" (AH1)
    # share a vowel once the stress digit is stripped, so it satisfies instead
    # of violating. "cat dog jumps" carries three distinct vowels (AE, AO, AH)
    # with none repeated.
    report = check("assonance_constraint", "cat dog jumps")
    assert report.satisfied is False


def test_assonance_skips_a_word_missing_from_the_pronouncing_dictionary() -> None:
    """R14: a word absent from CMU must not abort the scan.

    `flurbish` is not a real English word, so `pack.phonemes` raises
    `MissingCapability` for it. The row must catch that locally, skip the word,
    and still produce a report rather than propagating the exception — counting
    the skip in `estimated_words`, the same contract `metre_violations` follows.
    """
    report = check("assonance_constraint", "the rain in spain flurbish mainly plain")
    assert report.metrics["estimated_words"] >= 1


# Two lines whose words each carry more than one vowel, so every vowel ties at one
# word: a tie-break in set order named a different vowel under each hash seed.
_TIED = "Sommer Blume\nweiter"
_REPORT = (
    "from denckring import check; "
    f"print(check('assonance_constraint', {_TIED!r}, lang='de').model_dump_json())"
)


def test_assonance_breaks_a_tie_the_same_way_under_every_hash_seed() -> None:
    """R-F2: `check` is deterministic across processes, as the README promises, not only
    within one. Each run is a fresh interpreter with its own `PYTHONHASHSEED`."""
    reports = [
        subprocess.run(
            [sys.executable, "-c", _REPORT],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for seed in ("0", "1")
    ]
    assert reports[0] == reports[1]


def test_assonance_names_the_first_tied_vowel_of_the_line() -> None:
    """The tie-break is reading order: of the vowels sharing the top count, the one the
    line reaches first (`Sommer`'s, before `Blume`'s)."""
    report = check("assonance_constraint", _TIED, lang="de")
    found = [violation.found for violation in report.violations]
    assert found == ["1 on 'ɔ'", "1 on 'a'"]
