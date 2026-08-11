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
    assert set(list_procedures()) == BATCH_ONE


def test_catalogue_is_larger_than_the_implemented_set() -> None:
    coverage = harness.status()
    assert coverage.catalogued > coverage.implemented
    assert coverage.implemented == coverage.validated == len(BATCH_ONE)


def test_readme_mentions_the_licence_split() -> None:
    text = README.read_text(encoding="utf-8")
    assert "MIT" in text
    assert "CC BY 4.0" in text
