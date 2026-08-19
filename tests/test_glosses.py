"""Definitions, and an honest answer when there are none."""

import pytest

from denckring.core.errors import MissingCapability
from denckring.lang import get_pack
from denckring.lang.en import EnglishPack


def test_a_pack_without_the_capability_raises() -> None:
    with pytest.raises(MissingCapability):
        EnglishPack().glosses("bank")


def test_every_sense_is_returned_not_just_the_first() -> None:
    """A writer replacing `bank` with the riverbank sense is doing the procedure
    correctly, so a checker accepting only the first sense rejects correct work."""
    found = get_pack("en").glosses("bank")
    assert len(found) > 1


def test_an_inflected_form_resolves_through_the_fallback() -> None:
    """`birds` strips its trailing `s` to `bird` (R5 keeps `s`/`es` stripping)."""
    found = get_pack("en").glosses("birds")
    assert found == get_pack("en").glosses("bird")
    assert any("bird" in gloss for gloss in found)


def test_an_ed_inflection_is_not_guessed_at_r5() -> None:
    """R5: `_inflections` tries only `s`/`es`, not `ed`/`ing`. `ed`/`ing` stripping
    was measured and dropped because it silently misresolves — `cared` strips to
    `car` and would surface automobile definitions for a text that never said
    `car`, which is worse than not resolving at all. This is the regression pin
    for that finding; it fails against the pre-R5 code, which returned the `car`
    glosses here instead of `()`."""
    assert get_pack("en").glosses("cared") == ()


def test_an_irregular_form_is_out_of_reach() -> None:
    """`went` needs irregular morphology — go -> went is not a plain inflection —
    so resolution cannot reach it and returns nothing rather than a guess."""
    assert get_pack("en").glosses("went") == ()


def test_an_unresolvable_word_returns_nothing_rather_than_guessing() -> None:
    """`flurbish` is not a word at all, in any inflection. Resolution tries it,
    its lemma, and the plain-inflection fallback, and all of them come up empty —
    the rows that consume this count such words and disclose them; none of them
    guess."""
    assert get_pack("en").glosses("flurbish") == ()
