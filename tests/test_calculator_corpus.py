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
    """The source ADR 0037 measured its figures against, named per language.

    Was "graded words where the pack has them, the noun list otherwise", which
    read as mirroring `_produce`. It did not: `calculator_word` never enumerates
    a corpus — it decodes digit partitions and asks `is_word` — and uses
    `graded_words` only to *rank*. The distinction went unnoticed while German
    had no graded words, and ADR 0038 gave it some, at which point the helper
    silently switched German from 184,040 nouns to 101,296 graded words and the
    pinned figures moved. Named explicitly now, so a future data chapter cannot
    move a figure by changing what some other pack happens to carry.
    """
    pack = get_pack(lang)
    if lang == "de":
        return list(pack.nouns())
    return list(pack.graded_words())


def test_apply_still_floors_on_the_capability_every_pack_meets() -> None:
    """D5's decision outlived its reason, and that is worth pinning.

    It floored `apply_requires` on `lexicon.nouns` because German had no
    `lexicon.graded_words` and a row demanding them could not generate in the
    language of its own example. ADR 0038 gave German graded words, so that
    reason is gone — and the decision is still right, because `lexicon.nouns` is
    the floor every pack meets and `apply_requires` should name what a row
    genuinely needs rather than the best thing available.

    This test is what noticed: it asserted German had no graded words, and went
    red the day German got some.
    """
    for lang in ("en", "de", "fr"):
        assert "lexicon.nouns" in get_pack(lang).capabilities
        assert "lexicon.graded_words" in get_pack(lang).capabilities


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
