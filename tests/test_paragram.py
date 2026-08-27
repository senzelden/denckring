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


def test_it_returns_more_than_one_candidate() -> None:
    """The search already found these and the old return type discarded them."""
    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    produced = procedure.produce("The cat is great.")
    assert len(produced.texts) > 1
    assert len(set(produced.texts)) == len(produced.texts), "candidates must be distinct"


def test_the_best_is_still_first() -> None:
    """`apply`'s result must not move: it is the same winner, now with the
    runners-up behind it rather than thrown away."""
    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    assert procedure.produce("The cat is great.").texts[0] == "The cat is great treat."


def _swapped_word(source: str, candidate: str) -> str:
    """The word `_produce` inserted, recovered from the text it inserted it into.

    `_produce` returns `text[:end] + " " + swapped + text[end:]`, so the candidate
    is the source with one `" " + swapped` spliced in at a word end. Walking the
    splice points and taking the one whose inserted slice is a space followed by
    letters is exact, where stripping the common prefix and suffix is not: a
    swapped word sharing letters with what follows it slides the apparent
    boundary, and `great`/`greet` in this very fixture does exactly that.
    """
    width = len(candidate) - len(source)
    for cut in range(len(source) + 1):
        if candidate[:cut] != source[:cut] or candidate[cut + width :] != source[cut:]:
            continue
        inserted = candidate[cut : cut + width]
        if inserted.startswith(" ") and inserted[1:].isalpha():
            return inserted[1:]
    raise AssertionError(f"no single-word insertion turns {source!r} into {candidate!r}")


def test_the_order_is_the_score_it_already_computed() -> None:
    """`CandidateScore` is `(pronounced, is_noun, length)` and totally ordered,
    and `texts` must be sorted by it, best first.

    This used to assert only that two identical calls agree, which is true of any
    deterministic implementation and would hold with the sort key reversed. Here
    each candidate's score is rebuilt from the word it inserted — the same three
    components `_produce` computed — and the sequence must be non-increasing.
    The two-calls-agree assertion stays as what it always was: the stability half,
    which is what keeps equal scores in the order the search walked them in.
    """
    from denckring.lang import get_pack

    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    source = "The cat is great."
    texts = procedure.produce(source, max_results=100).texts
    assert len(texts) > 1, "one candidate cannot demonstrate an order"

    pack = get_pack("en")
    scores = []
    for candidate in texts:
        swapped = _swapped_word(source, candidate)
        assert pack.is_word(swapped), f"{swapped!r} is not the inserted word"
        scores.append(
            (pack.syllable_count(swapped)[1], pack.noun_index(swapped) is not None, len(swapped))
        )
    assert scores == sorted(scores, reverse=True), f"texts are not in score order: {scores}"

    assert texts == procedure.produce(source, max_results=100).texts


def test_max_results_caps_and_says_so() -> None:
    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    produced = procedure.produce("The cat is great.", max_results=2)
    assert len(produced.texts) == 2
    assert produced.truncated is True


def test_apply_raises_when_no_swap_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """A wordless text gives the search nothing to work with; refusing beats
    returning text with no swap in it, which `check` would then reject."""
    from denckring.core.errors import NoCandidateWord

    procedure = get("paragram")
    assert isinstance(procedure, Constructive)
    with pytest.raises(NoCandidateWord):
        procedure.apply("   ", lang="en")
