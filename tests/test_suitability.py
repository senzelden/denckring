"""What a row tells a caller building a transform prompt from it (audit C4).

denckring-bench hand-picked the rows a transform suite could use: those whose answer
is fixed by the source, and not those whose verdict reads material the model is
never shown. `Meta.unique_answer` and `Meta.hidden_material` say both. These tests
hold each flag to what it promises rather than to a list of rows.
"""

from __future__ import annotations

import re
from itertools import pairwise
from typing import Any

import pytest

from denckring import apply, check, describe, golden_cases
from denckring.core.base import ConstructiveProcedure
from denckring.core.errors import NoCandidateWord
from denckring.core.protocol import Lang
from denckring.core.registry import all_procedures

PROCEDURES = all_procedures()
UNIQUE = sorted(pid for pid, procedure in PROCEDURES.items() if procedure.meta.unique_answer)
HIDDEN = sorted(pid for pid, procedure in PROCEDURES.items() if procedure.meta.hidden_material)

#: Capabilities whose data decides a row's answer, not merely how a text is read: the
#: seventh noun after a word, a word's dictionary gloss, a corpus saying's seam.
ANSWER_DATA = frozenset({"lexicon.nouns", "lexicon.glosses", "corpus.proverbs"})

#: Sources of the shapes the flagged rows read: lines, and blank-line separated pages.
SOURCES = (
    "The cat sat on the mat today\nA dog ran far into the night\n"
    "Birds sang loud above the trees\nRain fell soft upon the roof",
    "Morning light across the water\nslow boats drift toward the harbour\n\n"
    "Evening falls on quiet streets\nlamps come on in every window",
)


def _variants(text: str) -> list[str]:
    """Texts that differ from `text` in their words: one dropped, swapped, changed or added."""
    words = list(re.finditer(r"[^\W\d_]+", text))
    found: list[str] = []
    first, last = words[0], words[-1]
    found.append(text[: first.start()] + text[first.end() :])
    found.append(text[: last.start()] + text[last.end() :])
    found.append(text[: first.start()] + "zzz" + text[first.end() :])
    found.append(text + " " + first.group())
    for left, right in pairwise(words):
        if left.group().casefold() != right.group().casefold():
            found.append(
                text[: left.start()]
                + right.group()
                + text[left.end() : right.start()]
                + left.group()
                + text[right.end() :]
            )
            break
    return found


def _sources(pid: str) -> list[tuple[str, dict[str, Any], Lang]]:
    cases: list[tuple[str, dict[str, Any], Lang]] = [
        (case.params["source"], case.params, case.lang)
        for case in golden_cases()
        if case.procedure == pid and isinstance(case.params.get("source"), str)
    ]
    defaults: dict[str, Any] = {"slenderizing": {"deleted": "t"}}.get(pid, {})
    english: Lang = "en"
    return [*cases, *((source, {"source": source, **defaults}, english) for source in SOURCES)]


def test_the_transforms_the_bench_used_are_flagged() -> None:
    """Not the rule, an anchor: the rows whose answer the source fixes."""
    assert {"every_nth_word", "slenderizing", "boustrophedon"} <= set(UNIQUE)
    assert not PROCEDURES["anagram"].meta.unique_answer
    # Not unique today: an appended word from the source costs only an `extra_words`
    # violation on a report that stays satisfied (selection_report floors its total).
    assert not PROCEDURES["column_reading"].meta.unique_answer


@pytest.mark.parametrize("pid", UNIQUE)
def test_a_unique_answer_is_the_one_text_check_passes(pid: str) -> None:
    procedure = PROCEDURES[pid]
    assert isinstance(procedure, ConstructiveProcedure), f"{pid} has no answer to be unique"
    assert procedure.meta.checkability == "source"
    tried = 0
    for source, params, lang in _sources(pid):
        rest = {name: value for name, value in params.items() if name != "source"}
        try:
            answer = apply(pid, source, lang=lang, **rest)
        except NoCandidateWord:
            continue  # a source of the wrong shape for this row: nothing to hold
        assert check(pid, answer, lang=lang, **params).satisfied
        assert check(pid, answer.upper(), lang=lang, **params).satisfied
        for variant in _variants(answer):
            report = check(pid, variant, lang=lang, **params)
            assert not report.satisfied, f"{pid}: {variant!r} passes beside {answer!r}"
        tried += 1
    assert tried >= 1, f"{pid}: no source of a shape it reads"


@pytest.mark.parametrize("pid", HIDDEN)
def test_hidden_material_names_a_parameter_or_a_required_capability(pid: str) -> None:
    meta = PROCEDURES[pid].meta
    fields = PROCEDURES[pid].params_model().model_fields
    for name in meta.hidden_material:
        if name in fields:
            assert not fields[name].is_required(), f"{pid}.{name}: required, so supplied"
        else:
            assert name in meta.requires, f"{pid}: {name!r} is neither a parameter nor required"


@pytest.mark.parametrize("pid", sorted(PROCEDURES))
def test_a_row_whose_answer_is_in_pack_data_says_so(pid: str) -> None:
    """A row needing a noun list, glosses or a proverb corpus reads its answer from data
    the prompt does not carry, so it declares hidden material."""
    meta = PROCEDURES[pid].meta
    if ANSWER_DATA & set(meta.requires):
        assert meta.hidden_material, f"{pid} requires {sorted(ANSWER_DATA & set(meta.requires))}"


def test_describe_carries_both_flags() -> None:
    assert describe("every_nth_word").unique_answer is True
    assert describe("n_plus_7").hidden_material == ["dictionary"]
    assert describe("lipogram").hidden_material == []
