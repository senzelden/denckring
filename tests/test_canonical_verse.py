"""Canonical verse, measured against the checkers that implement its forms.

This is a conformance corpus in miniature, and the smallest honest one: every
line here comes from a published poem old enough to be out of copyright, and
none of it was written for this suite. That is the whole point. 489 of the 532
golden cases were constructed by this project's author, so the suite can agree
with the implementation about a reading both of them share — which is exactly
what these lines are for.

**Three of seven canonical pentameter lines are not read as ten syllables**, for
three different reasons, and only two of the three are recorded anywhere:

1. **Synaeresis.** Milton reads *disobedience* as four syllables; the CMU
   dictionary carries five, exactly and without an estimate, so `Paradise Lost`
   opens on a line this package counts as eleven. English elision has no
   treatment here at all. French has one — ADR 0034, because a mute e elides or
   counts depending on what follows — and English and German were never given
   the equivalent. This is the undocumented cause of the three.
2. **A feminine ending.** Keats' *a thing of beauty is a joy for ever* is eleven
   syllables and is pentameter; the eleventh is unstressed. The catalogue row for
   `iambic_pentameter` already says the substitutions real verse uses "are not
   accepted", so this one is a stated limitation being observed.
3. **A dictionary miss.** *Pierian* is not in the pronouncing dictionary and the
   spelling heuristic guesses two syllables where the line needs three, so Pope's
   couplet reads as nine. `Report.evidence` now names the guessed word, which is
   what makes this diagnosable rather than merely wrong.

Nothing here asserts the poetry is defective. These tests pin what the package
currently reads, with the literary reading beside it, so that a future change —
English elision, a wider metre model, a better fallback — shows up as a diff in
this file rather than as a silent shift in what the catalogue claims to check.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from denckring.lang import get_pack

PACK = get_pack("en")

#: `(source, line, syllables the metre wants, syllables this package reads)`.
#: Where the last two differ, the note says which of the three causes it is.
PENTAMETER = [
    ("Milton, Paradise Lost (1667), I.1", "of mans first disobedience and the fruit", 10, 11),
    ("Milton, Paradise Lost (1667), I.16", "things unattempted yet in prose or rhyme", 10, 10),
    (
        "Gray, Elegy in a Country Churchyard (1751), l.1",
        "the curfew tolls the knell of parting day",
        10,
        10,
    ),
    ("Shakespeare, Sonnet 18 (1609), l.1", "shall i compare thee to a summers day", 10, 10),
    (
        "Pope, An Essay on Criticism (1711), l.363",
        "drink deep or taste not the pierian spring",
        10,
        9,
    ),
    ("Keats, Endymion (1818), l.1", "a thing of beauty is a joy for ever", 11, 11),
    ("Wordsworth, The Prelude (1850)", "and yet the books which i have loved so well", 10, 10),
]


@pytest.mark.parametrize(("source", "line", "wanted", "read"), PENTAMETER)
def test_the_package_reads_canonical_verse_as_recorded(
    source: str, line: str, wanted: int, read: int
) -> None:
    """Characterisation, not judgement. The third argument is what the metre
    asks for and the fourth is what this package answers; where they differ the
    module docstring says why."""
    total, _ = PACK.line_syllables(line)
    assert total == read, f"{source}: reading changed from {read} to {total}"


def test_the_disagreement_is_the_size_it_was_measured_at() -> None:
    """A floor on honesty rather than a target. If a change makes canonical verse
    scan, this fails and the number above should come down — that is the point.
    It also fails if a change makes *more* of it fail, which is the regression
    this corpus exists to catch."""
    disagreeing = [line for _, line, wanted, read in PENTAMETER if wanted != read]
    assert len(disagreeing) == 2, (
        f"{len(disagreeing)} of {len(PENTAMETER)} canonical lines disagree with the "
        f"metre, measured at 2 on 2026-09-08"
    )


def test_the_dictionary_miss_is_reported_rather_than_hidden() -> None:
    """Pope's line is short because a word was guessed at, and the report says so.
    That is the difference between a wrong answer and a diagnosable one."""
    total, estimated = PACK.line_syllables("drink deep or taste not the pierian spring")
    assert total == 9
    assert estimated == 1, "the guessed word should be counted as estimated"


def test_miltons_elision_is_not_a_dictionary_miss() -> None:
    """The sharpest of the three: nothing is estimated, so no existing signal
    marks this line as uncertain. The dictionary is confident and the poet
    disagrees with it, which is a case neither `estimated_words` nor
    `Report.evidence` can currently flag."""
    total, estimated = PACK.line_syllables("of mans first disobedience and the fruit")
    assert (total, estimated) == (11, 0)
    assert PACK.syllable_count("disobedience") == (5, True)


def canonical_lines() -> list[dict[str, object]]:
    """The canonical corpus, with what each line's metre wants beside what this
    package reads. `reads` is filled in here rather than stored, so the fixture
    records the poetry and the suite records the package."""
    path = Path(__file__).parent / "fixtures" / "canonical_lines.yaml"
    rows: list[dict[str, object]] = yaml.safe_load(path.read_text(encoding="utf-8"))
    for row in rows:
        lang = str(row["lang"])
        line = str(row["line"])
        row["reads"] = get_pack(lang).line_syllables(line)[0]
    return rows


#: ADR 0040 D2's ceiling. 3 of 69 English canonical lines disagree with the model
#: without any guessed word involved; the other 12 outliers are lexicon misses.
#: Asserted as a ceiling because D2 declined synaeresis on exactly this number —
#: if it rises, the decision is owed a re-reading.
ENGLISH_TRUE_DISAGREEMENTS = 3


def test_the_english_ceiling_D2_declined_on_has_not_moved() -> None:  # noqa: N802
    """Fails in both directions on purpose. Fewer means English elision just got
    cheaper than ADR 0040 D2 measured it and the decision should be re-read; more
    means a regression.

    The `D2` in the name is ADR 0040's decision label, not a naming lapse — that
    is why the `noqa` above is targeted rather than a blanket exemption.
    """
    pack = get_pack("en")
    # `syllable_evidence` is on `BasePack`, not the published `LanguagePack`
    # protocol (a third-party pack need not implement it), so `getattr` reaches
    # it the same way `procedures/syllable_count.py`'s own reader does.
    evidence = pack.syllable_evidence  # type: ignore[attr-defined]
    disagreements = [
        row
        for row in canonical_lines()
        if row["lang"] == "en"
        and row["reads"] != row["wants"]
        and not any(not exact for *_, exact in evidence(row["line"]))
    ]
    assert len(disagreements) == ENGLISH_TRUE_DISAGREEMENTS, (
        f"{len(disagreements)} English canonical lines disagree with the model with "
        f"no guessed word, not {ENGLISH_TRUE_DISAGREEMENTS}: "
        f"{[r['source'] for r in disagreements]}"
    )
