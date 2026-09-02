import pytest

from denckring import check
from denckring.core.errors import InvalidParams
from denckring.core.protocol import Constructive
from denckring.core.registry import get


def _slenderizing() -> Constructive:
    """`get` returns `BaseProcedure`, which has no `apply` — narrow it once here
    rather than repeating the `isinstance` assert at every call site below."""
    procedure = get("slenderizing")
    assert isinstance(procedure, Constructive)
    return procedure


def test_deleting_the_letter_throughout_is_satisfied() -> None:
    assert check("slenderizing", "bat", source="brat", deleted="r").satisfied


def test_keeping_the_letter_is_a_violation() -> None:
    assert not check("slenderizing", "brat", source="brat", deleted="r").satisfied


def test_extra_letters_are_reported() -> None:
    report = check("slenderizing", "batx", source="brat", deleted="r")
    assert any(v.rule == "extra_letters" for v in report.violations)


def test_apply_output_satisfies_its_own_checker_in_german() -> None:
    """The thesis, in the language that broke it.

    `_produce` kept a character when `fold_diacritics(ch).lower() != deleted`;
    `ß` folds to `ss`, which never equals one letter, so `ß` always survived —
    while `_check` expanded it into two `s` and dropped both. Measured before
    the fix: apply gave 'Die traße war groß.' and its own check scored 0.412
    with seven violations. See ADR 0035, D6.
    """
    source = "Die Straße war groß."
    produced = _slenderizing().apply(source, lang="de", deleted="s")
    assert check("slenderizing", produced, lang="de", source=source, deleted="s").satisfied


def test_the_eszett_is_removed_as_two_esses() -> None:
    """Folding says `ß` is `ss`, so deleting `s` must take the `ß` with it."""
    produced = _slenderizing().apply("Die Straße war groß.", lang="de", deleted="s")
    assert produced == "Die trae war gro."


def test_a_deleted_letter_that_folds_to_two_is_refused_by_name() -> None:
    """`deleted="ß"` used to raise `degenerate_output` advising
    `allow_identity=true`, which would have returned the untouched text as a
    slenderizing. D4 names the real cause instead.
    """
    with pytest.raises(InvalidParams) as caught:
        _slenderizing().apply("Die Straße war groß.", lang="de", deleted="ß")
    assert "fold_diacritics" in str(caught.value)


def test_the_eszett_can_be_deleted_with_folding_off() -> None:
    produced = _slenderizing().apply(
        "Die Straße war groß.", lang="de", deleted="ß", fold_diacritics=False
    )
    assert "ß" not in produced
