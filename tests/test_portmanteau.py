"""`portmanteau` — a coinage that shows one word inside another.

*Haarmonie* is *Harmonie* with `Haar` visible in it; *Hairitage* is *heritage*
with `hair`. This is the half of the punning-shopfront tradition `paronomasia`
cannot reach, because the surface is a word no dictionary carries — and the way
round it is that a blend is never arbitrary: both the host and the word spliced
into it are ordinary dictionary words, so nothing unknown has to be pronounced.
"""

from __future__ import annotations

import pytest

from denckring import check as _check
from denckring.core.errors import InvalidParams
from denckring.core.protocol import Lang, Report


def check(text: str, *, lang: Lang = "en", **params: object) -> Report:
    return _check("portmanteau", text, lang=lang, **params)


def rules(report: Report) -> list[str]:
    return [violation.rule for violation in report.violations]


# --- the relation holds -------------------------------------------------------


def test_hairitage_is_heritage_with_hair_in_it() -> None:
    report = check("Hairitage", source="heritage", splice="hair")
    assert report.satisfied


def test_haarmonie_is_the_case_the_equivalence_table_exists_for() -> None:
    """`Haar` is `h aː ɐ̯` and `Harmonie` opens `h a ʁ`: the same r, spelled two
    ways because German vocalises it in the coda. Unfolded this is 0.667 and out
    of band; folded it is 0.333 and the best-known German blend in the tradition
    is reachable."""
    report = check("Haarmonie", lang="de", source="Harmonie", splice="Haar")
    assert report.satisfied
    assert report.metrics["distance"] == pytest.approx(1 / 3, abs=0.01)


def test_foehnix_is_a_homophone_splice() -> None:
    report = check("Föhnix", lang="de", source="Phönix", splice="Föhn")
    assert report.satisfied
    assert report.metrics["distance"] == 0.0


def test_the_splice_may_sit_anywhere_in_the_coinage() -> None:
    report = check("ExtraordinHair", source="extraordinary", splice="hair")
    assert "splice_not_present" not in rules(report)


# --- the relation fails, each for its own reason ------------------------------


def test_a_coinage_that_does_not_show_the_word_is_not_a_blend() -> None:
    report = check("Heritage", source="heritage", splice="hair")
    assert not report.satisfied
    assert "splice_not_present" in rules(report)


def test_the_spliced_word_must_be_a_word() -> None:
    """Otherwise any letters at all could be declared the joke."""
    report = check("Hairitage", source="heritage", splice="airit")
    assert not report.satisfied
    assert "splice_not_a_word" in rules(report)


def test_a_host_that_cannot_be_heard_behind_the_coinage_is_unrecoverable() -> None:
    report = check("Hairitage", source="bicycle", splice="hair")
    assert not report.satisfied
    assert "host_unrecoverable" in rules(report)


def test_a_splice_that_sounds_like_no_part_of_the_host_is_out_of_band() -> None:
    """`bread` is a word and is present, and `breaditage` is close enough to
    `heritage` to be recoverable — but `bread` sounds like nothing in it."""
    report = check("Breaditage", source="heritage", splice="bread", max_distance=0.34)
    assert not report.satisfied
    assert "sound_out_of_band" in rules(report)


def test_a_host_the_dictionary_cannot_pronounce_is_reported() -> None:
    """`Barbarella` is not in CMUdict, and the honest answer is to say so rather
    than guess. This is the measured limit of the whole approach: it needs both
    halves to be real words, and a proper noun often is not one."""
    report = check("Barberella", source="Barbarella", splice="barber")
    assert not report.satisfied
    assert "unresolvable_pronunciation" in rules(report)


def test_an_empty_text_does_not_score_one_vacuously() -> None:
    report = check("", source="heritage", splice="hair")
    assert not report.satisfied


def test_an_inverted_band_is_refused() -> None:
    with pytest.raises(InvalidParams):
        check("Hairitage", source="heritage", splice="hair", min_distance=0.9, max_distance=0.1)


def test_an_unknown_parameter_is_refused() -> None:
    with pytest.raises(InvalidParams):
        check("Hairitage", source="heritage", splice="hair", blend=True)


# --- metrics and evidence ------------------------------------------------------


def test_metrics_report_what_the_verdict_was_computed_from() -> None:
    report = check("Hairitage", source="heritage", splice="hair")
    assert report.metrics["distance"] == 0.0
    assert 0.0 <= report.metrics["host_distance"] <= 1.0


def test_evidence_names_the_window_of_the_host_that_was_matched() -> None:
    report = check("Hairitage", source="heritage", splice="hair")
    assert report.evidence
    assert all(item.basis == "dictionary" for item in report.evidence)


def test_each_violating_strategy_case_trips_the_rule_it_names() -> None:
    """The strategy file records a rule per case; nothing else reads it.

    `test_strategies.py` asserts only that a violating case is unsatisfied, which
    a case failing for the wrong reason passes just as well.
    """
    from strategies.portmanteau import VIOLATING

    for text, params, expected in VIOLATING:
        report = check(text, **params)
        assert not report.satisfied, f"{text!r} should not satisfy"
        assert expected in rules(report), (
            f"{text!r} was meant to trip {expected!r}, but tripped {rules(report)}"
        )
    assert len({rule for *_, rule in VIOLATING}) == len(VIOLATING)


def test_the_equivalence_fold_changes_no_existing_verdict() -> None:
    """German coda-r folding was added for `Haarmonie` and must not quietly
    re-read work already checked. Measured against the pairs the German fixtures
    and domain phrases actually turn on.
    """
    from denckring.core.phonetics import bare_phonemes, phoneme_distance
    from denckring.lang import get_pack

    pack = get_pack("de")
    pairs = [
        ("Kamm", "Komm"),
        ("Haar", "klar"),
        ("Welle", "Welt"),
        ("Locke", "Liebe"),
        ("Zopf", "Kopf"),
        ("Glanz", "Ganz"),
        ("Föhn", "schön"),
        ("Kur", "Nur"),
        ("Locke", "Locker"),
    ]
    for left, right in pairs:
        a = bare_phonemes(pack.phonemes(left))
        b = bare_phonemes(pack.phonemes(right))
        assert phoneme_distance(a, b) == phoneme_distance(a, b, "de"), (
            f"folding moved {left}/{right}, which it was measured not to"
        )


def test_a_word_that_already_contains_another_is_not_a_blend() -> None:
    """`Crustacean` really does contain `crust`, and `Sightseeing` contains
    `sight` — and both passed an earlier draft at a spelling distance of 0.000,
    because nothing had been spliced. That is the *found* pun, which states no
    relation between two texts because it is one text. Found in the data while
    authoring blends, not by reasoning about the code."""
    for text, splice in (("Crustacean", "crust"), ("Sightseeing", "sight")):
        report = check(text, source=text, splice=splice)
        assert not report.satisfied
        assert "identical_to_host" in rules(report)


def test_apply_makes_blends_its_own_checker_accepts() -> None:
    """The round trip, run here because `portmanteau` is parameter-gated in
    `test_round_trip.py`: the fuzz harness supplies no trade, and without one
    there is nothing to splice in."""
    from denckring import produce

    hosts: list[tuple[str, Lang]] = [("Harmonie", "de"), ("airport", "en"), ("coiffure", "fr")]
    for host, lang in hosts:
        production = produce("portmanteau", host, lang=lang, domain="hair", max_results=5)
        assert production.candidates
        for candidate in production.candidates:
            assert candidate.text.casefold() != host.casefold()


def test_the_generator_finds_the_attested_name_first_for_most_hosts() -> None:
    """The measured claim, pinned so it cannot quietly rot.

    Ten of twelve attested hosts return the real salon name first. The two that
    do not are named — this is a floor on a measurement, not a guess, and ADR
    0043 records the three ranking changes that were tried and made it worse.
    """
    from denckring import produce

    cases: list[tuple[str, Lang, str]] = [
        ("Harmonie", "de", "Haarmonie"),
        ("Kamille", "de", "Kammille"),
        ("Kambodscha", "de", "Kammbodscha"),
        ("Sahara", "de", "SaHaara"),
        ("Harlekin", "de", "Haarlekin"),
        ("Hawaii", "de", "Haarwaii"),
        ("heritage", "en", "Hairitage"),
        ("airport", "en", "Hairport"),
        ("heirloom", "en", "Hairloom"),
        ("comfort", "en", "Combfort"),
        ("paraphernalia", "en", "Hairaphernalia"),
        ("Chamäleon", "de", "Kammäleon"),
    ]
    first = 0
    for host, lang, wanted in cases:
        texts = produce("portmanteau", host, lang=lang, domain="hair", max_results=40).texts
        folded = [t.casefold() for t in texts]
        if folded and folded[0] == wanted.casefold():
            first += 1
    assert first >= 10, f"the attested name came first for only {first} of {len(cases)} hosts"


def test_the_known_weakness_is_still_the_known_weakness() -> None:
    """`Chamäleon` returns `ChKammäleon` ahead of `Kammäleon` — a seam stutter
    that keeps more of the host and so wins on recoverability.

    Asserted so that a future ranking change has to look at it. If this starts
    failing because `Kammäleon` now comes first, that is a *fix*: delete the test
    and say so in the ADR, rather than leaving a note about a problem that has
    gone away.
    """
    from denckring import produce

    texts = produce("portmanteau", "Chamäleon", lang="de", domain="hair", max_results=40).texts
    assert "Kammäleon" in texts, "the real name should at least be found"
    assert texts[0] != "Kammäleon", (
        "the documented weakness no longer fires; delete this test and update ADR 0043"
    )
