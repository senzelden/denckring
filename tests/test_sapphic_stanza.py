"""Sapphic stanza — three hendecasyllables and an adonic."""

from denckring import check
from denckring.procedures.sapphic_stanza import ADONIC, HENDECASYLLABLE


def test_the_patterns_are_the_right_length() -> None:
    assert len(HENDECASYLLABLE) == 11
    assert len(ADONIC) == 5


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("sapphic_stanza", "")
    assert not report.satisfied
    assert report.violations


def test_a_three_line_stanza_is_rejected() -> None:
    report = check("sapphic_stanza", "forest\nforest\nforest")
    assert not report.satisfied
    assert "wrong_line_count" in [v.rule for v in report.violations]
