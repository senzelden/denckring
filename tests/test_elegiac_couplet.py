"""Elegiac couplet — a hexameter then a pentameter."""

from denckring import check
from denckring.procedures.elegiac_couplet import PENTAMETER_PATTERNS


def test_the_pentameter_admits_substitution_only_in_its_first_half() -> None:
    """That asymmetry is the form. A checker allowing substitution throughout
    would accept lines no elegist wrote."""
    assert len(PENTAMETER_PATTERNS) == 4
    assert min(len(p) for p in PENTAMETER_PATTERNS) == 12
    assert max(len(p) for p in PENTAMETER_PATTERNS) == 14
    # Every reading ends with the two fixed dactyls and the final long.
    assert all(p.endswith("1001001") for p in PENTAMETER_PATTERNS)


def test_an_odd_line_count_is_rejected() -> None:
    report = check("elegiac_couplet", "murmuring murmuring murmuring murmuring murmuring forest")
    assert not report.satisfied
    assert "wrong_line_count" in [v.rule for v in report.violations]


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("elegiac_couplet", "")
    assert not report.satisfied
    assert report.violations
