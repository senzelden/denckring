"""A word the pronouncing dictionary does not carry is normal in verse.

`word_stress` already settled this for metre: an unknown word scans as free and
is counted, rather than aborting the check. Rhyme had no such path, so a single
unusual noun at a line's end raised `MissingCapability` — naming a capability
the pack does provide — and no poem containing one could be checked at all.

What an unknown word *means* for rhyme is an editorial decision rather than a
library constant, the same argument ADR 0009 makes for diacritic folding, so it
is carried as a parameter.
"""

import pytest

from denckring import check
from denckring.core.errors import DenckringError, MissingCapability

#: `flurbish` is not a word; no pronouncing dictionary carries it.
UNKNOWN = "the cat sat on the flurbish\nthe dog ran to the flurbish"


#: Lines 1-2 rhyme on words the dictionary knows; lines 3-4 end on a word it
#: does not. One pair is decidable, one is not, which is what separates the
#: three readings.
MIXED = """the sun will set behind the hill in may
the fox will hide beneath the fallen way
the owl will call across the flurbish
the mice will creep beside the flurbish"""


def test_an_unknown_line_ending_reports_rather_than_raising() -> None:
    report = check("rhyme_scheme", UNKNOWN, scheme="AA")
    assert report.violations is not None


def test_free_lets_an_unknown_word_satisfy_whatever_the_scheme_asks() -> None:
    """It constrains nothing, in either direction — the `word_stress` reading."""
    report = check("rhyme_scheme", MIXED, scheme="AABB", unknown_rhyme="free")
    assert report.satisfied is True


def test_strict_fails_a_pair_it_cannot_verify() -> None:
    report = check("rhyme_scheme", MIXED, scheme="AABB", unknown_rhyme="strict")
    assert report.satisfied is False
    violation = next(v for v in report.violations if v.rule == "unknown_rhyme")
    assert violation.found == "flurbish"


def test_undecidable_scores_only_the_pairs_it_could_decide() -> None:
    """The default: the known pair is judged, the unknown pairs leave `total`."""
    report = check("rhyme_scheme", MIXED, scheme="AABB")
    assert report.satisfied is True
    assert report.metrics["estimated_words"] == 2.0


#: The qafia is the rhyme *before* the repeated radif, so `ghazal` reaches the
#: dictionary by its own path rather than through the scheme checker.
GHAZAL_UNKNOWN = """i cannot find the flurbish tonight
the lamps have all been slowed tonight
the river takes another turn
and leaves its heavy load tonight"""


def test_an_unknown_qafia_reports_rather_than_raising() -> None:
    report = check("ghazal", GHAZAL_UNKNOWN)
    assert report.violations is not None


def test_undecidable_refuses_to_pass_a_text_it_could_not_judge_at_all() -> None:
    """Scoring nothing over nothing reads as satisfied; that would be a lie.

    A partial verdict is honest. An empty one dressed as 1.0 is the vacuous
    pass this whole parameter exists to avoid.
    """
    report = check("rhyme_scheme", UNKNOWN, scheme="AA")
    assert report.satisfied is False
    assert any(v.rule == "rhyme_undecidable" for v in report.violations)


def test_a_pack_genuinely_lacking_phonemes_still_raises() -> None:
    """The exception is not the bug — refusing a word the dictionary lacks was.

    A pack with no pronunciation at all cannot check rhyme by any reading, and
    saying so is what `MissingCapability` is for.
    """
    with pytest.raises(MissingCapability):
        check("rhyme_scheme", "the cat sat\nthe dog ran", scheme="AA", lang="de")


#: Every row that pairs rhymes. `assonance_constraint` and `spoonerism` declare
#: `phonemes` too, but for vowels and onsets rather than rhyme, so the reading
#: would mean nothing to them.
RHYMING_ROWS = [
    "ballade",
    "blank_verse",
    "clerihew",
    "curtal_sonnet",
    "englyn",
    "ghazal",
    "heroic_couplet",
    "limerick",
    "ottava_rima",
    "petrarchan_sonnet",
    "rhyme_royal",
    "rhyme_scheme",
    "rondeau",
    "shakespearean_sonnet",
    "sonnet",
    "spenserian_stanza",
    "terza_rima",
    "triolet",
    "villanelle",
]


def test_every_rhyming_row_lets_the_caller_choose_the_reading() -> None:
    """The choice is worthless if it only reaches one row's parameter schema."""
    from denckring.core.registry import get

    missing = [
        row for row in RHYMING_ROWS if "unknown_rhyme" not in get(row).params_model().model_fields
    ]
    assert missing == []


def test_a_metre_row_can_scan_an_unknown_word_under_what_it_declares(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`word_stress`'s fallback counts syllables, so a row that scans metre needs
    `syllables.heuristic` as well as `stress` — and ten rows declared only the
    latter. Their own fixtures never reached the fallback, so nothing noticed.
    """
    from denckring.core import catalogue
    from denckring.core.registry import all_procedures, get
    from denckring.eval import harness
    from denckring.lang import get_pack
    from test_requires_honesty import _StrictPack

    real = get_pack("en")
    # Each row's own satisfying fixture, with one word swapped for an invented
    # one: a text of the wrong shape returns on `wrong_line_count` before the
    # scan ever reaches the fallback, so a generic probe cannot see this.
    cases = {
        case.procedure: case
        for case in harness.golden_cases()
        if case.satisfied and case.lang == "en"
    }
    raised = []
    for procedure_id in sorted(all_procedures()):
        declared = frozenset(catalogue.get(procedure_id).requires)
        case = cases.get(procedure_id)
        if "stress" not in declared or case is None:
            continue
        words = case.text.split(" ")
        text = " ".join(["flurbish" if index == 1 else word for index, word in enumerate(words)])
        strict = _StrictPack(real, declared, procedure_id)

        def only_strict(lang: str = "en", _pack: object = strict) -> object:
            return _pack

        monkeypatch.setattr("denckring.lang.get_pack", only_strict)
        try:
            get(procedure_id).check(text, **case.params)
        except MissingCapability as exc:
            raised.append((procedure_id, exc.capability))
        except DenckringError:
            pass  # refusing the text on its own terms is not this defect
        monkeypatch.undo()
    assert raised == []


def test_undecidable_is_the_default() -> None:
    assert check("rhyme_scheme", MIXED, scheme="AABB").satisfied == (
        check("rhyme_scheme", MIXED, scheme="AABB", unknown_rhyme="undecidable").satisfied
    )
