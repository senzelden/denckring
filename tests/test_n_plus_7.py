import pytest

from denckring import check
from denckring.core.errors import InvalidParams
from denckring.procedures.n_plus_7 import NPlus7

pytest.importorskip("denckring_en_data")

SOURCE = "the cat sat on the table"
DISPLACED = "the catacomb satchmo on the tablespoonful"
GARDEN = ["aster", "bramble", "crocus", "dahlia", "elder", "fennel", "gorse", "hazel"]


def test_a_correct_displacement_is_satisfied() -> None:
    assert check("n_plus_7", DISPLACED, source=SOURCE).satisfied


def test_leaving_a_noun_alone_is_readable_as_another_part_of_speech() -> None:
    """A word list cannot rule it out, so it is tolerated and counted."""
    report = check("n_plus_7", SOURCE, source=SOURCE)
    assert report.satisfied
    assert report.metrics["ambiguous_words"] > 0


def test_changing_a_non_noun_is_a_violation() -> None:
    report = check("n_plus_7", "a cat sat on the table", source=SOURCE)
    assert not report.satisfied
    assert report.violations[0].rule == "changed_a_non_noun"


def test_a_wrong_displacement_is_a_violation() -> None:
    wrong = DISPLACED.replace("catacomb", "zebra")
    assert not check("n_plus_7", wrong, source=SOURCE).satisfied


def test_a_different_word_count_is_a_violation() -> None:
    report = check("n_plus_7", "too short", source=SOURCE)
    assert report.violations[0].rule == "wrong_word_count"


def test_a_supplied_dictionary_is_the_one_that_gets_walked() -> None:
    """`n_plus_7`'s catalogue definition says the displacement happens "in a
    chosen dictionary". Until now there was no choice — the defect class ADR 0015
    exists to prevent, sitting in the row since it was written."""
    produced = NPlus7().apply("aster", lang="en", dictionary=GARDEN, offset=1)
    assert produced == "bramble"


def test_check_verifies_against_the_same_dictionary_it_was_given() -> None:
    """The reason `dictionary` is on the CHECK params and not apply-only: given a
    different list, `check` computes different displacements and rejects correct
    work. Both directions, or this proves only that the parameter is accepted."""
    procedure = NPlus7()
    produced = procedure.apply("aster", lang="en", dictionary=GARDEN, offset=1)
    assert procedure.check(
        produced, lang="en", source="aster", dictionary=GARDEN, offset=1
    ).satisfied
    assert not procedure.check(produced, lang="en", source="aster", offset=1).satisfied


def test_the_default_is_still_the_packs_nouns() -> None:
    """Nothing changes for a caller who does not ask."""
    procedure = NPlus7()
    assert procedure.apply("cat", lang="en") == procedure.apply("cat", lang="en", dictionary=None)


def test_a_dictionary_entry_must_survive_the_tokeniser() -> None:
    """ADR 0015 restricts `nouns()` to single alphabetic lemmas because a
    displacement has to be a word the tokeniser gives back whole — `cat's-paw`
    comes back as three tokens and breaks the source-to-result correspondence.
    A supplied list is held to the same rule, for the same reason."""
    with pytest.raises(InvalidParams):
        NPlus7().apply("aster", lang="en", dictionary=["aster", "cat's-paw"])


def test_an_empty_dictionary_is_refused() -> None:
    """`(index + offset) % len(nouns)` divides by it."""
    with pytest.raises(InvalidParams):
        NPlus7().apply("aster", lang="en", dictionary=[])
