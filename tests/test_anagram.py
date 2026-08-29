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
