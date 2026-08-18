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


def test_links_below_the_built_in_minimum_does_not_relax_it() -> None:
    """`links` raises the floor; it cannot lower it. `links=1` collapses into
    the built-in minimum of 2 rather than making a single hokku satisfiable."""
    report = check("renga", HOKKU + "\n\n" + WAKIKU, links=1)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_links_above_the_actual_count_is_rejected_exactly_once() -> None:
    report = check("renga", HOKKU + "\n\n" + WAKIKU, links=5)
    assert not report.satisfied
    too_few = [v for v in report.violations if v.rule == "too_few_links"]
    assert len(too_few) == 1
    assert too_few[0].expected == "at least 5 stanzas"


def test_a_chain_meeting_the_requested_links_is_accepted() -> None:
    chain = HOKKU + "\n\n" + WAKIKU + "\n\n" + HOKKU + "\n\n" + WAKIKU
    report = check("renga", chain, links=4)
    assert report.satisfied, [(v.rule, v.found) for v in report.violations]


def test_a_fault_in_a_later_stanza_reports_a_document_offset() -> None:
    """`line_syllables` measures offsets within the stanza substring it is
    given, but every other procedure's offsets — including this one's own
    `wrong_stanza_shape` — are document-relative. The fault here sits in the
    second stanza, not the first, so a stanza-relative offset and a
    document-relative one point at different places."""
    broken_line = "cat dog mat sat run sky tree big"
    text = HOKKU + "\n\n" + "cat dog mat sat run sky tree\n" + broken_line
    report = check("renga", text)
    faults = [v for v in report.violations if v.rule == "wrong_syllable_count"]
    assert len(faults) == 1
    assert text[faults[0].offset :].startswith(broken_line)
