"""Two selections from a source, differing only in where the letter must land."""

from denckring import check, get
from denckring.core.protocol import Constructive

SOURCE = "silence is the garden where nothing grows and everything waits"


def test_diastic_picks_words_by_position() -> None:
    """Word 1 has s first, word 2 has h second, word 3 has o third, word 4 has r
    fourth — a selection that genuinely satisfies, asserted as satisfying.

    The case this replaced read `seed_phrase="sil"` over `"silence is silence"` and
    asserted only `isinstance(report.satisfied, bool)`, which is true of every report
    this library can produce. Measured, that case scored 0.67 and raised both
    `not_in_source` and `wrong_letter_at_position`: the docstring described a passing
    selection and the assertion could not have noticed it was a failing one.
    """
    report = check("diastic", "silence the grows everything", source=SOURCE, seed_phrase="shore")
    assert report.satisfied is True


def test_diastic_rejects_a_word_whose_letter_is_wrong() -> None:
    report = check("diastic", "garden is silence", source=SOURCE, seed_phrase="sil")
    assert report.satisfied is False
    assert any(v.rule == "wrong_letter_at_position" for v in report.violations)


def test_a_selection_must_come_from_the_source() -> None:
    report = check("diastic", "elephant", source=SOURCE, seed_phrase="e")
    assert report.satisfied is False
    assert any(v.rule == "not_in_source" for v in report.violations)


def test_diastic_apply_round_trips() -> None:
    procedure = get("diastic")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply(SOURCE, seed_phrase="sil")
    assert produced
    report = procedure.check(produced, source=SOURCE, seed_phrase="sil")
    assert report.satisfied


def test_diastic_apply_uses_the_caller_supplied_seed_phrase() -> None:
    """Pins R15: `seed_phrase` used to be named `seed`, which collided with
    `apply`'s reserved `seed: int | None` RNG keyword — a caller-supplied value
    was silently discarded in favour of the default (`"the"`), with no error.
    Two different seed phrases must now produce two different outputs."""
    procedure = get("diastic")
    assert isinstance(procedure, Constructive)
    produced_default = procedure.apply(SOURCE)
    produced_custom = procedure.apply(SOURCE, seed_phrase="sil")
    assert produced_default != produced_custom


def test_mesostic_runs_the_spine_down_the_middle() -> None:
    """s, i, t, g down the four lines, in that order, from the source in that order."""
    report = check(
        "mesostic",
        "silence\nis\nthe\ngarden",
        source=SOURCE,
        spine="sitg",
    )
    assert report.satisfied is True


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
