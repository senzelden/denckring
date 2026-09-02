import pytest

from denckring import check
from denckring.core.errors import DegenerateOutput, InvalidParams
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


def test_apply_output_satisfies_its_own_checker_across_a_mixed_fold() -> None:
    """The thesis again, in the language that broke the *fix*.

    Dropping a source character whenever any letter it folds to is `deleted`
    agrees with `_check` only for a uniform fold. `ß` → `ss` is uniform; `œ` →
    `oe` is not. Measured under that rule: `deleted="e"` gave
    'L cur t la sur', scoring 0.167, and `deleted="o"` gave 'Le cur et la sur',
    scoring 0.214 — where the code before ADR 0035 raised `DegenerateOutput`,
    so the second was a regression and not merely a shortfall.

    Both letters, because they exercise opposite halves of the ligature: `e`
    is the half the earlier rule mangled into text failing this assertion, `o`
    the half the code before ADR 0035 refused outright. Confirmed to
    discriminate by restoring that rule and watching this fail on both.
    """
    source = "Le cœur et la sœur"
    for deleted in ("e", "o"):
        produced = _slenderizing().apply(source, lang="fr", deleted=deleted)
        report = check("slenderizing", produced, lang="fr", source=source, deleted=deleted)
        assert report.satisfied, (deleted, produced, report.score)


def test_a_mixed_fold_keeps_the_half_that_was_not_deleted() -> None:
    """The output itself, not just its verdict.

    `test_apply_output_satisfies_its_own_checker_across_a_mixed_fold` would
    also pass if both halves of `œ` vanished *and* `_check` agreed, which is
    the failure mode a round-trip test cannot see on its own. These are the
    strings, and they are the ones the golden cases pin.
    """
    source = "Le cœur et la sœur"
    assert _slenderizing().apply(source, lang="fr", deleted="e") == "L cour t la sour"
    assert _slenderizing().apply(source, lang="fr", deleted="o") == "Le ceur et la seur"


def test_a_character_no_letter_of_which_was_deleted_is_left_untouched() -> None:
    """Case and the ligature survive, because the character is not rewritten.

    Emitting the folded survivors unconditionally would give 'le coeur...' —
    still satisfying `_check`, which compares folded streams, and still wrong
    as text.
    """
    assert _slenderizing().apply("Le cœur", lang="fr", deleted="l") == "e cœur"


def test_the_eszett_can_be_deleted_with_folding_off() -> None:
    produced = _slenderizing().apply(
        "Die Straße war groß.", lang="de", deleted="ß", fold_diacritics=False
    )
    assert "ß" not in produced


def test_folding_off_refuses_where_it_used_to_delete_through_the_fold() -> None:
    """A recorded behaviour change, not an accident (ADR 0035, Consequences).

    The old `_produce` ignored `fold_diacritics` and always folded, so this
    call returned 'Bh' — deleting a letter through the very fold the caller
    had switched off. With folding off, `ä` is `ä`, the text holds no `a`, and
    the slenderizing of it is the text itself, which is also the answer
    `_check` gives: the refusal is the two agreeing.
    """
    with pytest.raises(DegenerateOutput):
        _slenderizing().apply("Bäh", lang="de", deleted="a", fold_diacritics=False)
    assert check(
        "slenderizing", "Bäh", lang="de", source="Bäh", deleted="a", fold_diacritics=False
    ).satisfied
