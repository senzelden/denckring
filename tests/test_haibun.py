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


def test_estimated_words_is_carried_from_line_syllables() -> None:
    """`line_syllables` promises every syllabic report carries its estimate
    count. `hemlocks` is an ordinary word CMUdict lacks, so it is scanned
    heuristically — the report must say so rather than dropping the count."""
    prose = "The lonely hemlocks stood beside the water in the fading light."
    report = check("haibun", prose + "\n\n" + HAIKU)
    assert report.metrics["estimated_words"] >= 1.0
