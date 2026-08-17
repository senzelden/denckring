"""Alcaic stanza — two hendecasyllables, an enneasyllable, a decasyllable."""

from denckring import check
from denckring.procedures.alcaic_stanza import DECASYLLABLE, ENNEASYLLABLE, HENDECASYLLABLE


def test_the_patterns_are_the_right_length() -> None:
    """These were wrong in the spec's first draft — 10, 8 and 9 against the
    11, 9 and 10 the form requires. Pinned here before anything scans."""
    assert len(HENDECASYLLABLE) == 11
    assert len(ENNEASYLLABLE) == 9
    assert len(DECASYLLABLE) == 10


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("alcaic_stanza", "")
    assert not report.satisfied
    assert report.violations


def test_a_three_line_stanza_is_rejected() -> None:
    report = check("alcaic_stanza", "forest\nforest\nforest")
    assert not report.satisfied
    assert "wrong_line_count" in [v.rule for v in report.violations]
