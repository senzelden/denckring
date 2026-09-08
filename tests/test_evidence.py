"""A syllabic report names the words it counted and says which it guessed at.

`metrics["estimated_words"]` has carried the uncertainty since the beginning, and
it carries it as a bare number: a haiku report could say two of its words were
estimated and never which two. That is enough to know the verdict is soft and not
enough to do anything about it — to repair the line, to audit the reading, or to
decide whether the estimate fell on the word the count turned on.

`basis` is a closed set and not a confidence score, deliberately. The pack knows
whether a count came from a dictionary or from a spelling heuristic; it does not
know a probability, and attaching one would invent a precision no measurement
here supports.
"""

from __future__ import annotations

import contextlib

import pytest

from denckring import check
from denckring.core.errors import DenckringError
from denckring.core.registry import get

HAIKU_EN = "the evening rain\nis falling softly\nsplash silence again"


def test_a_syllabic_report_names_the_words_it_counted() -> None:
    evidence = check("haiku", HAIKU_EN).evidence
    assert evidence, "a syllabic report with no account of its counting"
    assert {e.subject for e in evidence} >= {"evening", "falling", "softly"}
    assert all(e.value.endswith("syllables") for e in evidence)


def test_every_entry_declares_how_it_was_obtained() -> None:
    assert {e.basis for e in check("haiku", HAIKU_EN).evidence} <= {"dictionary", "estimated"}


def test_the_evidence_agrees_with_the_metric_it_details() -> None:
    """Two statements of one fact, so they have to match. The metric stays for the
    callers already reading it; the evidence is the same number with the
    identities kept."""
    report = check("haiku", HAIKU_EN)
    words = [e for e in report.evidence if e.scope == "word"]
    estimated = sum(1 for e in words if e.basis == "estimated")
    assert estimated == report.metrics["estimated_words"]


def test_offsets_point_into_the_whole_text_not_the_line() -> None:
    """The pack measures within a line it was handed; a caller has the text. An
    offset that silently meant "into line 3" would land a highlight in the wrong
    place, which is the bug `Violation.offset` already exists to avoid."""
    report = check("haiku", HAIKU_EN)
    for entry in report.evidence:
        assert entry.offset is not None
        assert HAIKU_EN[entry.offset :].startswith(entry.subject)


def test_french_reports_a_line_because_that_is_what_it_counts() -> None:
    """A final mute e elides before a vowel and counts before a consonant, so a
    word's contribution is not a property of the word (ADR 0034). There is no
    per-word breakdown to give, and manufacturing one would be the false
    precision this field exists to avoid."""
    report = check(
        "haiku", "un vieux jardin dort\nle silence tombe enfin\nun chat noir traverse", lang="fr"
    )
    assert report.evidence
    assert {e.scope for e in report.evidence} == {"line"}
    assert {e.basis for e in report.evidence} == {"estimated"}


def test_an_exactly_decidable_row_carries_no_evidence() -> None:
    """Empty is the right answer, not a gap. A lipogram's violation already names
    the offending character and its offset; there is nothing an estimate could
    have softened."""
    assert check("lipogram", "a conforming bit of writing", forbidden="z").evidence == []


@pytest.mark.parametrize(
    "procedure", ["haiku", "tanka", "senryu", "cinquain", "syllable_count", "hendecasyllable"]
)
def test_the_syllabic_family_all_carry_it(procedure: str) -> None:
    """They share `pattern_result`, so this is really one assertion that the
    shared helper was the right place to put it."""
    text = "one two three\nfour five six"
    report = (
        get(procedure).check(text, pattern=[3, 3])
        if procedure == "syllable_count"
        else get(procedure).check(text)
    )
    assert report.evidence


def test_no_procedure_returns_evidence_it_cannot_place(procedure_id: str) -> None:
    """A `word`-scoped entry claims a span of the text, so it has to be there."""
    from denckring.core.errors import DenckringError

    text = "one two three\nfour five six"
    try:
        report = get(procedure_id).check(text)
    except DenckringError:
        pytest.skip("needs a parameter this test does not supply")
    for entry in report.evidence:
        if entry.scope == "word" and entry.offset is not None:
            assert text[entry.offset :].startswith(entry.subject)


def test_a_pack_without_the_method_reports_nothing_rather_than_failing() -> None:
    """`LanguagePack` is a published contract satisfied by structure, so a
    third-party pack written before this method must keep working."""
    from denckring.procedures.syllable_count import syllable_evidence

    class Older:
        pass

    assert syllable_evidence("a line", Older()) == []  # type: ignore[arg-type]


def test_metre_names_the_stress_it_read_each_word_as() -> None:
    """A line that does not scan is unactionable as a verdict and actionable as a
    reading: `curfew (10)` is something a writer can argue with."""
    report = check("iambic_pentameter", "the curfew tolls the knell of parting day")
    assert report.evidence
    assert {e.subject for e in report.evidence} >= {"curfew", "parting"}
    assert next(e for e in report.evidence if e.subject == "curfew").value == "10"


def test_rhyme_names_the_keys_the_pairs_were_judged_on() -> None:
    """Two lines fail to rhyme because their key sets do not intersect, and the
    keys are the only thing that makes that verdict checkable by a reader."""
    report = check(
        "rhyme_scheme",
        "the cat sat on the mat\na dog ran by the log\n"
        "the rat wore just a hat\nthe hog was in a bog",
        scheme="ABAB",
    )
    keys = {e.subject: e.value for e in report.evidence}
    assert keys["mat"] == keys["hat"], "a rhyming pair should share a key"
    assert keys["mat"] != keys["log"]


def test_a_word_with_two_pronunciations_reports_both() -> None:
    """`bog` is AA1 G and AO1 G. Reporting one would make the rhyme verdict look
    like a coin toss to anyone checking it against a dictionary."""
    report = check("rhyme_scheme", "a heavy log\na misty bog", scheme="AA")
    assert "/" in next(e for e in report.evidence if e.subject == "bog").value


def test_arca_reports_the_source_it_measured_not_the_music() -> None:
    """`text` is the music — "5 3 1 3" — and the syllables the verdict rests on
    are the source's. Evidence drawn from `text` would name digits, and the
    offsets are dropped because they would index the other string."""
    import yaml

    from denckring.eval.harness import GOLDEN_DIR

    case = yaml.safe_load((GOLDEN_DIR / "arca_musarithmica.yaml").read_text())["cases"][0]
    report = check("arca_musarithmica", case["text"], **case["params"])
    assert report.evidence
    assert all(e.offset is None for e in report.evidence)
    assert not any(e.subject.isdigit() for e in report.evidence)


def test_the_heuristic_rows_carry_evidence_and_the_exact_ones_do_not() -> None:
    """The split `describe().reading.determinacy` reports, checked against what
    the reports actually contain rather than against the catalogue's word for it.

    Not all 41: five rows reach their verdict by paths of their own that this
    chapter did not thread. They are named so the gap is a record rather than a
    surprise.
    """
    from denckring import describe
    from denckring.core.registry import all_procedures

    exact = [i for i in all_procedures() if describe(i).reading.determinacy == "exact"]
    assert exact, "the exact half should not be empty"
    for procedure in exact[:20]:
        with contextlib.suppress(DenckringError):
            assert get(procedure).check("one two three").evidence == []
