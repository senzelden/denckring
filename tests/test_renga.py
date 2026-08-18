"""Renga — alternating three-line and two-line stanzas."""

from denckring import check

HOKKU = "cat dog mat sat run\ncat dog mat sat run sky tree\ncat dog mat sat run"
WAKIKU = "cat dog mat sat run sky tree\ncat dog mat sat run sky tree"


def test_an_alternating_chain_is_accepted() -> None:
    report = check("renga", HOKKU + "\n\n" + WAKIKU)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_a_single_stanza_is_a_hokku_not_a_renga() -> None:
    report = check("renga", HOKKU)
    assert not report.satisfied
    assert "too_few_links" in [v.rule for v in report.violations]


def test_a_chain_beginning_with_a_two_line_stanza_is_rejected() -> None:
    report = check("renga", WAKIKU + "\n\n" + HOKKU)
    assert not report.satisfied


def test_an_empty_text_is_unsatisfied_and_says_why() -> None:
    report = check("renga", "")
    assert not report.satisfied
    assert report.violations
