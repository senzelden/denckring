"""The shipped trades: what a shop sells, and the phrases its puns are made on.

These files are data with a claim attached — that a pun for this trade, in this
language, actually lands. The tests below hold them to it, because a domain
that produced nothing would be a scene's worth of furniture and no procedure.
"""

from __future__ import annotations

import pytest

from denckring import produce
from denckring.core import domain as domains
from denckring.core.errors import InvalidParams
from denckring.core.protocol import Lang

#: Every language the catalogue knows. Typed once here rather than narrowed at
#: each use, which is what an earlier draft did with a `type: ignore` that mypy
#: then reported as unnecessary — the literal tuple is already `Lang`.
LANGS: tuple[Lang, ...] = ("en", "de", "fr")


def test_the_shipped_trades_are_the_ones_named() -> None:
    assert domains.ids() == (
        "bakery",
        "bar",
        "butcher",
        "coffee",
        "fishmonger",
        "florist",
        "hair",
        "nails",
        "optician",
        "pets",
    )


@pytest.mark.parametrize("domain_id", domains.ids())
def test_every_trade_names_itself_in_every_language_it_speaks(domain_id: str) -> None:
    trade = domains.load(domain_id)
    assert trade.id == domain_id
    assert trade.source.strip()
    for lang in trade.languages:
        assert lang in trade.names, f"{domain_id} speaks {lang} but does not name itself in it"


@pytest.mark.parametrize("domain_id", domains.ids())
def test_a_trade_is_not_padded_into_a_language_it_has_nothing_for(domain_id: str) -> None:
    """`speaks` is the honest answer, and empty tuples are the fallback.

    `optician` ships English only and `bakery` dropped German on purpose. A
    trade must never answer with a language whose lists are empty, because a
    caller reads that as "this works here".
    """
    trade = domains.load(domain_id)
    for typed in LANGS:
        if trade.speaks(typed):
            # Vocabulary, which is what the procedures read. Phrases are optional
            # since the corpus landed — see `TradeWords.phrases`.
            assert trade.words(typed)
        else:
            assert trade.words(typed) == () and trade.phrases(typed) == ()


def test_an_unknown_trade_is_a_bad_argument_not_a_missing_file() -> None:
    with pytest.raises(InvalidParams) as caught:
        produce("paronomasia", "Brad Pitt", lang="en", domain="greengrocer")
    assert "greengrocer" in str(caught.value)
    assert "bakery" in str(caught.value), "the error should say what could have been said instead"


def _cases() -> list[tuple[str, str, str]]:
    out = []
    for domain_id in domains.ids():
        trade = domains.load(domain_id)
        for lang in trade.languages:
            for phrase in trade.phrases(lang):  # type: ignore[arg-type]
                out.append((domain_id, lang, phrase))
    return out


@pytest.mark.parametrize(("domain_id", "lang", "phrase"), _cases())
def test_every_shipped_phrase_displaces_onto_its_own_trade(
    domain_id: str, lang: str, phrase: str
) -> None:
    """The claim each phrase makes, checked one phrase at a time.

    Not "the generator returns something" — it nearly always does — but that
    the *best* thing it returns is a word of this trade. Three drafts failed
    here for two distinct reasons worth keeping: a phrase that already
    contained its own trade word had nothing left to displace (`Curl up and
    die`, `Das Brot`), and a phrase whose only near neighbour was an inflection
    of a word already present displaced onto morphology rather than a pun
    (`Combing the Desert` -> `Combing the Deserts`, `Look Sharp` -> `Look
    Sharper`). Both are invisible to a test that only asks whether output
    exists.
    """
    typed: Lang = lang  # type: ignore[assignment]
    best = produce("paronomasia", phrase, lang=typed, domain=domain_id, max_results=1).candidates[0]
    assert best.metrics["in_trade"] == 1.0, (
        f"{phrase!r} for a {domain_id} in {lang} came back as {best.text!r}, "
        f"which is not a word of the trade"
    )


@pytest.mark.parametrize(("domain_id", "lang", "phrase"), _cases())
def test_every_shipped_phrase_produces_a_sign_its_own_checker_accepts(
    domain_id: str, lang: str, phrase: str
) -> None:
    from denckring import check

    typed: Lang = lang  # type: ignore[assignment]
    text = produce("paronomasia", phrase, lang=typed, domain=domain_id, max_results=1).texts[0]
    assert check("paronomasia", text, lang=typed, source=phrase).satisfied


def test_a_german_noun_keeps_its_capital_on_the_sign() -> None:
    """German's graded words are an entirely lower-case frequency corpus, so a
    displacement rendered as that list spells it reads `Alles haar`. The domain
    file is the spelling authority precisely so it does not."""
    text = produce("paronomasia", "Alles klar", lang="de", domain="hair", max_results=1).texts[0]
    assert text == "Alles Haar"


def test_the_displaced_words_own_case_still_applies() -> None:
    """The trade spells `bread`; the phrase capitalises it."""
    assert produce("paronomasia", "Brad Pitt", lang="en", domain="bakery").texts[0] == "Bread Pitt"


def test_a_trade_word_beats_a_closer_word_from_outside_it() -> None:
    """The whole point of ranking the trade first.

    `pit` is an exact homophone of `Pitt` and wins on sound alone; `bread` is
    0.250 away. With a bakery to fill, `bread` must still come first.
    """
    plain = produce("paronomasia", "Brad Pitt", lang="en", max_results=1).candidates[0]
    baked = produce("paronomasia", "Brad Pitt", lang="en", domain="bakery", max_results=1)
    assert plain.metrics["distance"] < baked.candidates[0].metrics["distance"]
    assert baked.texts[0] == "Bread Pitt"


def test_closest_beats_commonest_now_that_the_key_is_the_right_way_round() -> None:
    """The defect this ordering replaced: `bread` is SCOWL band 20 while `brand`,
    `bad`, `it` and `put` are band 10, so ranking by commonness first buried
    `Bread Pitt` at position 74 behind `Brad It`. Asserted as the rule — every
    candidate is at least as close as the one after it — not as a fixed list."""
    candidates = produce("paronomasia", "Brad Pitt", lang="en", max_results=40).candidates
    distances = [c.metrics["distance"] for c in candidates]
    assert distances == sorted(distances)


def test_a_vocabulary_of_your_own_ranks_the_same_way() -> None:
    """`domain_words` without a shipped trade, for a shop nobody catalogued."""
    text = produce(
        "paronomasia", "Brad Pitt", lang="en", domain_words=["thread", "spool"], max_results=1
    ).texts[0]
    assert text == "Thread Pitt"
