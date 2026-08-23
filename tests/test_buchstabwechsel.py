"""Buchstabwechsel — Harsdörffer's letter-exchange, not a copy of `anagram`.

Pins Rule II (p. 514 of the *Erquickstunden*, 1651). Only the h-exemption is a
genuine behavioural difference from `anagram`'s multiset equality; the u/i-not-
v/j prohibition is a rule Harsdörffer states explicitly but which `anagram`
already satisfies by construction — its `fold_diacritics` never merged those
letters — so the tests below pin that prohibition against future regression,
not against a difference from `anagram` that exists today. See
`PRIMARY-SOURCE.md`, the module docstring in
`denckring/procedures/buchstabwechsel.py`, and the catalogue row's `notes` for
the transcription, the reasoning, and the correction of an earlier, wrong claim
that `anagram` would accept the swap.
"""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams
from denckring.lang.de import GermanPack
from denckring.procedures.buchstabwechsel import Buchstabwechsel


def test_dropping_the_h_from_the_source_still_satisfies() -> None:
    """ "übergangen" — the h may be passed over. "Anjon" has Johann's other
    letters (j, o, a, n, n) and no h at all."""
    report = check("buchstabwechsel", "Anjon", lang="de", source="Johann")
    assert report.satisfied is True


def test_inserting_an_h_the_source_never_had_still_satisfies() -> None:
    """ "eingerucket" — the h may be inserted. "Hase" has no h in a candidate
    built from "Ase" plus one, and the source carries none either."""
    report = check("buchstabwechsel", "Hase", lang="de", source="Ase")
    assert report.satisfied is True


def test_h_counts_are_independent_on_both_sides() -> None:
    """Rule II frees h in both directions at once: a source with one h and a
    candidate with three, or none, are all indifferent to each other."""
    assert check("buchstabwechsel", "hhhalos", lang="de", source="halos").satisfied is True
    assert check("buchstabwechsel", "aslo", lang="de", source="hhalos").satisfied is True


def test_a_plain_anagram_would_reject_the_dropped_h_but_this_row_accepts_it() -> None:
    """The same pair scored by `anagram` fails on the h alone."""
    assert check("anagram", "Anjon", lang="de", source="Johann").satisfied is False
    assert check("buchstabwechsel", "Anjon", lang="de", source="Johann").satisfied is True


def test_iohann_against_johann_fails() -> None:
    """Pinned per the brief: Rule II's "das u und i die Stimmer nicht für v und j
    setzend" refuses exactly the Latin-alphabet habit of writing I for
    consonantal J. `anagram` already rejects this pair too (see
    `test_anagram_also_rejects_i_for_j_but_this_row_states_the_rule` below); a
    checker whose folding merged i with j would not, which is the regression
    this test guards against."""
    report = check("buchstabwechsel", "Iohann", lang="de", source="Johann")
    assert report.satisfied is False
    rules = {v.rule for v in report.violations}
    assert "surplus_letter" in rules
    assert "missing_letter" in rules


def test_u_read_as_v_fails() -> None:
    """The other half of the same prohibition: u must not stand in for v."""
    report = check("buchstabwechsel", "Uater", lang="de", source="Vater")
    assert report.satisfied is False


def test_anagram_also_rejects_i_for_j_but_this_row_states_the_rule() -> None:
    """Correction of an earlier draft: this row's own notes used to claim a
    plain anagram check would wrongly *accept* an i-for-j or u-for-v swap, making
    the prohibition a second reason buchstabwechsel is not a duplicate of
    `anagram`. Measured, that is false — `anagram`'s `fold_diacritics` is
    case-folding plus NFKD combining-mark stripping, which never merged those
    letters, so `anagram` already rejects both pairs below on its own. Both
    procedures give the same verdict here; the difference is that Harsdörffer
    states the u/i-not-v/j prohibition as a rule (Rule II) and this row pins it
    with its own test, so a future change to `fold_diacritics` that introduced
    the merge would be caught here even if nothing else noticed. The genuine,
    load-bearing reason this row is not a duplicate of `anagram` is the
    h-exemption alone — see the tests above."""
    assert check("anagram", "Uater", lang="de", source="Vater").satisfied is False
    assert check("buchstabwechsel", "Uater", lang="de", source="Vater").satisfied is False
    assert check("anagram", "Iohann", lang="de", source="Johann").satisfied is False
    assert check("buchstabwechsel", "Iohann", lang="de", source="Johann").satisfied is False


def test_missing_and_surplus_letters_are_reported_outside_h() -> None:
    report = check("buchstabwechsel", "Johannx", lang="de", source="Johann")
    assert report.satisfied is False
    assert {v.rule for v in report.violations} == {"surplus_letter"}


def test_missing_source_is_an_invalid_params_error() -> None:
    with pytest.raises(InvalidParams):
        check("buchstabwechsel", "Anjon", lang="de")


def test_known_words_metric_counts_lexicon_membership() -> None:
    """ "anjon" is nobody's German word; "hallo" is. `check` never fails on the
    first, and reports the count the way `definitional_expansion` reports
    `estimated_words`."""
    unknown = check("buchstabwechsel", "Anjon", lang="de", source="Johann")
    assert unknown.metrics["known_words"] == 0.0

    known = check("buchstabwechsel", "hallo", lang="de", source="hallo")
    assert known.metrics["known_words"] == 1.0


def test_unknown_output_words_never_fail_the_check() -> None:
    """Rule II asks only that every letter appear; nothing requires the result
    to be an attested word. "Anjon" is not in the lexicon and still satisfies."""
    report = check("buchstabwechsel", "Anjon", lang="de", source="Johann")
    assert report.satisfied is True
    assert not any(v.rule == "not_a_word" for v in report.violations)


def test_known_words_metric_is_omitted_without_the_lexicon_capability() -> None:
    """Without `denckring-de-data`, the base `GermanPack` has no `lexicon.words`
    — `check` must not raise, and must not claim a count it cannot demonstrate."""
    procedure = Buchstabwechsel()
    params = procedure.parse_params({"source": "hallo"})
    report = procedure._check("hallo", GermanPack(), params)
    assert report.satisfied is True
    assert "known_words" not in report.metrics
