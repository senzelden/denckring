"""The German pack composes three optional distributions.

`de` alone, plus frequency, plus Wiktionary, or all three — four combinations,
and `denckring_de_data.pack()` must name a class for each. Only the combination
this install actually has can be asserted through `get_pack`; the rest are
asserted on the classes themselves.
"""

import pytest

from denckring.lang import get_pack


def test_the_installed_german_pack_has_graded_words() -> None:
    assert "lexicon.graded_words" in get_pack("de").capabilities


def test_graded_words_is_a_read_only_view() -> None:
    """The module function is `lru_cache`d and shared by every caller in the
    process, so handing the dict out would let one caller's mutation corrupt it
    for all the others. English and French return `MappingProxyType` for this."""
    table = get_pack("de").graded_words()
    with pytest.raises(TypeError):
        table["esel"] = 1  # type: ignore[index]


def test_every_combination_declares_what_it_carries() -> None:
    from denckring_de_data import GermanDataPack
    from denckring_de_frequency import GermanFrequencyPack, GermanWiktionaryFrequencyPack
    from denckring_de_wiktionary import GermanWiktionaryPack

    assert "lexicon.graded_words" not in GermanDataPack.capabilities
    assert "lexicon.graded_words" not in GermanWiktionaryPack.capabilities
    assert "lexicon.graded_words" in GermanFrequencyPack.capabilities
    assert "lexicon.graded_words" in GermanWiktionaryFrequencyPack.capabilities
    # The richest carries both distributions' capabilities, not one of them.
    assert "stress" in GermanWiktionaryFrequencyPack.capabilities
    assert "lexicon.nouns" in GermanFrequencyPack.capabilities
    # And the lexical floor is inherited rather than restated.
    assert GermanDataPack.capabilities < GermanFrequencyPack.capabilities


def test_anagram_generates_in_german() -> None:
    """The point of the whole chapter. `Lebensmittel` has a genuine single-word
    anagram, which is the case worth naming."""
    from denckring import apply, check

    text = apply("anagram", "Lebensmittel", lang="de")
    assert check("anagram", text, lang="de", source="Lebensmittel").satisfied


def test_german_anagram_no_longer_refuses() -> None:
    """It raised `MissingCapability` naming `lexicon.graded_words` until this
    chapter. ADR 0028 is still true — SCOWL ships in denckring-en-data alone —
    and German simply no longer needs it."""
    from denckring import produce

    assert produce("anagram", "Taschenrechner", lang="de", max_results=3).texts
