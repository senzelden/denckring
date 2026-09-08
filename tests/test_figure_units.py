"""Anaphora and epistrophe, against what the catalogue says they check.

Both rows promise "successive **clauses or lines** … the same word **or phrase**".
Both implemented every *line* and a single *word*, so neither could accept the
figure as it is actually written: Gaunt's "This royal throne of kings" carries its
anaphora across an enjambment, and Lincoln's "of the people, by the people, for
the people" is three clauses inside one line.

Found by research batch 3. The constructed cases could not find it, because they
were written to the implementation rather than to the definition.
"""

from __future__ import annotations

from denckring import check

GAUNT = """This royal throne of kings, this sceptred isle,
This earth of majesty, this seat of Mars,
This other Eden, demi-paradise,
This fortress built by Nature for her self
Against infection and the hand of war,
This happy breed of men, this little world,
This precious stone set in a silver sea"""

GETTYSBURG = "that government of the people, by the people, for the people"


def test_anaphora_still_demands_every_line_by_default() -> None:
    """The default does not move: six of Gaunt's seven lines open with `This`."""
    assert not check("anaphora", GAUNT, lang="en", opening="This").satisfied


def test_anaphora_accepts_a_minimum_where_an_enjambment_breaks_the_run() -> None:
    report = check("anaphora", GAUNT, lang="en", opening="This", minimum=6)
    assert report.satisfied, [str(v) for v in report.violations]


def test_anaphora_takes_a_phrase_not_only_a_word() -> None:
    """`this royal` opens one line only, so a phrase must be read as a phrase
    rather than silently truncated to its first word."""
    report = check("anaphora", GAUNT, lang="en", opening="This royal", minimum=1)
    assert report.satisfied


def test_epistrophe_reads_clauses_when_told_to() -> None:
    """The figure is inside one line, so by lines there is one unit and nothing is
    compared — the row reports a vacuous pass. By clauses it is three units and
    the repetition is actually checked, which is the difference that matters."""
    by_line = check("epistrophe", GETTYSBURG, lang="en", closing="the people")
    by_clause = check("epistrophe", GETTYSBURG, lang="en", closing="the people", unit="clause")
    assert by_line.metrics["units"] == 1.0
    assert by_clause.metrics["units"] == 3.0
    assert by_clause.satisfied, [str(v) for v in by_clause.violations]


def test_epistrophe_by_lines_still_fails_the_full_sentence() -> None:
    """The default does not move: with the closing clause restored there are two
    lines, and the second does not end on the refrain."""
    full = GETTYSBURG + ",\nshall not perish from the earth."
    assert not check("epistrophe", full, lang="en", closing="the people").satisfied


def test_epistrophe_clause_unit_still_rejects_a_wrong_closing() -> None:
    """The guard against over-permissiveness."""
    report = check("epistrophe", GETTYSBURG, lang="en", closing="the nation", unit="clause")
    assert not report.satisfied
