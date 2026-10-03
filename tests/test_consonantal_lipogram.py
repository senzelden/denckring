import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_text_avoiding_the_set_is_satisfied() -> None:
    assert check("consonantal_lipogram", "a real one", forbidden="bcd").satisfied


def test_one_forbidden_consonant_is_a_violation() -> None:
    report = check("consonantal_lipogram", "a bad one", forbidden="bcd")
    assert not report.satisfied
    assert {v.found for v in report.violations} == {"b", "d"}


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("consonantal_lipogram", "", forbidden="bcd").satisfied


# The forbidden set is folded the way the text is. Unfolded, `forbidden="ç"`
# could never match a folded letter and any text at all was vacuously
# satisfied: the lipogram's ADR 0035 D3 defect, surviving in the group row.
# Every case here is non-ASCII on the parameter side, so it fails against the
# unfolded code for its own reason (rules/procedures.md).
def test_an_accented_forbidden_letter_is_folded_like_the_text() -> None:
    report = check("consonantal_lipogram", "Le garçon chante.", lang="fr", forbidden="ç")
    assert not report.satisfied
    assert [(v.offset, v.found) for v in report.violations] == [(6, "c"), (10, "c")]


def test_an_accented_letter_among_plain_ones_is_folded() -> None:
    report = check("consonantal_lipogram", "un garçon", lang="fr", forbidden="bçd")
    assert not report.satisfied
    assert [v.offset for v in report.violations] == [6]


def test_unfolded_the_accented_letter_is_still_its_own_letter() -> None:
    assert check(
        "consonantal_lipogram", "un garcon", lang="fr", forbidden="ç", fold_diacritics=False
    ).satisfied
    assert not check(
        "consonantal_lipogram", "un garçon", lang="fr", forbidden="ç", fold_diacritics=False
    ).satisfied


def test_a_forbidden_letter_that_folds_to_two_is_refused() -> None:
    with pytest.raises(InvalidParams, match="fold_diacritics=false"):
        check("consonantal_lipogram", "Straße", lang="de", forbidden="bß")
