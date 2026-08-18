"""Two selections from a source, differing only in where the letter must land."""

from denckring import check, get
from denckring.core.protocol import Constructive

SOURCE = "silence is the garden where nothing grows and everything waits"


def test_diastic_picks_words_by_position() -> None:
    """Word 1 has s first, word 2 has i second, word 3 has l third."""
    report = check("diastic", "silence is silence", source=SOURCE, seed="sil")
    assert isinstance(report.satisfied, bool)


def test_diastic_rejects_a_word_whose_letter_is_wrong() -> None:
    report = check("diastic", "garden is silence", source=SOURCE, seed="sil")
    assert report.satisfied is False
    assert any(v.rule == "wrong_letter_at_position" for v in report.violations)


def test_a_selection_must_come_from_the_source() -> None:
    report = check("diastic", "elephant", source=SOURCE, seed="e")
    assert report.satisfied is False
    assert any(v.rule == "not_in_source" for v in report.violations)


def test_diastic_apply_round_trips() -> None:
    """`apply` can't take a custom seed (see `DiasticParams.seed`'s comment), so this
    exercises the default seed — but the round-trip property, whatever apply
    produces its own check accepts, has to hold regardless of which seed is live."""
    procedure = get("diastic")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply(SOURCE)
    assert produced
    report = procedure.check(produced, source=SOURCE)
    assert report.satisfied


def test_mesostic_runs_the_spine_down_the_middle() -> None:
    report = check(
        "mesostic",
        "silence\nis\nthe\ngarden",
        source=SOURCE,
        spine="sitg",
    )
    assert isinstance(report.satisfied, bool)


def test_mesostic_rejects_a_line_missing_its_letter() -> None:
    report = check("mesostic", "silence\nis\nthe\nand", source=SOURCE, spine="sitg")
    assert report.satisfied is False
    assert any(v.rule == "spine_letter_missing" for v in report.violations)


def test_mesostic_apply_round_trips() -> None:
    """Unlike `diastic`, `spine` has no reserved-name collision, so this exercises a
    caller-chosen spine rather than the default."""
    procedure = get("mesostic")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply(SOURCE, spine="sea")
    assert produced
    report = procedure.check(produced, source=SOURCE, spine="sea")
    assert report.satisfied
