"""Two rows built on words taken apart: tmesis (a lexicon split) and spoonerism
(a phonemic exchange). Both need the `en` data extra — `lexicon.words` for
tmesis, `phonemes` for spoonerism — installed alongside this suite.
"""

import pytest

from denckring import check
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import Constructive
from denckring.core.registry import get


def test_tmesis_accepts_the_classic_example() -> None:
    report = check("tmesis", "abso-bloody-lutely")
    assert report.satisfied is True
    assert report.metrics["valid_splits"] >= 1.0


def test_tmesis_rejects_when_halves_do_not_rejoin() -> None:
    report = check("tmesis", "cats-really-dogs")
    assert report.satisfied is False
    assert any(v.rule == "halves_do_not_rejoin" for v in report.violations)


def test_tmesis_rejects_a_hyphenation_with_nothing_inserted() -> None:
    """Two hyphen-joined parts is a compound, not a split-and-insertion."""
    report = check("tmesis", "well-known")
    assert report.satisfied is False
    assert any(v.rule == "no_material_inserted" for v in report.violations)


def test_tmesis_scores_below_one_when_any_split_fails() -> None:
    """A violation must never coincide with score == 1.0: a satisfying split
    alongside a failing one must still drag the score down, not get buried
    under the passing one.
    """
    report = check("tmesis", "abso-bloody-lutely cats-really-dogs")
    assert report.violations
    assert report.score < 1.0


def test_spoonerism_accepts_words_with_distinct_onsets() -> None:
    report = check("spoonerism", "cat dog")
    assert report.satisfied is True


def test_spoonerism_rejects_words_sharing_an_onset() -> None:
    report = check("spoonerism", "cat cap")
    assert report.satisfied is False
    assert any(v.rule == "onsets_not_distinct" for v in report.violations)


def test_spoonerism_skips_a_word_missing_from_the_pronouncing_dictionary() -> None:
    """R14: a word absent from CMU must not abort the scan.

    `flurbish` is not a real English word, so `pack.phonemes` raises
    `MissingCapability` for it. The row must catch that locally and still
    produce a report — the pair is scored as a violation, since its
    genuineness cannot be verified, rather than the exception propagating.
    """
    report = check("spoonerism", "flurbish dog")
    assert any(v.rule == "unresolved_phonemes" for v in report.violations)
    assert report.metrics["estimated_words"] >= 1.0


def test_spoonerism_apply_swaps_the_first_two_onsets() -> None:
    procedure = get("spoonerism")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply("cat dog", lang="en")
    assert produced == "dat cog"


def test_spoonerism_apply_round_trips_through_its_own_check() -> None:
    """Whatever `apply` produces, its own `check` must accept."""
    procedure = get("spoonerism")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply("cat dog", lang="en")
    report = check("spoonerism", produced)
    assert report.satisfied is True


def test_spoonerism_apply_refuses_a_single_word() -> None:
    procedure = get("spoonerism")
    assert isinstance(procedure, Constructive)
    with pytest.raises(NoCandidateWord):
        procedure.apply("solo", lang="en")
