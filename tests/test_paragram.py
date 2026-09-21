import time

import pytest

from denckring import check
from denckring.core.errors import MissingCapability
from denckring.core.protocol import Constructive
from denckring.core.registry import get
from denckring.procedures.paragram import Paragram, _count_pairs


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


def test_a_common_swap_outranks_a_rare_one() -> None:
    """The ordering among equally-scoring candidates was the search's own —
    alphabetical — so `bight` (SCOWL band 50) came back ahead of `light`,
    `might` and `fight` (band 10). All five are five letters, all are in the
    pronouncing dictionary and none is a noun, so the first three score
    elements tie and the fourth is what separates them.

    `lexicon.graded_words` is read only when the pack declares it. It is not on
    `apply_requires`, because refusing to generate on a core-only install would
    trade a working procedure for a nicety.
    """
    from denckring import produce

    texts = produce("paragram", "silent night holy night", lang="en", max_results=40).texts
    swapped = [t.split()[2] for t in texts]
    # Not dropped — ranked. `max_results=40` is wide enough to see it at all:
    # at the default 10 the band-10 swaps fill the list and `bight` never
    # appears, which is the improvement rather than a filter.
    assert "bight" in swapped
    for common in ("light", "might", "fight", "eight"):
        assert swapped.index(common) < swapped.index("bight"), common


def test_a_word_the_table_does_not_know_ranks_mid_not_best() -> None:
    """`dat` is absent from the graded list and `bat` is band 20. Absent must
    not read as commonest — the same mid-band default `calculator_word` chose."""
    from denckring import produce

    texts = produce("paragram", "a small cat sat on the mat", lang="en", max_results=12).texts
    swapped = [t.split()[3] for t in texts]
    if "dat" in swapped and "bat" in swapped:
        assert swapped.index("bat") < swapped.index("dat")


def _differ_by_one(left: str, right: str) -> bool:
    """Equal length, differing at exactly one position.

    Used to be `paragram.differ_by_one` — public, undocumented-as-such
    production code (no leading underscore, a docstring that read as API).
    The O(U*L) rewrite (`_count_pairs`) removed its only production caller;
    it has survived since only as this file's equivalence oracle. Moved
    here rather than left behind with a "kept as reference implementation"
    docstring, because nothing outside this test exercises it, imports it,
    or benefits from it being importable — a test helper that only a test
    uses belongs in the test (issue #18 item 1: checked first that nothing
    else imports it)."""
    if len(left) != len(right) or left == right:
        return False
    return sum(a != b for a, b in zip(left, right, strict=True)) == 1


def _reference_pair_count(words: list[str]) -> int:
    """The old O(U^2 * L) algorithm, kept here only as an equivalence oracle."""
    from itertools import combinations

    return sum(
        1 for left, right in combinations(sorted(set(words)), 2) if _differ_by_one(left, right)
    )


def test_count_pairs_agrees_with_the_reference_on_small_corpora() -> None:
    import random

    rng = random.Random(7)
    alphabet = "abcdefg"
    for _ in range(200):
        size = rng.randint(0, 30)
        length = rng.randint(1, 5)
        words = ["".join(rng.choice(alphabet) for _ in range(length)) for _ in range(size)]
        assert _count_pairs(words) == _reference_pair_count(words), words


def test_count_pairs_is_not_quadratic() -> None:
    """P1-02: 10,000 unique 5-letter words must count in well under a second,
    not the tens of seconds the O(U^2) scan took at this size."""
    words = [f"{i:05d}".translate(str.maketrans("0123456789", "abcdefghij")) for i in range(10_000)]
    assert len(set(words)) == 10_000
    start = time.monotonic()
    _count_pairs(words)
    elapsed = time.monotonic() - start
    assert elapsed < 2.0, f"took {elapsed:.2f}s — check the pair-counting algorithm is still O(U*L)"


def test_a_large_adversarial_text_checks_without_hanging() -> None:
    """The actual public entry point, not just the helper — MCP calls this."""
    procedure = Paragram()
    words = [f"{i:05d}".translate(str.maketrans("0123456789", "abcdefghij")) for i in range(5_000)]
    text = " ".join(words)
    start = time.monotonic()
    report = procedure.check(text)
    elapsed = time.monotonic() - start
    assert elapsed < 3.0, f"took {elapsed:.2f}s"
    assert report.metrics["pairs"] >= 0.0


def test_a_single_very_long_word_does_not_hang() -> None:
    """Fix round 1: the first version of `_count_pairs` rebuilt an O(length)
    wildcarded *string* per position instead of an O(1) hash combine, which is
    O(length^2) per word and invisible to every test above — they all fix
    word length at 5 and vary word *count*. This is the exact adversarial
    input the round-1 review reported hanging: one word, zero possible pairs,
    but the buggy version still took over a second on it — while the O(U^2*L)
    `combinations()` code this task originally replaced was instant, since a
    one-element set has no pairs to check at all.
    """
    start = time.monotonic()
    result = _count_pairs(["a" * 99_999 + "b"])
    elapsed = time.monotonic() - start
    assert result == 0
    assert elapsed < 1.0, f"took {elapsed:.2f}s — check for an O(length^2) regression"


def test_count_pairs_scales_with_word_length() -> None:
    """The word-length axis, which no test above exercises: word *count* is
    fixed low (20) and only *length* varies, so a quadratic-in-length
    regression shows up as a blow-up here even though it's invisible to
    `test_count_pairs_is_not_quadratic` (which fixes length at 5) and
    `test_a_large_adversarial_text_checks_without_hanging` (length 5 again).
    Doubling the length should cost roughly double, not roughly quadruple.
    """

    def _timed(length: int) -> float:
        words = [f"{i:04d}{'x' * (length - 4)}" for i in range(20)]
        start = time.monotonic()
        _count_pairs(words)
        return time.monotonic() - start

    small = _timed(2000)
    large = _timed(8000)
    assert large < max(small * 4, 1.0), (
        f"length 2000 took {small:.3f}s, length 8000 (4x longer) took "
        f"{large:.3f}s — that looks quadratic in word length, not linear"
    )
    # Generous, for the reason `test_a_realistic_long_document_checks_without_hanging`
    # gives: the ratio above is the rule, and an absolute wall-clock bound measures
    # the runner and its instrumentation as much as it measures the code.
    assert large < 30.0, f"took {large:.2f}s for 20 words of length 8000 — that is a hang"


def test_a_realistic_long_document_checks_without_hanging() -> None:
    """Mirrors the round-1 review's more realistic case: not one pathological
    word, but many long, unique ones — 300 unique 3000-character words is a
    plausible large document, not an extreme construction, and it hung for
    2.6s under the O(length^2) regression.

    The rule under test is that cost is linear in word length, so that is what
    is asserted: halving the length should roughly halve the work. An absolute
    wall-clock ceiling cannot express it, because the same correct code runs
    several times slower under the coverage job's instrumentation than it does
    on a bare local run — a 1.0s ceiling passed locally and failed CI at 1.69s
    while the implementation was right. A ratio is immune to that, because both
    measurements carry the same overhead; the generous ceiling below stays only
    to keep the literal promise in this test's name.
    """
    import random

    rng = random.Random(3)
    alphabet = "abcdefghij"

    def _timed(length: int) -> float:
        words = {"".join(rng.choice(alphabet) for _ in range(length)) for _ in range(300)}
        assert len(words) == 300
        listed = list(words)
        # The minimum of a few runs, not the mean: a shared CI runner adds time
        # to a sample, never removes it, so the fastest run is the least noisy
        # estimate of the work actually being done.
        return min(_elapsed(listed) for _ in range(3))

    def _elapsed(words: list[str]) -> float:
        start = time.monotonic()
        _count_pairs(words)
        return time.monotonic() - start

    half = _timed(1500)
    full = _timed(3000)
    assert full < half * 3, (
        f"300 words of length 1500 took {half:.3f}s, length 3000 (2x longer) took "
        f"{full:.3f}s — linear costs about 2x, quadratic about 4x, and this is neither"
    )
    assert full < 30.0, f"took {full:.2f}s for 300 unique 3000-char words — that is a hang"
