"""The four generators added last: anagram, slenderizing, N+7 and S+7.

Each has a checker that predates it, so the bar is the one the round-trip
property already sets — whatever `apply` produces, its own `check` accepts.
These tests pin the parts that property cannot see: that the displacement
actually moves a noun rather than passing everything through, that
slenderizing removes the letter it was asked to remove, and that the anagram
generator uses the lexicon rather than shuffling.
"""

import pytest

from denckring.core.errors import MissingCapability
from denckring.core.protocol import Constructive
from denckring.core.registry import get
from denckring.lang import get_pack


def generator(procedure_id: str) -> Constructive:
    """`get` is typed as the base class, which has no `apply` — ADR 0002 keeps it
    off `BaseProcedure` because it is optional. Narrow once, here."""
    procedure = get(procedure_id)
    assert isinstance(procedure, Constructive), f"{procedure_id} has no apply()"
    return procedure


def test_all_four_now_generate() -> None:
    """The catalogue calls each of these constructive or both."""
    for procedure_id in ("anagram", "slenderizing", "n_plus_7", "s_plus_7"):
        assert isinstance(get(procedure_id), Constructive), f"{procedure_id} has no apply()"


# ── slenderizing ───────────────────────────────────────────────────────────


def test_slenderizing_removes_every_instance_of_the_letter() -> None:
    produced = generator("slenderizing").apply("the sunset settles", lang="en", deleted="s")
    assert "s" not in produced
    assert produced.replace(" ", "") == "theunetettle"


def test_slenderizing_output_satisfies_its_own_checker() -> None:
    source = "a stiff breeze"
    produced = generator("slenderizing").apply(source, lang="en", deleted="f")
    report = get("slenderizing").check(produced, lang="en", source=source, deleted="f")
    assert report.satisfied


# ── N+7 and S+7 ────────────────────────────────────────────────────────────


def test_displacement_actually_moves_a_noun() -> None:
    """A generator that changed nothing would still pass `check`, because the
    checker tolerates an unchanged noun as a possible verb. So assert movement."""
    pack = get_pack("en")
    produced = generator("n_plus_7").apply("the cat sleeps", lang="en")
    # Word-level, not substring: cat displaces to `catacomb`, which contains
    # "cat" — a naive `not in` check would call a correct displacement a failure.
    assert "cat" not in produced.split()
    expected = pack.nouns()[(pack.noun_index("cat") or 0) + 7]
    assert expected in produced.split()


def test_displacement_leaves_non_nouns_alone() -> None:
    produced = generator("n_plus_7").apply("the cat sleeps", lang="en")
    assert produced.startswith("the ")


def test_s_plus_7_honours_its_offset() -> None:
    pack = get_pack("en")
    index = pack.noun_index("cat") or 0
    for offset in (1, 3):
        produced = generator("s_plus_7").apply("the cat sleeps", lang="en", offset=offset)
        assert pack.nouns()[index + offset] in produced


def test_displacement_output_satisfies_its_own_checker() -> None:
    source = "the cat sat on the mat"
    for procedure_id in ("n_plus_7", "s_plus_7"):
        produced = generator(procedure_id).apply(source, lang="en")
        report = get(procedure_id).check(produced, lang="en", source=source)
        assert report.satisfied, f"{procedure_id}: {produced!r}"


def test_a_wordless_text_and_source_agree_vacuously() -> None:
    """Found by the round-trip property, not by hand: apply(" ") returns " ",
    and the checker called that unsatisfied while listing no violation — a
    verdict with nothing behind it."""
    report = get("n_plus_7").check(" ", lang="en", source=" ")
    assert report.satisfied
    assert not report.violations


def test_an_empty_candidate_still_fails_against_a_source_with_words() -> None:
    report = get("n_plus_7").check("", lang="en", source="the cat")
    assert not report.satisfied
    assert [v.rule for v in report.violations] == ["wrong_word_count"]


# ── anagram ────────────────────────────────────────────────────────────────


def test_anagram_uses_the_lexicon_rather_than_shuffling() -> None:
    """The point of the lexicon-backed generator: the result reads as words."""
    pack = get_pack("en")
    produced = generator("anagram").apply("listen carefully", lang="en")
    words = produced.split()
    assert words, "produced nothing"
    assert pack.is_word(words[0]), f"first word is not a word: {words[0]!r}"


def test_anagram_preserves_the_letter_multiset() -> None:
    source = "the quick brown fox"
    produced = generator("anagram").apply(source, lang="en")
    assert sorted(produced.replace(" ", "")) == sorted(source.replace(" ", ""))


def test_anagram_output_satisfies_its_own_checker() -> None:
    source = "silent night"
    produced = generator("anagram").apply(source, lang="en")
    report = get("anagram").check(produced, lang="en", source=source)
    assert report.satisfied, produced


def test_anagram_check_still_works_without_a_lexicon() -> None:
    """`requires` gates `check`, so adding lexicon.words there would have broken
    every core-only caller. The generator gates itself instead."""
    from denckring.lang.en import EnglishPack

    assert "lexicon.words" not in EnglishPack().capabilities
    report = get("anagram").check("tac", lang="en", source="cat")
    assert report.satisfied


def test_anagram_refuses_input_it_cannot_search() -> None:
    """A greedy walk over a paragraph is not an anagram anybody wants; refusing
    beats returning something the procedure could not really do."""
    from denckring.core.errors import InputTooLong

    with pytest.raises(InputTooLong):
        generator("anagram").apply("a" * 80, lang="en")


def test_anagram_apply_refuses_without_a_lexicon(monkeypatch: pytest.MonkeyPatch) -> None:
    from denckring.lang.en import EnglishPack

    monkeypatch.setattr("denckring.lang.get_pack", lambda lang="en": EnglishPack())
    with pytest.raises(MissingCapability):
        generator("anagram").apply("cat", lang="en")
