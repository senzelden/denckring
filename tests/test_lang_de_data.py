"""The German lexicon's own invariants.

Skipped in full when `denckring[de]` is not installed, exactly as the English
data tests skip without `denckring[en]`.
"""

import re

import pytest

de_data = pytest.importorskip("denckring_de_data")

SINGLE_TOKEN = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")


def test_noun_list_is_single_token_and_alphabetic() -> None:
    """ADR 0015's rule: N+7 walks this list and needs whole tokens."""
    nouns = de_data.noun_list()
    assert len(nouns) > 100_000
    offenders = [w for w in nouns if not SINGLE_TOKEN.fullmatch(w)]
    assert not offenders[:10], f"multi-token or non-alphabetic lemmas: {offenders[:10]}"


def test_noun_list_is_capitalised_as_german_nouns_are() -> None:
    nouns = de_data.noun_list()
    assert all(w[:1].isupper() for w in nouns[:1000])


def test_noun_list_is_in_dictionary_order() -> None:
    nouns = de_data.noun_list()
    assert list(nouns) == sorted(nouns)


def test_membership_covers_more_than_nouns() -> None:
    """A noun-only oracle would reject `singen` and `rot`."""
    known = de_data.known_words()
    assert "singen" in known
    assert "rot" in known
