from itertools import permutations

import pytest

from denckring import apply, check
from denckring.core.errors import InvalidParams, MissingCapability, NoCandidateWord
from denckring.lang.en import EnglishPack

DATA = pytest.importorskip("denckring_en_data")
SOURCE = "A stitch in time saves nine"
DONOR = "Birds of a feather flock together"


def test_every_distinct_corpus_pair_round_trips() -> None:
    corpus = DATA.EnglishDataPack().proverbs()
    assert len(corpus) >= 2
    for first, second in permutations(corpus, 2):
        source, donor = " ".join(first), " ".join(second)
        output = apply("perverb", source, donor=donor)
        assert output == f"{first[0]} {second[1]}"
        assert output != source
        assert check("perverb", output, source=source, donor=donor).satisfied


@pytest.mark.parametrize("candidate", ["", SOURCE, "A stitch in time gathers no moss"])
def test_wrong_grafts_fail_for_the_graft_rule(candidate: str) -> None:
    report = check("perverb", candidate, source=SOURCE, donor=DONOR)
    assert not report.satisfied
    assert [v.rule for v in report.violations] == ["not_the_graft"]


@pytest.mark.parametrize(
    "source,donor", [("unknown", DONOR), (SOURCE, "unknown"), (SOURCE, SOURCE), ("", DONOR)]
)
def test_unknown_or_identical_pairs_cannot_pass_or_generate(source: str, donor: str) -> None:
    report = check("perverb", "A stitch in time flock together", source=source, donor=donor)
    assert not report.satisfied
    assert [v.rule for v in report.violations] == ["unresolved_proverb_pair"]
    with pytest.raises(NoCandidateWord):
        apply("perverb", source, donor=donor)


def test_normalisation_is_explicit_and_does_not_change_the_word_sequence() -> None:
    assert check(
        "perverb", "A STITCH in time, flock together!", source=SOURCE + ".", donor=DONOR.upper()
    ).satisfied
    assert not check(
        "perverb", "A stitch flock in time together", source=SOURCE, donor=DONOR
    ).satisfied


def test_donor_is_required_and_source_cannot_be_overridden() -> None:
    with pytest.raises(InvalidParams):
        apply("perverb", SOURCE)
    with pytest.raises(InvalidParams):
        apply("perverb", SOURCE, source=SOURCE, donor=DONOR)


def test_base_pack_does_not_claim_a_corpus() -> None:
    assert "corpus.proverbs" not in EnglishPack.capabilities
    with pytest.raises(MissingCapability):
        EnglishPack().proverbs()


def test_corpus_entries_have_nonempty_distinct_halves_and_unique_sayings() -> None:
    corpus = DATA.EnglishDataPack().proverbs()
    assert all(left.strip() and right.strip() for left, right in corpus)
    assert len({" ".join(entry).casefold() for entry in corpus}) == len(corpus)


def test_public_capability_gate_refuses_core_only_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("denckring.lang.get_pack", lambda lang="en": EnglishPack())
    with pytest.raises(MissingCapability):
        check("perverb", "A stitch in time flock together", source=SOURCE, donor=DONOR)
    with pytest.raises(MissingCapability):
        apply("perverb", SOURCE, donor=DONOR)
