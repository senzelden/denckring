"""The corpus figures ADR 0037 argues from, pinned so they cannot drift.

Every decision in the spec rests on a measured yield, and a yield moves when a
data package is rebuilt. These assert the numbers rather than trusting the
prose, with a tolerance tight enough to notice a real change while absorbing a
lexicon revision of a word or two.
"""

import pytest

from denckring.core.calculator import ALPHABET
from denckring.lang import get_pack


def _corpus(lang: str) -> list[str]:
    """The enumerable word source for a pack: graded words where it has them,
    the noun list otherwise. Mirrors what `_produce` does — ADR 0037 D5."""
    pack = get_pack(lang)
    if "lexicon.graded_words" in pack.capabilities:
        return list(pack.graded_words())
    return list(pack.nouns())


def test_german_has_no_graded_words_which_is_why_apply_floors_on_nouns() -> None:
    """The premise D5 rests on.

    SCOWL is vendored into `denckring-en-data` alone (ADR 0028); French got its
    own in chapter 6; German never has. Declaring `lexicon.graded_words` on this
    row would therefore make German `apply` fail — in the language of the row's
    own example — and emit the misleading remedy fixed on 2026-09-04. If this
    ever becomes false, D5 is free to be simplified, and this is how anyone
    finds out.
    """
    assert "lexicon.graded_words" not in get_pack("de").capabilities
    assert "lexicon.graded_words" in get_pack("en").capabilities
    assert "lexicon.graded_words" in get_pack("fr").capabilities
    assert "lexicon.nouns" in get_pack("de").capabilities


@pytest.mark.parametrize(("lang", "expected"), [("en", 304), ("de", 216), ("fr", 207)])
def test_the_corpus_yield_is_what_the_adr_claims(lang: str, expected: int) -> None:
    """Measured 2026-09-04. If this fails, do not widen the tolerance — find
    what moved and correct the ADR, because these numbers are its argument."""
    found = sum(1 for word in _corpus(lang) if word and set(word.lower()) <= ALPHABET)
    assert abs(found - expected) <= 5, f"{lang}: {found}, ADR 0037 says {expected}"


def test_refusing_the_folk_table_is_what_costs_half_the_corpus() -> None:
    """D2's stated cost, so it stays visible.

    Adding `2 -> Z` and `2 -> R` roughly doubles the corpus in every language,
    which makes the refusal look like an oversight rather than a decision. This
    fails if anyone widens the table, which is the point: D2 is meant to be
    reopened deliberately, not drifted into.
    """
    widened = ALPHABET | {"z", "r"}
    for lang, expected in (("en", 643), ("de", 652), ("fr", 631)):
        found = sum(1 for word in _corpus(lang) if word and set(word.lower()) <= widened)
        assert abs(found - expected) <= 15, f"{lang}: {found}, ADR 0037 says {expected}"
