"""Dactylic hexameter — six feet, the first four substitutable."""

from denckring import check
from denckring.procedures.dactylic_hexameter import PATTERNS


def test_the_pattern_set_is_the_classical_one() -> None:
    """Feet 1-4 dactyl or spondee, foot 5 dactyl, foot 6 spondee or trochee."""
    assert len(PATTERNS) == 32
    assert min(len(p) for p in PATTERNS) == 13
    assert max(len(p) for p in PATTERNS) == 17


def test_real_hexameter_from_the_literature_is_accepted() -> None:
    """Longfellow's opening line. It contains `hemlocks`, which CMUdict does not
    carry — before the out-of-dictionary repair this raised rather than scanned."""
    report = check(
        "dactylic_hexameter",
        "This is the forest primeval the murmuring pines and the hemlocks",
    )
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]
    assert report.metrics["estimated_words"] >= 1


def test_prose_of_the_right_length_is_rejected() -> None:
    """The whole argument for scanning stress rather than counting syllables: a
    count-only checker cannot tell these two apart."""
    report = check("dactylic_hexameter", "I walked down to the shop this morning to buy a loaf")
    assert not report.satisfied
    assert report.violations


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("dactylic_hexameter", "")
    assert not report.satisfied
    assert report.violations


def test_substitutable_feet_actually_accept_a_spondee() -> None:
    """Counting `len(PATTERNS)` proves the set has 32 members but not that a
    scan ever uses one of the 31 that aren't all-dactyl-then-trochee. These
    pin the substitution itself: a spondee in foot 1, a spondee in foot 6, two
    spondees, and all four substitutable feet as spondees, all still satisfy.
    `daylight`/`birthright`/`moonlight` read `1?` in CMUdict — primary stress
    then secondary, which this pack renders `?` — so they fit the `11`
    spondee slot through the free second syllable."""
    lines = [
        "daylight murmuring murmuring murmuring murmuring forest",
        "murmuring murmuring murmuring murmuring murmuring daylight",
        "daylight birthright murmuring murmuring murmuring forest",
        "daylight birthright moonlight daylight murmuring forest",
    ]
    for line in lines:
        report = check("dactylic_hexameter", line)
        assert report.satisfied, (line, [(v.rule, v.found) for v in report.violations])
