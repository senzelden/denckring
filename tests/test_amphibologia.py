"""`amphibologia` — the shop sign that alters nothing and still reads two ways.

The third shape of the punning shopfront. `paronomasia` displaces a word,
`portmanteau` splices one inside another, and here the phrase is left exactly as
it was: `A Cut Above` over a salon. What makes it a pun is the trade, so what is
checked is a relation between a text and a trade rather than between two texts.
"""

from __future__ import annotations

import pytest

from denckring import check as _check
from denckring.core.errors import InvalidParams
from denckring.core.protocol import Lang, Report


def check(text: str, *, lang: Lang = "en", **params: object) -> Report:
    return _check("amphibologia", text, lang=lang, **params)


def rules(report: Report) -> list[str]:
    return [violation.rule for violation in report.violations]


def test_a_cut_above_is_the_case_the_row_exists_for() -> None:
    report = check("A Cut Above", domain="hair")
    assert report.satisfied
    assert report.metrics["trade_words"] == 1.0
    assert report.metrics["senses"] > 1


def test_a_phrase_with_no_word_of_the_trade_says_nothing_doubtful() -> None:
    report = check("Nothing relevant here", domain="hair")
    assert not report.satisfied
    assert rules(report) == ["no_trade_word"]


def test_a_trade_word_with_one_sense_leaves_nothing_to_activate() -> None:
    """The whole test the row rests on. `xylophone` has exactly one sense in the
    lexicon, so a trade that sold them could put it on a sign and it would still
    mean only the one thing."""
    report = check("A xylophone above", domain_words=["xylophone"])
    assert not report.satisfied
    assert "unambiguous" in rules(report)


def test_the_ambiguity_floor_can_be_raised() -> None:
    """`dye` carries three senses; asking for more refuses it."""
    assert check("Curl Up and Dye", domain_words=["dye"]).satisfied
    assert not check("Curl Up and Dye", domain_words=["dye"], min_senses=40).satisfied


def test_a_row_about_a_trade_refuses_to_run_without_one() -> None:
    """Unlike `paronomasia`, there is no falling back on sound alone: with no
    trade there is no question to answer."""
    with pytest.raises(InvalidParams) as caught:
        check("A Cut Above")
    assert "domain" in str(caught.value)


def test_an_unknown_trade_is_a_bad_argument() -> None:
    with pytest.raises(InvalidParams) as caught:
        check("A Cut Above", domain="greengrocer")
    assert "bakery" in str(caught.value)


def test_an_unknown_parameter_is_refused() -> None:
    with pytest.raises(InvalidParams):
        check("A Cut Above", domain="hair", ambiguous=True)


def test_an_empty_text_does_not_score_one_vacuously() -> None:
    report = check("", domain="hair")
    assert not report.satisfied


def test_it_reads_the_other_languages_too() -> None:
    assert check("Der letzte Schnitt", lang="de", domain="hair").satisfied
    assert check("la coupe est pleine", lang="fr", domain="hair").satisfied


def test_evidence_says_how_many_senses_each_trade_word_carries() -> None:
    report = check("Curl Up and Dye", domain="hair")
    assert {item.subject for item in report.evidence} == {"Curl", "Dye"}
    assert all(item.basis == "dictionary" for item in report.evidence)


def test_apply_selects_the_phrases_that_read_two_ways() -> None:
    """The round trip, run here because `amphibologia` is parameter-gated: the
    fuzz harness supplies no trade."""
    from denckring import check as _c
    from denckring import produce

    corpus = "\n".join(
        [
            "A Cut Above",
            "Sheer Delight",
            "Nothing whatever to do with it",
            "Against the grain",
            "Head over heels",
            "Curl up with a book",
        ]
    )
    texts = produce("amphibologia", corpus, lang="en", domain="hair").texts
    assert texts
    for line in texts:
        assert _c("amphibologia", line, lang="en", domain="hair").satisfied
    assert "Nothing whatever to do with it" not in texts
    assert "Sheer Delight" not in texts, "`sheer` is not the trade's word; `shear` is"


def test_the_trade_decides_what_is_selected() -> None:
    from denckring import produce

    corpus = "A Cut Above\nAgainst the grain"
    assert produce("amphibologia", corpus, lang="en", domain="hair").texts == ["A Cut Above"]
    assert produce("amphibologia", corpus, lang="en", domain="bakery").texts == [
        "Against the grain"
    ]


def test_a_corpus_with_nothing_doubtful_says_so() -> None:
    from denckring import produce
    from denckring.core.errors import NoCandidateWord

    with pytest.raises(NoCandidateWord):
        produce("amphibologia", "Nothing here\nNor here", lang="en", domain="hair")
