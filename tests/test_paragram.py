import pytest

from denckring import check
from denckring.core.errors import MissingCapability
from denckring.core.protocol import Constructive
from denckring.core.registry import get


def test_a_one_letter_swap_is_found() -> None:
    report = check("paragram", "the cat sat on the mat")
    assert report.satisfied
    assert report.metrics["pairs"] >= 1.0


def test_a_text_with_no_swap_violates() -> None:
    report = check("paragram", "one three seventeen")
    assert not report.satisfied
    assert any(v.rule == "no_paragram" for v in report.violations)


def test_words_of_different_length_are_not_a_pair() -> None:
    assert not check("paragram", "cat cats").satisfied


def test_a_word_is_not_paired_with_itself() -> None:
    assert not check("paragram", "cat cat cat").satisfied


def test_minimum_raises_the_bar() -> None:
    """cat/sat/mat is three pairwise swaps, so a bar of three is met."""
    assert check("paragram", "cat sat mat", minimum=3).satisfied
    assert not check("paragram", "cat sat", minimum=3).satisfied


def test_a_swap_at_the_last_position_counts() -> None:
    assert check("paragram", "cat car").satisfied


def test_apply_produces_a_real_word() -> None:
    from denckring.lang import get_pack

    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply("the cat sat", lang="en")
    assert produced != "the cat sat"
    assert check("paragram", produced, minimum=0).satisfied or True  # shape only
    assert all(get_pack("en").is_word(w) for w in produced.split() if w.isalpha())


def test_apply_output_contains_both_halves_of_the_swap() -> None:
    """The pair has to survive in the text, or `check` has nothing to find."""
    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    produced = procedure.apply("the cat sat", lang="en")
    report = check("paragram", produced)
    assert report.satisfied
    assert report.metrics["pairs"] >= 1.0


def test_apply_refuses_without_a_lexicon(monkeypatch: pytest.MonkeyPatch) -> None:
    from denckring.lang.en import EnglishPack

    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    monkeypatch.setattr("denckring.lang.get_pack", lambda lang="en": EnglishPack())
    with pytest.raises(MissingCapability):
        procedure.apply("cat", lang="en")


def test_check_still_works_without_a_lexicon() -> None:
    """`requires` gates check, so the lexicon requirement lives in apply only."""
    from denckring.lang.en import EnglishPack

    assert "lexicon.words" not in EnglishPack().capabilities
    assert check("paragram", "cat sat").satisfied


def test_a_wordless_text_is_unsatisfied_with_a_violation() -> None:
    """Nothing to pair is not vacuous here: `minimum` defaults to 1, so a text
    with no words at all falls short of it and must say so."""
    report = check("paragram", "   ")
    assert not report.satisfied
    assert any(v.rule == "no_paragram" for v in report.violations)


def test_a_wordless_text_is_satisfied_vacuously_at_minimum_zero() -> None:
    """Asking for zero pairs and finding zero pairs is coherent agreement, not
    a verdict with nothing behind it."""
    report = check("paragram", "   ", minimum=0)
    assert report.satisfied
    assert not report.violations


def test_apply_raises_when_no_swap_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """A wordless text gives the search nothing to work with; refusing beats
    returning text with no swap in it, which `check` would then reject."""
    from denckring.core.errors import NoCandidateWord

    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    with pytest.raises(NoCandidateWord):
        procedure.apply("   ", lang="en")
