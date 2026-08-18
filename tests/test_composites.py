"""Unit tests for `larding` and `multiple_constraint`, beyond the golden/strategy suites."""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams, MissingCapability
from denckring.core.registry import get
from denckring.lang.en import EnglishPack

# ---------------------------------------------------------------------------
# larding
# ---------------------------------------------------------------------------


def test_larding_checks_alternating_positions() -> None:
    report = check(
        "larding",
        "A cat sat. New lard one. The dog ran. New lard two. It rained hard.",
        source="A cat sat. The dog ran. It rained hard.",
    )
    assert report.satisfied is True
    assert report.score == 1.0


def test_larding_rejects_a_missing_lard() -> None:
    report = check(
        "larding",
        "A cat sat. The dog ran. It rained hard.",
        source="A cat sat. The dog ran. It rained hard.",
    )
    assert report.satisfied is False
    assert report.score < 1.0
    assert {v.rule for v in report.violations} & {
        "missing_intercalated_sentence",
        "wrong_sentence_count",
    }


def test_larding_rejects_a_source_sentence_out_of_place() -> None:
    report = check(
        "larding",
        "A cat sat. New lard one. Something else entirely. New lard two. It rained hard.",
        source="A cat sat. The dog ran. It rained hard.",
    )
    assert report.satisfied is False
    assert any(v.rule == "source_sentence_out_of_place" for v in report.violations)


def test_larding_penalises_trailing_material_not_merely_flag_it() -> None:
    """A score of 1.0 alongside a fired violation was the real bug found in this
    batch — invented material past the expected alternation must cost score."""
    report = check(
        "larding",
        "A cat sat. New lard one. The dog ran. New lard two. It rained hard. Extra junk.",
        source="A cat sat. The dog ran. It rained hard.",
    )
    assert report.satisfied is False
    assert report.score < 1.0
    assert any(v.rule == "wrong_sentence_count" for v in report.violations)


def test_larding_populates_offsets_for_misplaced_sentences() -> None:
    report = check(
        "larding",
        "A cat sat. New lard one. Something else. New lard two. It rained hard.",
        source="A cat sat. The dog ran. It rained hard.",
    )
    misplaced = [v for v in report.violations if v.rule == "source_sentence_out_of_place"]
    assert misplaced
    assert all(v.offset is not None for v in misplaced)


def test_larding_ships_no_apply() -> None:
    """`kind: both` in the catalogue, but inventing the intercalated sentence is
    writing, not transforming — ADR 0002 makes `apply` optional and this row
    does not provide one."""
    assert not hasattr(get("larding"), "apply")


def test_larding_is_vacuous_with_no_source_sentences() -> None:
    report = check("larding", "anything at all", source="")
    assert report.satisfied is True
    assert report.score == 1.0


# ---------------------------------------------------------------------------
# multiple_constraint
# ---------------------------------------------------------------------------


def test_multiple_constraint_satisfied_only_when_all_are() -> None:
    report = check(
        "multiple_constraint",
        "the letters were her tender ferments",
        constraints=["univocalic", "lipogram"],
        constraint_params={"univocalic": {"vowel": "e"}, "lipogram": {"forbidden": "a"}},
    )
    assert report.satisfied is True
    assert report.score == 1.0


def test_multiple_constraint_fails_when_one_constraint_fails() -> None:
    report = check(
        "multiple_constraint",
        "the cat sat",
        constraints=["univocalic", "lipogram"],
        constraint_params={"univocalic": {"vowel": "e"}, "lipogram": {"forbidden": "z"}},
    )
    assert report.satisfied is False
    assert report.score < 1.0


def test_violations_carry_the_producing_constraints_id_in_note() -> None:
    """Unreadable otherwise: a bare 'foreign_vowel' violation does not say which
    of several named constraints objected."""
    report = check(
        "multiple_constraint",
        "the cat sat",
        constraints=["univocalic", "lipogram"],
        constraint_params={"univocalic": {"vowel": "e"}, "lipogram": {"forbidden": "z"}},
    )
    assert report.violations
    assert all(v.note == "univocalic" for v in report.violations)


def test_a_delegates_own_note_is_preserved_alongside_the_constraint_id() -> None:
    """`diastic` sets its own descriptive `note`; forwarding must not clobber it."""
    report = check(
        "multiple_constraint",
        "zzz",
        constraints=["diastic", "univocalic"],
        constraint_params={
            "diastic": {"source": "abc"},
            "univocalic": {"vowel": "e"},
        },
    )
    diastic_violations = [v for v in report.violations if v.note and v.note.startswith("diastic")]
    assert diastic_violations
    # `wrong_letter_at_position` already carries its own note ("position 1 of
    # 'zzz'"); forwarding must prefix the constraint id onto it, not replace it.
    combined = [v for v in diastic_violations if v.rule == "wrong_letter_at_position"]
    assert combined
    assert all(v.note == "diastic: position 1 of 'zzz'" for v in combined)


def test_multiple_constraint_requires_at_least_two_constraints() -> None:
    with pytest.raises(InvalidParams):
        check("multiple_constraint", "text", constraints=["univocalic"])


def test_multiple_constraint_rejects_direct_self_reference() -> None:
    with pytest.raises(InvalidParams, match="multiple_constraint"):
        check(
            "multiple_constraint",
            "text",
            constraints=["multiple_constraint", "univocalic"],
            constraint_params={"univocalic": {"vowel": "e"}},
        )


def test_multiple_constraint_rejects_a_self_reference_nested_in_constraint_params() -> None:
    """The self-reference does not have to be the whole list — naming it alongside a
    real constraint, with its own (never-reached) nested params, is caught the same
    way, before any delegate executes."""
    with pytest.raises(InvalidParams, match="multiple_constraint"):
        check(
            "multiple_constraint",
            "text",
            constraints=["univocalic", "multiple_constraint"],
            constraint_params={
                "univocalic": {"vowel": "e"},
                "multiple_constraint": {
                    "constraints": ["lipogram", "multiple_constraint"],
                    "constraint_params": {"lipogram": {"forbidden": "z"}},
                },
            },
        )


def test_multiple_constraint_does_not_declare_a_delegates_capability() -> None:
    """The catalogue row's own `requires` is `[tokens]` only — it cannot know ahead
    of time what a named constraint will need, so it declares nothing beyond its
    own logic. Confirmed here directly against the catalogue entry rather than
    against a delegate's requirement, which is the whole point: this row's
    declaration must not grow just because `dactylic_hexameter` needs `stress`."""
    from denckring.core import catalogue

    assert catalogue.get("multiple_constraint").requires == ["tokens"]


def test_multiple_constraint_lets_a_delegates_missing_capability_propagate_cleanly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Naming a constraint this pack cannot run must fail as *that* constraint's
    `MissingCapability`, not a confusing failure blamed on `multiple_constraint`."""
    monkeypatch.setattr("denckring.lang.get_pack", lambda lang="en": EnglishPack())
    with pytest.raises(MissingCapability) as exc_info:
        check(
            "multiple_constraint",
            "some plain text for testing purposes",
            constraints=["univocalic", "dactylic_hexameter"],
            constraint_params={"univocalic": {"vowel": "e"}},
        )
    assert exc_info.value.procedure_id == "dactylic_hexameter"
    assert exc_info.value.capability == "stress"
