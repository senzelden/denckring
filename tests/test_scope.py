"""Each row's scope holds of its checker, and a witness proves its parameters (C2, C6).

A row that claims a scope promises a fact about every text built from units of
that size: the text passes if and only if each unit passes alone. These tests
build such texts from the units the golden corpus holds, passing and failing,
and compare the two verdicts, for every row that claims anything and at every
parameter set its golden cases use. A claim added later is held to it without
being listed here.
"""

from __future__ import annotations

import re
from itertools import islice
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import denckring
from denckring import admits, check, golden_cases, scope, witness
from denckring.core.errors import InvalidParams, NoCandidateWord, NotWordLocal, UnknownLanguage
from denckring.core.fields import kinds, roles
from denckring.core.protocol import Lang
from denckring.core.registry import all_procedures
from denckring.core.scope import SCOPES, coarsest
from denckring.core.text import UNIT_ENDS, line_spans
from denckring.lang import get_pack

PROCEDURES = all_procedures()
CLAIMING = sorted(pid for pid, procedure in PROCEDURES.items() if procedure.local_scope != "text")

#: A value of each kind an `inferred` parameter can hold, to state it with.
STATED = {"letter": "s", "vowel": "a", "vowels": "ae", "consonant": "t"}

#: Composites, whose scope is the coarsest their constraints keep.
COMPOSITES: list[dict[str, Any]] = [
    {
        "constraints": ["lipogram", "tautogram"],
        "constraint_params": {"tautogram": {"initial": "s"}},
    },
    {
        "constraints": ["prisoners_constraint", "liponym"],
        "constraint_params": {"liponym": {"forbidden": "a"}},
    },
]

#: The marks that close a sentence, as the scope and the reading both publish them.
SENTENCE_MARKS = UNIT_ENDS["sentence"]
SENTENCE_END = re.compile(rf"(?<=[{re.escape(SENTENCE_MARKS)}])\s+")


def _stated(pid: str, params: dict[str, Any]) -> dict[str, Any]:
    """`params` with every unset `inferred` parameter stated."""
    model = PROCEDURES[pid].params_model()
    found = dict(params)
    for name, role in roles(model).items():
        if role == "inferred" and found.get(name) is None:
            found[name] = STATED[kinds(model)[name]]
    return found


def _settings() -> list[tuple[str, Lang, dict[str, Any]]]:
    """Each claiming row at each distinct parameter set its golden cases use, with
    inferred parameters stated, where the row then claims a unit."""
    seen: list[tuple[str, Lang, dict[str, Any]]] = []
    for case in golden_cases():
        if case.procedure not in CLAIMING:
            continue
        params = _stated(case.procedure, case.params)
        entry = (case.procedure, case.lang, params)
        if scope(case.procedure, **params) != "text" and entry not in seen:
            seen.append(entry)
    # A claim no golden case reaches: heterogram's cases all ban repeats text-wide.
    seen.append(("heterogram", "en", {"scope": "word"}))
    seen += [("multiple_constraint", "en", params) for params in COMPOSITES]
    return seen


SETTINGS = _settings()
IDS = [f"{pid}-{lang}-{index}" for index, (pid, lang, _) in enumerate(SETTINGS)]


#: How many distinct units a pool holds: the row's own first, then the language's.
POOL = 300


def _texts(pids: list[str], lang: Lang) -> list[str]:
    """The row's golden texts first, then every other text in the language, so a
    language with few cases for the row still offers units of both verdicts."""
    cases = golden_cases(lang)
    own = [case.text for case in cases if case.procedure in pids]
    return own + [case.text for case in cases if case.procedure not in pids]


def _units(unit: str, pid: str, lang: Lang, params: dict[str, Any]) -> list[str]:
    """The units of the golden texts, the row's (or its constraints') first, each once."""
    pids = params.get("constraints", [pid])
    texts = _texts(pids, lang)
    if unit == "word":
        pack = get_pack(lang)
        found = [word for text in texts for _, word in pack.word_spans(text)]
    elif unit == "line":
        found = [line for text in texts for _, line in line_spans(text)]
    else:
        closed = [
            sentence.strip()
            for text in texts
            for sentence in SENTENCE_END.split(text.strip())
            if sentence.strip() and sentence.strip()[-1] in SENTENCE_MARKS
        ]
        # Each sentence closed by every mark in turn, so the claim is tested at each
        # mark it names and not only at those the golden texts happen to use.
        found = [sentence[:-1] + mark for sentence in closed for mark in SENTENCE_MARKS]
    return list(dict.fromkeys(found))[:POOL]


SEPARATORS = {
    "word": [" ", "\n", ", ", ". ", "; ", " - ", "! "],
    "line": ["\n"],
    "sentence": [" "],
}


def test_every_claiming_row_is_tested_at_its_claim() -> None:
    """No claim goes untested for want of a golden case to draw units from."""
    tested = {pid for pid, _, _ in SETTINGS}
    assert set(CLAIMING) <= tested
    assert {"word", "line", "sentence"} <= {scope(pid, **p) for pid, _, p in SETTINGS}


@pytest.mark.parametrize(("pid", "lang", "params"), SETTINGS, ids=IDS)
def test_a_text_of_units_passes_exactly_when_each_unit_does(
    pid: str, lang: Lang, params: dict[str, Any]
) -> None:
    unit = scope(pid, **params)
    pool = _units(unit, pid, lang, params)
    verdicts = {text: check(pid, text, lang=lang, **params).satisfied for text in pool}
    # Both directions are tested only if the pool holds a unit of each verdict.
    assert set(verdicts.values()) == {True, False}, f"{pid}: {unit}s all {verdicts}"

    @settings(max_examples=40, derandomize=True, deadline=None)
    @given(
        st.lists(st.sampled_from(pool), min_size=1, max_size=5),
        st.lists(st.sampled_from(SEPARATORS[unit]), min_size=4, max_size=4),
    )
    def holds(units: list[str], separators: list[str]) -> None:
        text = units[0]
        for index, part in enumerate(units[1:]):
            text += separators[index % len(separators)] + part
        expected = all(verdicts[part] for part in units)
        report = check(pid, text, lang=lang, **params)
        assert report.satisfied is expected, f"{pid} {unit}: {text!r}"

    holds()


INFERRING = [
    pid for pid in CLAIMING if "inferred" in roles(PROCEDURES[pid].params_model()).values()
]


@pytest.mark.parametrize("pid", INFERRING)
def test_an_unset_inferred_parameter_leaves_no_unit_judged_alone(pid: str) -> None:
    """Unset, the checker reads it off the text, so a unit's verdict is not its own:
    two words each passing alone fail together, and the row claims nothing."""
    procedure = PROCEDURES[pid]
    inferred = [
        name for name, role in roles(procedure.params_model()).items() if role == "inferred"
    ]
    case = next(case for case in golden_cases() if case.procedure == pid)
    params = {name: value for name, value in case.params.items() if name not in inferred}
    assert scope(pid, **params) == "text"
    with pytest.raises(NotWordLocal) as raised:
        admits(pid, "word", lang=case.lang, **params)
    assert raised.value.unset == inferred
    alone = [
        word
        for word in _units("word", pid, case.lang, params)[:80]
        if check(pid, word, lang=case.lang, **params).satisfied
    ]
    assert any(
        not check(pid, f"{first} {second}", lang=case.lang, **params).satisfied
        for first in alone
        for second in alone
    ), f"{pid}: every pair of words passing alone passes together"


def test_the_scopes_the_rows_were_measured_at() -> None:
    """Anchors, so a claim dropped from a row fails visibly."""
    assert scope("lipogram") == "word"
    assert scope("tautogram") == "text"
    assert scope("tautogram", initial="t") == "word"
    assert scope("beau_present", name="Ada") == "word"
    assert scope("beau_present", name="Ada", require_all=True) == "text"
    assert scope("heterogram") == "text"
    assert scope("heterogram", scope="word") == "word"
    assert scope("iambic_pentameter") == "line"
    assert scope("verbless_prose") == "sentence"
    assert scope("sonnet") == "text"


def test_a_composite_keeps_the_coarsest_scope() -> None:
    def composite(*pids: str, **params: dict[str, Any]) -> str:
        return scope("multiple_constraint", constraints=list(pids), constraint_params=params)

    assert composite("lipogram", "tautogram", tautogram={"initial": "s"}) == "word"
    assert composite("lipogram", "tautogram") == "text"
    assert composite("lipogram", "iambic_pentameter") == "line"
    assert composite("lipogram", "verbless_prose") == "sentence"
    assert composite("iambic_pentameter", "verbless_prose") == "text"


@pytest.mark.parametrize(
    ("scopes", "expected"),
    [
        ([], "word"),
        (["word", "word"], "word"),
        (["word", "line"], "line"),
        (["sentence", "word"], "sentence"),
        (["line", "sentence"], "text"),
        (["word", "text"], "text"),
    ],
)
def test_coarsest(scopes: list[Any], expected: str) -> None:
    assert coarsest(scopes) == expected


def test_scopes_are_published_and_defined() -> None:
    assert set(denckring.scopes()) == set(SCOPES) == {"word", "line", "sentence", "text"}
    assert all(text.strip() for text in denckring.scopes().values())
    assert denckring.scopes() is not denckring.scopes()


WORD_SETTINGS = [entry for entry in SETTINGS if scope(entry[0], **entry[2]) == "word"]


@pytest.mark.parametrize(
    ("pid", "lang", "params"), WORD_SETTINGS, ids=[f"{s[0]}-{s[1]}" for s in WORD_SETTINGS]
)
def test_a_witness_passes_and_admits_agrees_with_check(
    pid: str, lang: Lang, params: dict[str, Any]
) -> None:
    pool = _units("word", pid, lang, params)
    admitted = [word for word in pool if admits(pid, word, lang=lang, **params)]
    for word in pool:
        assert admits(pid, word, lang=lang, **params) is (word in admitted)
    text = witness(pid, pool, lang=lang, **params)
    assert check(pid, text, lang=lang, **params).satisfied
    assert text.split(" ") == admitted[:12]
    assert witness(pid, pool, lang=lang, size=2, **params).split(" ") == admitted[:2]
    refused = [word for word in pool if word not in admitted]
    with pytest.raises(NoCandidateWord):
        witness(pid, refused, lang=lang, **params)


def test_a_witness_reads_only_single_words_and_stops_at_size() -> None:
    vocabulary = ["two words", "dog", "", "cat!", "bird", "fish"]
    assert witness("lipogram", vocabulary) == "dog bird fish"
    assert witness("lipogram", vocabulary, size=1) == "dog"
    endless = (word for word in iter(lambda: "dog", None))
    assert witness("lipogram", islice(endless, 10_000), size=3) == "dog dog dog"
    with pytest.raises(InvalidParams):
        witness("lipogram", vocabulary, size=0)


def test_a_row_judging_no_word_alone_refuses_admits_and_witness() -> None:
    with pytest.raises(NotWordLocal) as raised:
        admits("iambic_pentameter", "word")
    assert raised.value.detail() == {
        "procedure_id": "iambic_pentameter",
        "scope": "line",
        "unset": [],
    }
    with pytest.raises(NotWordLocal, match="State initial"):
        witness("tautogram", ["sun"])
    assert raised.value.to_dict()["code"] == "not_word_local"


def test_scope_takes_lang_as_its_siblings_do() -> None:
    """M2: one kwargs dict serves `scope`, `admits` and `check` alike. The scope is
    the same in every language, and an unknown one is refused as `check` refuses it."""
    params: dict[str, Any] = {"forbidden": "e", "lang": "fr"}
    assert scope("lipogram", **params) == scope("lipogram", forbidden="e") == "word"
    assert admits("lipogram", "chat", **params) is True
    with pytest.raises(UnknownLanguage):
        scope("lipogram", forbidden="e", lang="xx")  # type: ignore[arg-type]


def test_a_sentence_scope_ends_where_the_reading_says_a_sentence_ends() -> None:
    """M4: `scopes()` and `describe(...).reading.units` publish one set of marks."""
    marks = denckring.describe("verbless_prose").reading.units["sentence"]
    assert marks
    for mark in marks:
        assert repr(mark) in denckring.scopes()["sentence"], mark
