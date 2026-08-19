from pathlib import Path

from denckring import check, list_procedures
from denckring.eval import harness

README = Path(__file__).resolve().parents[1] / "README.md"

BATCH_ONE = {
    "acrostic",
    "beau_present",
    "heterogram",
    "lipogram",
    "palindrome",
    "pangram",
    "prisoners_constraint",
    "reverse_snowball",
    "snowball",
    "tautogram",
    "telestich",
    "univocalic",
}


def test_readme_example_runs_as_written() -> None:
    report = check("lipogram", "This is a small conforming bit of writing", forbidden="z")
    assert report.satisfied


def test_all_twelve_batch_one_procedures_are_registered() -> None:
    # Later batches add more; Batch 1 must never regress out of the registry.
    assert set(list_procedures()) >= BATCH_ONE


def test_readme_scoreboard_is_the_one_the_harness_reports() -> None:
    """The README's `denckring status` transcript is a claim about this install, and a
    stale one misstates the project's own headline number. It went stale on the very
    next branch after being corrected by hand, because nothing compared the two: this
    test reads the line out of the README and requires it to be exactly what
    `harness.status()` prints.
    """
    text = README.read_text(encoding="utf-8")
    line = harness.status().line()
    assert line in text, (
        f"README does not carry the current scoreboard.\n"
        f"  expected: {line}\n"
        f"  found:    {_scoreboard_line(text) or '(no scoreboard line at all)'}"
    )


def _scoreboard_line(text: str) -> str:
    """The README's scoreboard line, whatever it currently says."""
    for line in text.splitlines():
        if "catalogued ·" in line:
            return line.strip()
    return ""


def test_readme_prose_counts_match_the_scoreboard() -> None:
    """The "What's here" paragraph restates the same four numbers in words, and drifted
    the same way. Every number it names must be one the harness actually reports.
    """
    text = README.read_text(encoding="utf-8")
    coverage = harness.status()
    unimplemented = coverage.implementable - coverage.implemented
    for claim in (
        f"the {coverage.catalogued} catalogued procedures",
        f"{coverage.unreachable} have no mechanical acceptance criterion",
        f"the remaining {unimplemented} are sourced",
    ):
        assert claim in text, f"README's prose does not say {claim!r}"


def test_catalogue_is_larger_than_the_implemented_set() -> None:
    coverage = harness.status()
    assert coverage.catalogued > coverage.implemented
    assert coverage.implemented >= len(BATCH_ONE)


def test_every_implemented_procedure_is_also_validated() -> None:
    """A procedure without golden examples is implemented but unproven."""
    coverage = harness.status()
    assert coverage.implemented == coverage.validated


def test_readme_mentions_the_licence_split() -> None:
    """Two licences in one repository is the kind of thing a reader has to be told
    about in the README rather than left to discover in a file listing (ADR 0006,
    amended by ADR 0024 when the code moved from MIT to Apache-2.0)."""
    text = README.read_text(encoding="utf-8")
    assert "Apache-2.0" in text
    assert "CC BY 4.0" in text


def test_readme_states_what_is_stable() -> None:
    """A README that promises "stable JSON for non-Python callers" and never says what
    that covers leaves every future change to judgement. These four surfaces are the ones
    outside code depends on, so the promise has to name them."""
    text = README.read_text(encoding="utf-8")
    assert "## What is stable" in text
    surfaces = ("Procedure ids", "`Report` as JSON", "catalogue export schema", "denckring.lang")
    for surface in surfaces:
        assert surface in text, f"the stability section does not name {surface}"


def test_readme_says_what_the_name_may_be_used_for() -> None:
    """Apache-2.0 section 6 reserves the name and says nothing about permitted use. A
    reservation nobody can comply with protects less than a stated policy."""
    assert "## Using the name" in README.read_text(encoding="utf-8")
