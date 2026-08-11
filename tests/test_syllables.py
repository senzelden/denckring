"""Syllable counting, and the honesty of the heuristic."""

import pytest

from denckring import check
from denckring.lang.base import SYLLABLES_DICTIONARY, SYLLABLES_HEURISTIC
from denckring.lang.en import EnglishPack

CORE = EnglishPack()

#: Below this the heuristic is not worth shipping; a change that makes it worse
#: fails the build rather than degrading quietly.
MINIMUM_AGREEMENT = 0.80


def test_core_english_declares_only_the_heuristic() -> None:
    assert SYLLABLES_HEURISTIC in CORE.capabilities
    assert SYLLABLES_DICTIONARY not in CORE.capabilities


def test_the_heuristic_never_claims_to_be_exact() -> None:
    for word in ("haiku", "water", "cat", "zzzq"):
        _, exact = CORE.syllable_count(word)
        assert exact is False


def test_the_heuristic_never_returns_less_than_one_for_a_word() -> None:
    for word in ("a", "rhythm", "strength"):
        count, _ = CORE.syllable_count(word)
        assert count >= 1


def test_an_empty_string_has_no_syllables() -> None:
    assert CORE.syllable_count("") == (0, False)


def test_syllabic_reports_say_how_much_was_estimated() -> None:
    report = check("haiku", "an old silent pond\na frog jumps into the pond\nsplash silence again")
    assert "estimated_words" in report.metrics


def test_the_heuristic_agrees_with_the_dictionary_often_enough() -> None:
    """Measured, not asserted in prose."""
    data = pytest.importorskip("denckring_en_data")
    entries = data.pronunciations()
    sample = sorted(entries)[::200]
    agreed = 0
    for word in sample:
        exact = sum(1 for phone in entries[word] if phone[-1].isdigit())
        estimate, _ = CORE.syllable_count(word)
        if estimate == exact:
            agreed += 1
    agreement = agreed / len(sample)
    assert agreement >= MINIMUM_AGREEMENT, (
        f"heuristic agrees with the dictionary on {agreement:.1%} of {len(sample)} words, "
        f"below the {MINIMUM_AGREEMENT:.0%} floor"
    )


def test_the_dictionary_pack_is_exact_where_it_knows_the_word() -> None:
    pytest.importorskip("denckring_en_data")
    from denckring.lang import get_pack

    pack = get_pack("en")
    assert SYLLABLES_DICTIONARY in pack.capabilities
    assert pack.syllable_count("antidisestablishmentarianism") == (12, True)


def test_the_dictionary_pack_falls_back_visibly_for_unknown_words() -> None:
    pytest.importorskip("denckring_en_data")
    from denckring.lang import get_pack

    count, exact = get_pack("en").syllable_count("zzzunknowncoinage")
    assert exact is False
    assert count >= 1
