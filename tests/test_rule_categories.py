"""Every declared rule names a kind of failure, from a closed set (audit C3).

denckring-bench mapped some seventy-five rule strings to eight classes in a file of
its own and re-checked it by hand against each release. The map is upstream now,
held to the declarations both ways, so a new rule without a category fails here,
and so does a category entry for a rule no row declares any more.
"""

from __future__ import annotations

from typing import get_args

import pytest

import denckring
from denckring.core.registry import all_procedures
from denckring.core.rules import (
    _BY_CATEGORY,
    CATEGORIES,
    ROW_CATEGORIES,
    RULE_CATEGORIES,
    Category,
)

PROCEDURES = all_procedures()
DECLARED = {rule for procedure in PROCEDURES.values() for rule in procedure.rules}


def test_every_declared_rule_has_a_category() -> None:
    assert sorted(DECLARED - set(RULE_CATEGORIES)) == []


def test_no_category_names_a_rule_no_row_declares() -> None:
    assert sorted(set(RULE_CATEGORIES) - DECLARED) == []


def test_a_rule_is_in_one_category_only() -> None:
    listed = [rule for rules in _BY_CATEGORY.values() for rule in rules]
    assert sorted(rule for rule in set(listed) if listed.count(rule) > 1) == []


def test_the_categories_are_the_closed_set_and_each_is_defined() -> None:
    assert set(CATEGORIES) == set(get_args(Category)) == set(_BY_CATEGORY)
    assert set(RULE_CATEGORIES.values()) == set(CATEGORIES)
    assert all(definition.strip() for definition in CATEGORIES.values())


@pytest.mark.parametrize("pid", sorted(PROCEDURES))
def test_rule_categories_covers_exactly_the_rows_rules(pid: str) -> None:
    categories = denckring.rule_categories(pid)
    assert tuple(categories) == denckring.rules(pid)
    assert set(categories.values()) <= set(denckring.failure_categories())


def test_a_composite_answers_for_every_rule_it_can_pass_through() -> None:
    assert set(denckring.rule_categories("multiple_constraint")) == DECLARED


def test_the_categories_read_as_the_kinds_of_mistake_they_name() -> None:
    """A few anchors a reader would check first, so a shuffled map fails visibly."""
    assert denckring.rule_categories("lipogram") == {"forbidden_letter": "excluded_letter"}
    assert denckring.rule_categories("pangram")["missing_letter"] == "inventory"
    assert denckring.rule_categories("haiku")["wrong_syllable_count"] == "sound"
    assert denckring.rule_categories("acrostic")["wrong_letter"] == "position"
    assert denckring.rule_categories("n_plus_7")["unchanged"] == "transcription"
    assert denckring.rule_categories("rhyme_scheme")["rhyme_undecidable"] == "unreadable"
    assert denckring.failure_categories() is not denckring.failure_categories()


def test_a_row_exception_names_a_rule_its_row_declares_and_changes_it() -> None:
    """An exception is for a rule that means another kind of failure on one row. One
    the row cannot emit, or that restates the default, is a stale entry."""
    for (pid, rule), category in ROW_CATEGORIES.items():
        assert rule in PROCEDURES[pid].rules, (pid, rule)
        assert category != RULE_CATEGORIES[rule], (pid, rule)
        assert category in CATEGORIES, (pid, rule)


def test_wrong_letter_is_a_place_on_a_spine_and_a_transcription_on_slenderizing() -> None:
    """On `acrostic` and `telestich` the letter is on the wrong line's edge; on
    `slenderizing` the text departs from its source, beside `extra_letters`."""
    assert denckring.rule_categories("acrostic")["wrong_letter"] == "position"
    assert denckring.rule_categories("telestich")["wrong_letter"] == "position"
    slender = denckring.rule_categories("slenderizing")
    assert slender == {
        "extra_letters": "transcription",
        "missing_letter": "transcription",
        "wrong_letter": "transcription",
    }
