"""Carroll's doublets: one letter per step, every step a word."""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams, NoCandidateWord
from denckring.core.protocol import Constructive
from denckring.core.registry import get


def test_a_valid_ladder_is_accepted() -> None:
    assert check("word_ladder", "cold cord card ward warm").satisfied is True


def test_a_step_changing_two_letters_is_rejected() -> None:
    report = check("word_ladder", "cold card warm")
    assert report.satisfied is False
    violation = next(v for v in report.violations if v.rule == "step_too_large")
    assert violation.found == "card"


def test_a_step_that_is_not_a_word_is_rejected() -> None:
    report = check("word_ladder", "cold cald card ward warm")
    assert report.satisfied is False
    assert any(v.rule == "not_a_word" for v in report.violations)


def test_apply_finds_a_ladder_its_own_check_accepts() -> None:
    """The round-trip property every generative row must satisfy."""
    procedure = get("word_ladder")
    assert isinstance(procedure, Constructive)
    ladder = procedure.apply("cold", target="warm")
    assert check("word_ladder", ladder).satisfied is True
    assert ladder.split()[0] == "cold"
    assert ladder.split()[-1] == "warm"


def test_the_canonical_german_step_is_accepted_with_folding_off() -> None:
    """`schon` to `schön` is the German doublet, and this row declares `de`.

    Folding is what decides it: folded, `ö` is `o`, the two are the same word, and
    the step is rightly refused. The row had no way to say otherwise — it folded
    unconditionally — so it reported `step_too_large` with the note "no letters
    differ", a violation contradicting its own rule name. `fold_diacritics` is now a
    parameter, as it is on `univocalic` and `homovocalism`.
    """
    assert check("word_ladder", "schon schön", lang="de", fold_diacritics=False).satisfied is True

    folded = check("word_ladder", "schon schön", lang="de")
    assert folded.satisfied is False
    assert [v.rule for v in folded.violations] == ["step_too_large"]


def test_apply_can_reach_an_umlaut_with_folding_off() -> None:
    """`_substitutions` walked `string.ascii_lowercase`, so no ladder `apply` ever
    produced could contain ä, ö or ü — the `de` declaration was unreachable from the
    generator's side however `check` was configured."""
    procedure = get("word_ladder")
    assert isinstance(procedure, Constructive)
    ladder = procedure.apply("schon", lang="de", target="schön", fold_diacritics=False)
    assert ladder == "schon schön"
    assert check("word_ladder", ladder, lang="de", fold_diacritics=False).satisfied is True


def test_apply_answers_every_malformed_endpoint_with_invalid_params() -> None:
    """One field, one error code. A missing target raised `InvalidParams` while a
    non-alphabetic or wrong-length one raised `NoCandidateWord`, seventeen lines
    apart. `NoCandidateWord` now means the search came back empty, not that the
    caller mistyped."""
    procedure = get("word_ladder")
    assert isinstance(procedure, Constructive)
    with pytest.raises(InvalidParams):
        procedure.apply("cold")
    with pytest.raises(InvalidParams):
        procedure.apply("cold", target="wa-rm")
    with pytest.raises(InvalidParams):
        procedure.apply("cold", target="warmth")


def test_an_endpoint_the_lexicon_does_not_know_is_a_search_failure() -> None:
    """The other side of the line: the parameters are well-formed, and the search has
    nothing to walk from."""
    procedure = get("word_ladder")
    assert isinstance(procedure, Constructive)
    with pytest.raises(NoCandidateWord):
        procedure.apply("cold", target="zzzz")


def test_the_ladder_prefers_rungs_a_reader_recognises() -> None:
    """`cold -> warm` climbed through `wold` (SCOWL band 55) and `wald` (absent
    from the graded list entirely), because the breadth-first search enqueued
    neighbours in the order `_substitutions` generated them — alphabetical.

    Sorting the *valid* neighbours by band before enqueuing does not touch the
    search's guarantee: every neighbour at depth d is still enqueued before any
    at depth d+1, so the ladder returned is still a shortest one. Only which
    shortest ladder is found first changes.
    """
    from denckring import apply

    rungs = apply("word_ladder", "cold", lang="en", target="warm").split()
    assert rungs[0] == "cold" and rungs[-1] == "warm"
    assert "wold" not in rungs


def test_ranking_did_not_lengthen_the_ladder() -> None:
    """The search's whole claim is that it returns a *shortest* ladder. A
    preference that made it longer would have broken the thing it decorates."""
    from denckring import apply

    assert len(apply("word_ladder", "cold", lang="en", target="warm").split()) == 5
