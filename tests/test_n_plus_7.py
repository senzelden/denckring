from typing import Any

import pytest

from denckring import check
from denckring.core.errors import InvalidParams
from denckring.procedures.n_plus_7 import NPlus7

pytest.importorskip("denckring_en_data")

SOURCE = "the cat sat on the table"
DISPLACED = "the catacomb satchmo on the tablespoonful"
GARDEN = ["aster", "bramble", "crocus", "dahlia", "elder", "fennel", "gorse", "hazel"]


def test_a_correct_displacement_is_satisfied() -> None:
    assert check("n_plus_7", DISPLACED, source=SOURCE).satisfied


def test_leaving_a_noun_alone_is_readable_as_another_part_of_speech() -> None:
    """A word list cannot rule it out, so it is tolerated and counted."""
    report = check("n_plus_7", SOURCE, source=SOURCE)
    assert report.satisfied
    assert report.metrics["ambiguous_words"] > 0


def test_changing_a_non_noun_is_a_violation() -> None:
    report = check("n_plus_7", "a cat sat on the table", source=SOURCE)
    assert not report.satisfied
    assert report.violations[0].rule == "changed_a_non_noun"


def test_a_wrong_displacement_is_a_violation() -> None:
    wrong = DISPLACED.replace("catacomb", "zebra")
    assert not check("n_plus_7", wrong, source=SOURCE).satisfied


def test_the_three_readings_score_the_same_text_differently() -> None:
    """A text whose unchanged word is a listed noun — readable as a verb there,
    which no word list can rule out. `free` is what ships today."""
    procedure = NPlus7()
    args: dict[str, Any] = {"lang": "en", "source": "the run of the mill"}
    free = procedure.check("the run of the mill", ambiguous_nouns="free", **args)
    strict = procedure.check("the run of the mill", ambiguous_nouns="strict", **args)
    assert free.score > strict.score


def test_ambiguous_words_reports_the_same_count_under_every_reading() -> None:
    """The metric says how much of the verdict rested on the reading chosen, so
    it must not itself depend on the reading."""
    procedure = NPlus7()
    args: dict[str, Any] = {"lang": "en", "source": "the run of the mill"}
    counts = {
        reading: procedure.check("the run of the mill", ambiguous_nouns=reading, **args).metrics[
            "ambiguous_words"
        ]
        for reading in ("undecidable", "free", "strict")
    }
    assert len(set(counts.values())) == 1


def test_the_default_preserves_todays_verdict() -> None:
    """Adding the knob must not change any shipped score."""
    procedure = NPlus7()
    args: dict[str, Any] = {"lang": "en", "source": "the run of the mill"}
    assert (
        procedure.check("the run of the mill", **args).score
        == procedure.check("the run of the mill", ambiguous_nouns="free", **args).score
    )


def test_a_wholly_undecidable_text_is_not_vacuously_satisfied() -> None:
    """`cat` is itself a listed noun (ADR-checked: `pack.noun_index("cat")` is
    8402), so a one-word text identical to its source leaves the only word
    undecided under `undecidable`, driving `total` to zero. `_report` scores
    that 1.0 — vacuously satisfied, right for an empty text but wrong here:
    this text has a word, and it was never weighed. Pinned unsatisfied."""
    procedure = NPlus7()
    report = procedure.check("cat", ambiguous_nouns="undecidable", lang="en", source="cat")
    assert not report.satisfied
    assert report.score == 0.0
    assert report.violations[0].rule == "ambiguous_nouns_undecidable"


def test_the_three_readings_diverge_when_a_real_mistake_sits_beside_an_ambiguity() -> None:
    """`undecidable` and `free` are indistinguishable on a text with no wrong
    displacement — removing an ambiguous position from a perfect numerator and
    denominator leaves a perfect ratio under both, so that case alone cannot
    show the three readings differ. This text has a genuine mistake (`dog` to
    `zebra`, not the correct `doggedness`) alongside two ambiguous unchanged
    nouns (`mill`, `run`), so the mistake is scored differently depending on
    what the ambiguous pair is allowed to contribute.

    Verified: `pack.noun_index` is 8402 for `cat` (-> `catacomb` at +7), 49859
    for `table` (-> `tablespoonful`), 31964 for `mill`, 43615 for `run`, and
    15054 for `dog` (-> `doggedness`, not `zebra`). `the` is `None`.

    Of the 6 words: `the` matches (non-noun, unaffected by the reading),
    `cat`/`table` are correct displacements (also unaffected), `mill`/`run`
    are the ambiguous unchanged pair, and `dog`/`zebra` is the one wrong
    displacement (always a violation, under every reading).

    - `free`        good=5 total=6   5/6 = 0.8(3)  (ambiguous pair counts good)
    - `undecidable` good=3 total=4   3/4 = 0.75    (ambiguous pair excluded)
    - `strict`      good=3 total=6   3/6 = 0.5     (ambiguous pair violates)
    """
    procedure = NPlus7()
    source = "the cat table mill run dog"
    candidate = "the catacomb tablespoonful mill run zebra"
    scores = {
        reading: procedure.check(candidate, lang="en", source=source, ambiguous_nouns=reading).score
        for reading in ("free", "undecidable", "strict")
    }
    assert scores == {"free": 5 / 6, "undecidable": 0.75, "strict": 0.5}
    assert len(set(scores.values())) == 3


def test_a_different_word_count_is_a_violation() -> None:
    report = check("n_plus_7", "too short", source=SOURCE)
    assert report.violations[0].rule == "wrong_word_count"


def test_a_supplied_dictionary_is_the_one_that_gets_walked() -> None:
    """`n_plus_7`'s catalogue definition says the displacement happens "in a
    chosen dictionary". Until now there was no choice — the defect class ADR 0015
    exists to prevent, sitting in the row since it was written."""
    produced = NPlus7().apply("aster", lang="en", dictionary=GARDEN, offset=1)
    assert produced == "bramble"


def test_check_verifies_against_the_same_dictionary_it_was_given() -> None:
    """The reason `dictionary` is on the CHECK params and not apply-only: given a
    different list, `check` computes different displacements and rejects correct
    work. Both directions, or this proves only that the parameter is accepted."""
    procedure = NPlus7()
    produced = procedure.apply("aster", lang="en", dictionary=GARDEN, offset=1)
    assert procedure.check(
        produced, lang="en", source="aster", dictionary=GARDEN, offset=1
    ).satisfied
    assert not procedure.check(produced, lang="en", source="aster", offset=1).satisfied


def test_the_default_is_still_the_packs_nouns() -> None:
    """Nothing changes for a caller who does not ask."""
    procedure = NPlus7()
    assert procedure.apply("cat", lang="en") == procedure.apply("cat", lang="en", dictionary=None)


def test_a_dictionary_entry_must_survive_the_tokeniser() -> None:
    """ADR 0015 restricts `nouns()` to single alphabetic lemmas because a
    displacement has to be a word the tokeniser gives back whole — `cat's-paw`
    comes back as three tokens and breaks the source-to-result correspondence.
    A supplied list is held to the same rule, for the same reason."""
    with pytest.raises(InvalidParams):
        NPlus7().apply("aster", lang="en", dictionary=["aster", "cat's-paw"])


def test_an_empty_dictionary_is_refused() -> None:
    """`(index + offset) % len(nouns)` divides by it."""
    with pytest.raises(InvalidParams):
        NPlus7().apply("aster", lang="en", dictionary=[])
