"""`paronomasia` — the pun as a relation between a text and the phrase it displaces.

The row is `checkability: source`: nothing here decides whether a pun is good, or
even whether it is a pun. It decides whether the text stands in the declared
relation to the declared phrase — one word displaced, the rest untouched, the
displacement landing inside the requested band of phonetic distance.
"""

from __future__ import annotations

import pytest

from denckring import check as _check
from denckring import produce as _produce
from denckring.core.errors import InvalidParams, NoCandidateWord
from denckring.core.protocol import Lang, Production, Report


def check(text: str, *, lang: Lang = "en", **params: object) -> Report:
    return _check("paronomasia", text, lang=lang, **params)


def produce(text: str, *, lang: Lang = "en", **params: object) -> Production:
    return _produce("paronomasia", text, lang=lang, **params)


def rules(report: Report) -> list[str]:
    return [violation.rule for violation in report.violations]


# --- the relation holds ------------------------------------------------------


def test_a_one_word_displacement_at_a_small_distance_is_satisfied() -> None:
    """*Bread Pitt* displaces `Brad`, one vowel away."""
    report = check("Bread Pitt", source="Brad Pitt")
    assert report.satisfied
    assert report.score == 1.0


def test_the_untouched_remainder_is_not_required_to_match_case() -> None:
    report = check("bread pitt", source="Brad Pitt")
    assert report.satisfied


def test_a_homophone_is_satisfied_at_the_default_band() -> None:
    """Distance 0.0 sits inside the default band, whose floor is 0.0."""
    report = check("Knead to Know", source="Need to Know")
    assert report.satisfied
    assert report.metrics["max_distance"] == 0.0


def test_metrics_report_what_the_verdict_was_computed_from() -> None:
    report = check("Bread Pitt", source="Brad Pitt")
    assert report.metrics["displacements"] == 1.0
    assert 0.0 < report.metrics["max_distance"] <= 0.5


def test_evidence_carries_both_pronunciations() -> None:
    report = check("Bread Pitt", source="Brad Pitt")
    assert [e.subject for e in report.evidence] == ["Bread"]  # as the text spells it
    assert all(e.basis == "dictionary" for e in report.evidence)


# --- the relation fails, each for its own reason ------------------------------


def test_a_text_identical_to_its_source_states_no_pun() -> None:
    report = check("Brad Pitt", source="Brad Pitt")
    assert not report.satisfied
    assert rules(report) == ["no_displacement"]


def test_a_displacement_beyond_the_band_is_named_as_such() -> None:
    """`Pitt` for `Brad` is a word, and nowhere near it."""
    report = check("Pitt Pitt", source="Brad Pitt", max_distance=0.25)
    assert not report.satisfied
    assert "distance_out_of_band" in rules(report)


def test_a_displacement_below_the_band_floor_is_also_out_of_band() -> None:
    """The band has two edges. A caller asking for a forced pun refuses a homophone."""
    report = check("Knead to Know", source="Need to Know", min_distance=0.2)
    assert not report.satisfied
    assert "distance_out_of_band" in rules(report)


def test_more_displacements_than_allowed_is_unrecoverable() -> None:
    report = check("Bread Pit", source="Brad Pitt")
    assert not report.satisfied
    assert "unrecoverable" in rules(report)


def test_a_differing_word_count_breaks_the_alignment() -> None:
    report = check("Bread Pitt Junior", source="Brad Pitt")
    assert not report.satisfied
    assert rules(report) == ["length_mismatch"]


def test_an_empty_text_does_not_score_one_vacuously() -> None:
    """`_report` scores an empty text 1.0 unless the row says otherwise, and a
    pun on nothing is not a pun. `pangram` carries the same guard for the same
    reason."""
    for text, source in (("", ""), ("   ", "")):
        report = check(text, source=source)
        assert not report.satisfied
        assert rules(report) == ["no_displacement"]


def test_an_empty_text_against_a_real_phrase_breaks_the_alignment() -> None:
    report = check("", source="Brad Pitt")
    assert not report.satisfied
    assert rules(report) == ["length_mismatch"]


def test_a_coined_word_is_reported_rather_than_guessed_at() -> None:
    """The measured bound on this row: nothing here can pronounce `Hairways`."""
    report = check("British Hairways", source="British Airways")
    assert not report.satisfied
    assert "unresolvable_pronunciation" in rules(report)


def test_an_unresolvable_text_does_not_score_one_vacuously() -> None:
    report = check("Hairitage Barberella", source="Heritage Cinderella")
    assert not report.satisfied
    assert report.score < 1.0


# --- the three readings of an unpronounceable word ---------------------------


def test_unknown_word_free_accepts_what_it_cannot_check() -> None:
    report = check("British Hairways", source="British Airways", unknown_word="free")
    assert report.satisfied


def test_unknown_word_strict_refuses_it() -> None:
    report = check("British Hairways", source="British Airways", unknown_word="strict")
    assert not report.satisfied
    assert "unresolvable_pronunciation" in rules(report)


def test_unknown_word_undecidable_is_the_default_and_reports() -> None:
    default = check("British Hairways", source="British Airways")
    named = check("British Hairways", source="British Airways", unknown_word="undecidable")
    assert rules(default) == rules(named)
    assert default.metrics["unresolved"] == 1.0


# --- parameters ---------------------------------------------------------------


def test_an_inverted_band_is_refused_rather_than_silently_empty() -> None:
    with pytest.raises(InvalidParams):
        check("Bread Pitt", source="Brad Pitt", min_distance=0.6, max_distance=0.2)


def test_an_unknown_parameter_is_refused() -> None:
    with pytest.raises(InvalidParams):
        check("Bread Pitt", source="Brad Pitt", badness=0.5)


# --- other languages ----------------------------------------------------------


def test_french_displaces_at_a_small_distance() -> None:
    """`Laxa'tif` and `Diminu'tif` are the French salon family; both bases are words."""
    report = check("diminutif normatif", source="diminutif nominatif", lang="fr")
    assert report.satisfied


def test_german_displaces_at_a_small_distance() -> None:
    report = check("Kamm rein", source="Komm rein", lang="de")
    assert report.satisfied


# --- the generator ------------------------------------------------------------


def test_produce_returns_texts_its_own_checker_accepts() -> None:
    production = produce("Brad Pitt")
    assert production.candidates
    for candidate in production.candidates:
        assert check(candidate.text, source="Brad Pitt").satisfied


def test_produce_keeps_the_untouched_remainder_byte_for_byte() -> None:
    for candidate in produce("Curl up & die!").candidates:
        assert candidate.text.endswith("!")
        assert "&" in candidate.text


def test_produce_refuses_a_phrase_it_cannot_pronounce() -> None:
    with pytest.raises(NoCandidateWord):
        produce("Hairitage Barberella")


def test_produce_is_deterministic() -> None:
    assert produce("Brad Pitt").texts == produce("Brad Pitt").texts


def test_each_violating_strategy_case_trips_the_rule_it_names() -> None:
    """The strategy file records a rule per case; without this, nothing reads it.

    `tests/test_strategies.py` asserts only that a violating case is unsatisfied,
    which a case failing for the wrong reason passes just as well — the French
    `kangaroo_word` negative that claimed "letters out of order" while actually
    missing a letter is the recorded instance. Six cases exist to cover six
    distinct rules, and this is what keeps them covering six.
    """
    from strategies.paronomasia import VIOLATING

    for text, source, params, expected in VIOLATING:
        report = check(text, source=source, **params)
        assert not report.satisfied, f"{text!r} should not satisfy"
        assert expected in rules(report), (
            f"{text!r} against {source!r} was meant to trip {expected!r}, "
            f"but tripped {rules(report)}"
        )
    # Five rules over six cases: `distance_out_of_band` appears twice on purpose,
    # once for each edge of the band, which is the parameter the row exists for.
    assert {rule for *_, rule in VIOLATING} == {
        "no_displacement",
        "distance_out_of_band",
        "unrecoverable",
        "unresolvable_pronunciation",
        "length_mismatch",
    }
