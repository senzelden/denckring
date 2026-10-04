"""Positional rows score over an alignment, not index by index (ADR 0056, audit A6).

Each row compared the text with what its rule expects unit by unit, so one dropped
unit early in the text shifted every later one, and the text scored as if it had
nothing right after the drop. N+7 went further: a word-count mismatch scored the
whole text 0/1. Each case below drops one unit near the start of an otherwise
correct text, and must cost that one unit and name it, with nothing cascading.
"""

from __future__ import annotations

from typing import Any

import pytest

from denckring import check
from denckring.core.source_compare import align, aligned_report

PAGE = "a cat\nb dog\nc bird\nd fish"
HAIKU_SOURCE = "the cat sat down\na dog ran fast\nbirds fly high\nfish swim deep"

# (row, text, params, score, the one violation's rule, its offset, its `expected`)
DROPPED: list[tuple[str, str, dict[str, Any], float, str, int, str]] = [
    (
        "every_nth_word",
        "four six eight",
        {"source": "one two three four five six seven eight", "n": 2},
        3 / 4,
        "missing_word",
        0,
        "two",
    ),
    # 6/7 rather than 3/4: `selection_report`'s three units, all good, sit
    # beside the alignment's four.
    (
        "column_reading",
        "dog bird fish",
        {"source": PAGE, "column": 2},
        6 / 7,
        "missing_word",
        0,
        "cat",
    ),
    ("haikuization", "fast high deep", {"source": HAIKU_SOURCE}, 6 / 7, "missing_word", 0, "down"),
    (
        "slenderizing",
        "th ct st",
        {"source": "the cat sat", "deleted": "a"},
        6 / 7,
        "missing_letter",
        3,
        "e",
    ),
    (
        "homoconsonantism",
        "te cot sit",
        {"source": "the cat sat"},
        5 / 6,
        "missing_letter",
        3,
        "h",
    ),
    (
        "homovocalism",
        "th cat sat on a mat",
        {"source": "the cat sat on a mat"},
        5 / 6,
        "missing_letter",
        4,
        "e",
    ),
    (
        "n_plus_7",
        "catacomb satchmo on the tablespoonful",
        {"source": "the cat sat on the table"},
        5 / 6,
        "missing_word",
        0,
        "the",
    ),
    (
        "s_plus_7",
        "catacala satanism on the tablefork",
        {"source": "the cat sat on the table", "offset": 3},
        5 / 6,
        "missing_word",
        0,
        "the",
    ),
]


@pytest.mark.parametrize(
    ("pid", "text", "params", "score", "rule", "offset", "expected"),
    DROPPED,
    ids=[case[0] for case in DROPPED],
)
def test_one_dropped_unit_costs_one_unit(
    pid: str,
    text: str,
    params: dict[str, Any],
    score: float,
    rule: str,
    offset: int,
    expected: str,
) -> None:
    report = check(pid, text, **params)
    assert report.satisfied is False
    assert report.score == pytest.approx(score)
    assert [(v.rule, v.offset, v.expected) for v in report.violations] == [(rule, offset, expected)]


def test_a_missing_unit_at_the_end_is_placed_at_the_end() -> None:
    report = check(
        "every_nth_word", "two four six", source="one two three four five six seven eight", n=2
    )
    assert [(v.rule, v.offset, v.expected) for v in report.violations] == [
        ("missing_word", len("two four six"), "eight")
    ]


def test_a_word_inserted_mid_text_is_one_run_at_its_first_word() -> None:
    """An insertion is no longer only a tail: the run is reported where it is."""
    text = "two very big four six eight"
    report = check("every_nth_word", text, source="one two three four five six seven eight", n=2)
    assert [(v.rule, v.offset, v.found) for v in report.violations] == [
        ("extra_words", 4, "very big")
    ]
    assert report.score == pytest.approx(4 / 6)


def test_only_an_exact_match_scores_one() -> None:
    steps = align(["a", "b", "c"], ["a", "b", "c"])
    assert [step.step for step in steps] == ["match"] * 3
    for actual in (["a", "c"], ["a", "b", "c", "d"], ["a", "x", "c"], [], ["c", "b", "a"]):
        result = aligned_report(
            ["a", "b", "c"],
            [(index, unit) for index, unit in enumerate(actual)],
            key=str.casefold,
            substituted="wrong",
            inserted="extra",
            deleted="missing",
            joiner="",
            end=len(actual),
        )
        assert result.good < result.total
        assert result.violations


def test_an_unequal_replace_counts_its_longer_side() -> None:
    """R-U8a: a `replace` of two units by three pairs two as substitutions and
    leaves one insertion, so the span counts three units, not five."""
    steps = align(["a", "x", "y", "b"], ["a", "p", "q", "r", "b"])
    assert [step.step for step in steps] == [
        "match",
        "substitute",
        "substitute",
        "insert",
        "match",
    ]


def test_an_empty_pair_aligns_to_nothing() -> None:
    """`total == 0`, which `_report` scores vacuously satisfied (the reason
    `letter_class_report` keeps no `, 1` floor)."""
    result = aligned_report(
        [],
        [],
        key=str.casefold,
        substituted="wrong",
        inserted="extra",
        deleted="missing",
        joiner="",
        end=0,
    )
    assert (result.good, result.total, result.violations) == (0, 0, [])
