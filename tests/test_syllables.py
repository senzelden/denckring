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


# The `e` of a final `-es` or `-ed` after a consonant is the stem's silent `e`
# (`awake` -> `awakes`), so the heuristic drops it as it drops a final `e`. Not
# after a sibilant (`faces`, `wishes`) or `t`/`d` (`wanted`), where the suffix is
# its own syllable, nor after a consonant and a liquid (`tables`, `hundred`),
# which `_SYLLABIC_LE` already treats as a syllable of its own.
@pytest.mark.parametrize(
    ("word", "count"),
    [
        ("awakes", 2),
        ("hoped", 1),
        ("makes", 1),
        ("faced", 1),
        ("faces", 2),
        ("wishes", 2),
        ("boxes", 2),
        ("wanted", 2),
        ("added", 2),
        ("tables", 2),
        ("bubbled", 2),
        ("hundred", 2),
        ("covered", 2),
    ],
)
def test_the_heuristic_reads_a_suffixed_silent_e(word: str, count: int) -> None:
    assert CORE.syllable_count(word) == (count, False)


#: Measured on every alphabetic CMUdict word ending `-es`/`-ed`: 54% and 42%
#: agreement while only a final `e` was silent, 89% and 91% with the suffix rule.
SUFFIX_AGREEMENT = 0.85


@pytest.mark.parametrize("suffix", ["es", "ed"])
def test_the_heuristic_agrees_on_suffixed_words(suffix: str) -> None:
    data = pytest.importorskip("denckring_en_data")
    entries = data.pronunciations()
    words = [w for w in entries if w.isalpha() and w.endswith(suffix)]
    agreed = sum(
        CORE.syllable_count(w)[0] == sum(1 for p in entries[w] if p[-1].isdigit()) for w in words
    )
    assert agreed / len(words) >= SUFFIX_AGREEMENT


@pytest.mark.parametrize(
    ("word", "count"),
    [
        ("awakes", 2),  # awake + s
        ("cleanses", 2),  # cleanse + s, a sibilant: the suffix is a syllable
        ("paraphrases", 4),  # paraphrase + s
        ("synthesizes", 4),  # synthesize + s
        ("scythes", 1),  # scythe + s, DH is not a sibilant
    ],
)
def test_the_dictionary_pack_reads_a_plural_through_its_stem(word: str, count: int) -> None:
    """Missing from CMUdict, present as a stem: an estimate, but a good one.

    The probe line "The owl awakes and calls across the glen" read eleven
    syllables because `awakes` fell to the spelling heuristic (three).
    """
    data = pytest.importorskip("denckring_en_data")
    from denckring.lang import get_pack

    assert word not in data.pronunciations()
    assert get_pack("en").syllable_count(word) == (count, False)


def test_the_stem_fallback_agrees_with_the_dictionary_where_both_answer() -> None:
    """Measured on CMUdict's own plurals: 98.9% agreement, and 97.9% before
    `-ss` words (`boss`, `chess`) were kept from being read as `bos` + `s`."""
    data = pytest.importorskip("denckring_en_data")
    entries = data.pronunciations()
    tried = agreed = 0
    for word, phones in entries.items():
        if not word.isalpha():
            continue
        found = data._inflected_syllables(word)
        if found is None:
            continue
        tried += 1
        agreed += found[0] == sum(1 for p in phones if p[-1].isdigit())
    assert tried > 10_000
    assert agreed / tried >= 0.98


def test_the_haiku_probe_line_counts_ten() -> None:
    pytest.importorskip("denckring_en_data")
    report = check(
        "syllable_count", "The owl awakes and calls across the glen", pattern=[10], lang="en"
    )
    assert report.satisfied, report.violations
