import pytest

from denckring import check
from denckring.core.errors import InvalidParams
from denckring.procedures.anagram import Anagram


def test_a_true_anagram_is_satisfied() -> None:
    assert check("anagram", "silent", source="listen").satisfied


def test_a_different_letter_multiset_is_not_satisfied() -> None:
    assert not check("anagram", "silence", source="listen").satisfied


def test_spacing_and_case_are_ignored() -> None:
    assert check("anagram", "Enlist!", source="listen").satisfied


def test_surplus_and_missing_letters_are_both_reported() -> None:
    report = check("anagram", "listenx", source="listen")
    assert {v.rule for v in report.violations} == {"surplus_letter"}


def test_missing_source_is_an_invalid_params_error() -> None:
    with pytest.raises(InvalidParams):
        check("anagram", "silent")


def test_dormitory_yields_dirty_room_and_ranks_it_above_the_junk() -> None:
    """The assertion the chapter exists to make true.

    `room dirty` was always reachable — it is one of sixty-five two-word covers
    over the old oracle — and the search was never the problem. What was missing
    was any way to tell it from `morty dior`, which the old oracle rated equally.

    Asserts the spec's claim and not a stronger one: present, and ranked above
    the named junk cover. Demanding it rank strictly first would fail if some
    third cover's least-common word were commoner than `dirty`, which would not
    make the ranking wrong.
    """
    texts = Anagram().produce("dormitory", lang="en", max_results=100).texts
    famous = {"room dirty", "dirty room"}
    assert famous & set(texts), f"the famous cover is unreachable: {texts[:10]}"
    junk = [t for t in texts if set(t.split()) == {"morty", "dior"}]
    if junk:
        best = min(texts.index(t) for t in famous & set(texts))
        assert best < texts.index(junk[0]), "ranked a surname cover above the famous one"


def test_astronomer_no_longer_returns_itself() -> None:
    """The reported defect. `astronomer` is a noun, so under a noun-only search
    it was the longest cover of its own letters and the guard refused it."""
    assert Anagram().apply("astronomer", lang="en") != "astronomer"


def test_every_cover_uses_exactly_the_source_letters() -> None:
    """The round-trip property in miniature, pinned at row level: the search may
    reorder and rank, but it may never lose or invent a letter."""
    procedure = Anagram()
    for candidate in procedure.produce("dormitory", lang="en").texts:
        assert procedure.check(candidate, lang="en", source="dormitory").satisfied


def test_candidates_carry_the_band_they_were_ranked_by() -> None:
    """The concrete use ADR 0027 exists for. Without it the order is an assertion
    the caller has to take on trust."""
    for candidate in Anagram().produce("dormitory", lang="en").candidates:
        assert "max_band" in candidate.metrics
        assert candidate.metrics["words"] == float(len(candidate.text.split()))


def test_the_ranking_keys_are_in_the_order_the_spec_names() -> None:
    """Fewest words first, then lowest maximum band. Asserted as the sort key
    rather than by naming winners, so it keeps holding when the lexicon changes."""
    candidates = Anagram().produce("dormitory", lang="en").candidates
    keys = [(c.metrics["words"], c.metrics["max_band"]) for c in candidates]
    assert keys == sorted(keys)


def test_the_node_budget_truncates_deterministically() -> None:
    """A wall-clock budget would make this machine-dependent, and the row is
    `deterministic: true`. Two runs at the same budget must agree exactly,
    including about having stopped early."""
    first = Anagram().produce("astronomer", lang="en", max_nodes=500)
    second = Anagram().produce("astronomer", lang="en", max_nodes=500)
    assert first.texts == second.texts
    assert first.truncated == second.truncated


def test_min_word_length_refuses_orphan_letters() -> None:
    """The direct answer to single letters passing as words."""
    for candidate in Anagram().produce("dormitory", lang="en", min_word_length=3).texts:
        assert all(len(word) >= 3 for word in candidate.split())


def test_a_capitalised_source_does_not_get_its_own_letters_back() -> None:
    """The reported defect once more, in the case a person actually types.

    The covers are built from a casefolded lexicon, so the identity cover of
    `Dormitory` is `dormitory` — which the guard let through while it compared
    case-sensitively, leaving `apply anagram "Astronomer"` returning its own
    input after `astronomer` was fixed.
    """
    for source in ("Dormitory", "DORMITORY", "Astronomer"):
        produced = Anagram().apply(source, lang="en")
        assert produced.casefold() != source.casefold(), source


def test_with_the_flag_off_nothing_changes() -> None:
    """The regression that keeps this from being a behaviour change in disguise.
    Byte-identical output on the three inputs the previous chapter was judged on."""
    procedure = Anagram()
    assert procedure.apply("dormitory", lang="en") == "dirty room"
    assert procedure.apply("astronomer", lang="en") == "arrest moon"
    assert procedure.apply("listen", lang="en") == "silent"


def test_a_subset_of_the_letters_satisfies_check_under_the_flag() -> None:
    """The transposal tradition: a candidate built from SOME of the source's
    letters. `check` reports every unused letter as `missing_letter` today."""
    procedure = Anagram()
    assert not procedure.check("room", lang="en", source="dormitory").satisfied
    assert procedure.check("room", lang="en", source="dormitory", allow_subset=True).satisfied


def test_surplus_letters_are_refused_under_the_flag_too() -> None:
    """A transposal may use fewer of the source's letters, never a letter the
    source does not have. Relaxing both halves would make the check vacuous."""
    assert not Anagram().check("zoo", lang="en", source="dormitory", allow_subset=True).satisfied


def test_a_short_transposal_is_not_marked_down_for_brevity() -> None:
    """Scoring moves with the rule: `total` becomes the candidate's letter count,
    so a valid short transposal scores 1.0 rather than being penalised for the
    letters it declined to use."""
    report = Anagram().check("room", lang="en", source="dormitory", allow_subset=True)
    assert report.score == 1.0


def test_full_covers_still_rank_first_under_the_flag() -> None:
    """Every single word that fits is a valid transposal — 373 of them for
    `astronomer` before any multi-word cover. Without `letters_used` as the
    primary key, turning the flag on buries every good answer under fragments."""
    production = Anagram().produce("dormitory", lang="en", allow_subset=True)
    assert production.texts[0] == "dirty room"
    assert production.candidates[0].metrics["letters_used"] == 9


def test_every_subset_cover_satisfies_the_relaxed_check() -> None:
    """The round-trip property for the flag-on path, which the shared harness in
    `test_round_trip.py` cannot reach: `allow_subset` defaults to False there, as
    it must, so nothing outside this file exercises the transposal search."""
    procedure = Anagram()
    produced = procedure.produce("dormitory", lang="en", allow_subset=True, max_results=100)
    partial = [text for text in produced.texts if len(text.replace(" ", "")) < 9]
    assert partial, "the flag recorded no partial cover at all"
    for candidate in produced.texts:
        assert procedure.check(
            candidate, lang="en", source="dormitory", allow_subset=True
        ).satisfied


def test_a_letterless_candidate_is_not_a_transposal_of_anything() -> None:
    """`total` is the candidate's letter count under the flag, so an empty text
    drives it to zero and `_report` scores that vacuously 1.0. The hole the
    relaxation opens, closed the way `n_plus_7` closed the identical shape under
    `ambiguous_nouns="undecidable"`: a named violation, not a silent pass."""
    procedure = Anagram()
    for text in ("", "   ", "!!!"):
        report = procedure.check(text, lang="en", source="dormitory", allow_subset=True)
        assert not report.satisfied, text
        assert [v.rule for v in report.violations] == ["empty_transposal"], text
    # Two letterless texts still agree vacuously — the carve-out
    # `displacement_report` makes for a wordless candidate and a wordless source.
    assert procedure.check("!", lang="en", source=".", allow_subset=True).satisfied
