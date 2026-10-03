"""The everyday-words view and N+7's readable dictionary (audit D1, D5).

denckring-bench filtered SCOWL's band 10 itself and kept a hand list of the junk
in it, and printed N+7's nouns from a list it rebuilt. `denckring.words` and
`denckring.nouns` are those views upstream. These tests hold them to the graded
table and the noun list they are views of, and to ADR 0051's exclusion list.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import get_args

import pytest

import denckring
from denckring import apply, nouns, words
from denckring.core.protocol import Lang
from denckring.lang import get_pack
from denckring.lang.base import BasePack, graded_view

LANGS: tuple[Lang, ...] = get_args(Lang)


def _excluded(lang: Lang) -> frozenset[str]:
    """The pack's exclusion list, an optional member the protocol does not name."""
    pack = get_pack(lang)
    assert isinstance(pack, BasePack)
    return pack.word_exclusions()


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("max_band", [None, 10, 35])
def test_words_is_the_graded_table_kept_to_the_band_and_ordered_commonest_first(
    lang: Lang, max_band: int | None
) -> None:
    pack = get_pack(lang)
    graded = pack.graded_words()
    excluded = _excluded(lang)
    found = words(lang, max_band=max_band)
    expected = {
        word
        for word, band in graded.items()
        if (max_band is None or band <= max_band) and word.isalpha() and word not in excluded
    }
    assert set(found) == expected
    assert len(found) == len(expected)
    keys = [(graded[word], word) for word in found]
    assert keys == sorted(keys)


@pytest.mark.parametrize("lang", LANGS)
def test_letters_only_drops_exactly_the_words_with_other_characters(lang: Lang) -> None:
    every = set(words(lang, max_band=10, letters_only=False))
    letters = set(words(lang, max_band=10))
    assert letters == {word for word in every if word.isalpha()}


def test_english_band_ten_is_cleared_of_the_junk_the_bench_listed() -> None:
    everyday = words("en", max_band=10)
    graded = get_pack("en").graded_words()
    for junk in ("payed", "numbest", "cs", "hes", "cums", "re"):
        assert graded[junk] == 10, f"{junk} is no longer band 10; review the list"
        assert junk not in everyday
    assert {"the", "cat", "pay", "paid", "numb"} <= set(everyday)


def test_every_exclusion_is_a_graded_word_the_view_would_otherwise_list() -> None:
    """A stale entry, one SCOWL no longer grades, fails here rather than lingering."""
    pack = get_pack("en")
    excluded = _excluded("en")
    assert excluded, "the English exclusion list did not load"
    graded = pack.graded_words()
    assert sorted(word for word in excluded if word not in graded) == []
    assert all(word.isalpha() and word.islower() for word in excluded)


def test_the_exclusions_touch_no_checker() -> None:
    """The graded table and `is_word` keep every excluded entry: the view alone moves."""
    pack = get_pack("en")
    assert all(word in pack.graded_words() for word in _excluded("en"))
    assert pack.is_word("re") is True


class _ProtocolPack:
    """A pack written to the protocol alone: graded words, and no `word_exclusions`."""

    def graded_words(self) -> Mapping[str, int]:
        return {"zebra": 20, "apple": 10, "pear": 10, "o'clock": 10, "junk": 10}


def test_a_pack_with_no_exclusion_list_gets_the_view_with_nothing_excluded() -> None:
    assert graded_view(_ProtocolPack()) == ("apple", "junk", "pear", "zebra")
    assert graded_view(_ProtocolPack(), 10, letters_only=False) == (
        "apple",
        "junk",
        "o'clock",
        "pear",
    )


def test_nouns_is_the_dictionary_n_plus_7_walks() -> None:
    """Unbanded, exactly the list N+7 reads by default, so a prompt can print it."""
    assert nouns("en") == tuple(get_pack("en").nouns())
    text = "the cat sat on the mat beside the house"
    supplied = list(nouns("en"))
    assert apply("n_plus_7", text) == apply("n_plus_7", text, dictionary=supplied)


@pytest.mark.parametrize("max_band", [10, 20])
def test_banded_nouns_are_the_everyday_ones_in_dictionary_order(max_band: int) -> None:
    banded = nouns("en", max_band=max_band)
    everyday = set(words("en", max_band=max_band, letters_only=False))
    dictionary = nouns("en")
    assert banded
    assert set(banded) == {noun for noun in dictionary if noun in everyday}
    order = {noun: index for index, noun in enumerate(dictionary)}
    assert [order[noun] for noun in banded] == sorted(order[noun] for noun in banded)
    assert "payed" not in banded


def test_the_views_are_published() -> None:
    assert {"words", "nouns"} <= set(denckring.__all__)
    assert "nouns(lang" in str(
        denckring.describe("n_plus_7").params["properties"]["dictionary"]["description"]
    )
