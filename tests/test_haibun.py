"""Haibun — prose and haiku alternating."""

from denckring import check

HAIKU = "cat dog mat sat run\ncat dog mat sat run sky tree\ncat dog mat sat run"
PROSE = "The road turned north and the rain did not let up until evening."


def test_prose_followed_by_a_haiku_is_accepted() -> None:
    report = check("haibun", PROSE + "\n\n" + HAIKU)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_prose_alone_is_rejected() -> None:
    report = check("haibun", PROSE)
    assert not report.satisfied
    assert "missing_haiku" in [v.rule for v in report.violations]


def test_a_haiku_alone_is_rejected() -> None:
    report = check("haibun", HAIKU)
    assert not report.satisfied
    assert "missing_prose" in [v.rule for v in report.violations]


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("haibun", "")
    assert not report.satisfied
    assert report.violations
