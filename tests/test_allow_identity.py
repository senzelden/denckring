"""`allow_identity`: a source row may be told to refuse its own source, unchanged.

Fourteen rows accepted a copy of their source as a correct answer, measured rather
than listed: `check(pid, source, source=source)` was satisfied with each row's own
golden parameters. `antigram` has always refused that, as `unchanged`; the other rows
now can, opt-in. The default stays `True` in 0.3.2 so no verdict moves.

The guard at the bottom holds the rule for rows not yet written: a source row whose
checker passes a copy either carries the parameter or is named in `COPY_IS_THE_ANSWER`
with the reason the copy is right there.
"""

from __future__ import annotations

from typing import Any

import pytest

from denckring import check
from denckring.core.base import ConstructiveProcedure
from denckring.core.errors import DenckringError
from denckring.core.protocol import Lang
from denckring.core.registry import all_procedures, get
from denckring.eval.harness import GoldenCase, golden_cases

ROWS = (
    "anagram",
    "buchstabwechsel",
    "cut_up",
    "diastic",
    "homoconsonantism",
    "homovocalism",
    "lipogrammatic_translation",
    "melting_text",
    "mesostic",
    "n_plus_7",
    "recombination",
    "s_plus_7",
    "transposal",
    "univocalic_translation",
)

#: Rows whose checker passes a copy only for a source on which the rule has nothing
#: to do, so the copy is the one correct answer and refusing it would refuse a
#: right answer. The fix for those is a source that gives the rule work, not a
#: refusal of the copy.
COPY_IS_THE_ANSWER = {
    "cent_mille_milliards": "a source with no '|' offers one line per position: the copy",
    "wechselsatz": "a template with no '|' offers one word per slot: the copy",
    "mathews_algorithm": "a source of one paragraph is a one-row table, rotated by 0",
    "larding": "a source of one sentence has no pair to lard between",
    "text_folding": "a fold at or past the last line leaves no far flap to bring forward",
    "boustrophedon": "a one-line source has no second line to turn",
    "column_reading": "a one-column source reads back as itself",
    "slenderizing": "a source without the deleted letter loses nothing",
    "definitional_expansion": "a source with no word the pack can gloss has nothing to expand",
    "definitional_literature": "a source with no word the pack can gloss has nothing to expand",
}

#: Ordinary shapes a caller hands a source row: eight-word lines with no
#: punctuation (the bench's transform sources), and two paragraphs of prose.
LINES = "\n".join(
    [
        "river stone bread window garden market silver morning",
        "teacher horse letter summer castle water paper candle",
        "forest kitchen pocket winter music doctor table orange",
        "mountain basket rabbit pencil island mother button village",
    ]
)
PROSE = (
    "The old man walked to the harbour at dawn. His dog followed him through the fog. "
    "Nobody else was awake yet.\n\nA boat came in with fish and salt. "
    "The man bought bread and went home."
)
TINY = "Silent night"


def _string_source_cases(pid: str) -> list[GoldenCase]:
    return [
        case
        for case in golden_cases()
        if case.procedure == pid and isinstance(case.params.get("source"), str)
    ]


def _copy_passes(pid: str, lang: Lang, params: dict[str, Any], source: str) -> bool:
    try:
        return check(pid, source, lang=lang, **{**params, "source": source}).satisfied
    except DenckringError:  # a source this row refuses outright is not a copy it accepts
        return False


def _a_copy_that_passes(pid: str) -> tuple[Lang, dict[str, Any]]:
    """Golden parameters under which a copy of the golden source passes by default."""
    for case in _string_source_cases(pid):
        if _copy_passes(pid, case.lang, case.params, case.params["source"]):
            return case.lang, case.params
    raise AssertionError(f"{pid}: no golden case's source passes as its own copy")


@pytest.mark.parametrize("pid", ROWS)
def test_the_default_still_accepts_the_copy(pid: str) -> None:
    lang, params = _a_copy_that_passes(pid)
    report = check(pid, params["source"], lang=lang, **params)
    assert get(pid).params_model().model_fields["allow_identity"].default is True
    assert report.satisfied
    assert check(pid, params["source"], lang=lang, allow_identity=True, **params) == report


@pytest.mark.parametrize("pid", ROWS)
def test_refusing_identity_fails_the_copy_as_antigram_does(pid: str) -> None:
    lang, params = _a_copy_that_passes(pid)
    report = check(pid, params["source"], lang=lang, allow_identity=False, **params)
    assert not report.satisfied
    assert report.score < 1.0
    unchanged = [v for v in report.violations if v.rule == "unchanged"]
    assert len(unchanged) == 1
    # Antigram's wording, minus the "rearrangement" that is antigram's alone.
    antigram = check("antigram", "ab", source="ab").violations[-1]
    assert antigram.expected.endswith(", not the source itself")
    assert unchanged[0].expected.endswith(", not the source itself")
    assert unchanged[0].offset is None


@pytest.mark.parametrize("pid", ROWS)
def test_refusing_identity_moves_no_other_golden_verdict(pid: str) -> None:
    """Only a copy is refused: every golden case that is not one keeps its verdict
    and its score."""
    for case in _string_source_cases(pid):
        default = check(pid, case.text, lang=case.lang, **case.params)
        if default.satisfied and case.text.split() == case.params["source"].split():
            continue
        strict = check(pid, case.text, lang=case.lang, allow_identity=False, **case.params)
        assert (strict.satisfied, strict.score) == (default.satisfied, default.score), case.name


def test_a_copy_differing_in_case_spacing_and_punctuation_is_still_a_copy() -> None:
    report = check("cut_up", "THE CAT,\nsat", source="the cat sat", allow_identity=False)
    assert [v.rule for v in report.violations] == ["unchanged"]


def test_antigram_does_not_offer_the_parameter_it_has_always_refused() -> None:
    assert "allow_identity" not in get("antigram").params_model().model_fields


def _source_rows() -> list[str]:
    return [pid for pid in all_procedures() if "source" in get(pid).params_model().model_fields]


def _accepts_a_copy(pid: str) -> bool:
    cases = _string_source_cases(pid)
    for lang, params in [(case.lang, case.params) for case in cases] or [("en", {})]:
        sources = [params.get("source"), LINES, PROSE, TINY]
        if any(
            isinstance(source, str) and _copy_passes(pid, lang, params, source)
            for source in sources
        ):
            return True
    return False


def _offering() -> set[str]:
    return {
        pid for pid in _source_rows() if "allow_identity" in get(pid).params_model().model_fields
    }


def test_the_parametrised_tests_cover_every_row_that_offers_the_parameter() -> None:
    """Not the rule, which is below: this keeps `ROWS`, and so the per-row tests
    above, in step with the rows that carry the field."""
    assert _offering() == set(ROWS)


def test_every_source_row_that_accepts_a_copy_can_refuse_it_or_says_why_not() -> None:
    offering = _offering()
    accepting = {pid for pid in _source_rows() if _accepts_a_copy(pid)}
    unexplained = accepting - offering - set(COPY_IS_THE_ANSWER)
    assert not unexplained, f"rows that pass a copy with no way to refuse it: {sorted(unexplained)}"
    stale = set(COPY_IS_THE_ANSWER) - accepting
    assert not stale, f"named as passing a copy, but none passes: {sorted(stale)}"


def test_every_generator_still_refuses_its_own_input_by_default() -> None:
    """`ApplyParams.allow_identity` is `false`, and a check model mixing in
    `IdentityParams` must not hand a generator its `true`: the two share a name,
    and the base listed first decides the default."""
    for pid in all_procedures():
        procedure = get(pid)
        if isinstance(procedure, ConstructiveProcedure):
            field = procedure.apply_params_model().model_fields["allow_identity"]
            assert field.default is False, pid


#: Ruling R-U2a: `allow_identity=False` refuses a copy only where the source admits
#: a different correct answer. Per row: (lang, params, a source whose only answer is
#: the copy, or None where every source leaves another, a source that leaves
#: another, and that other answer).
GARDEN = ["aster", "bramble", "crocus", "dahlia", "elder", "fennel", "gorse", "hazel"]
EDGES: dict[str, tuple[Lang, dict[str, Any], str | None, str, str]] = {
    "anagram": ("en", {}, "aa", "ab", "ba"),
    "transposal": ("en", {}, "aa bb", "ab", "ba"),
    "buchstabwechsel": ("de", {}, None, "a", "ha"),
    "cut_up": ("en", {}, "cat", "cat sat", "sat"),
    "melting_text": ("en", {}, "cat", "cat sat", "cat"),
    "diastic": ("en", {"seed_phrase": "t"}, "the", "the cat", "the"),
    "mesostic": ("en", {"spine": "t"}, "cat", "a cat", "cat"),
    "homovocalism": ("en", {}, None, "a", "ba"),
    "homoconsonantism": ("en", {}, None, "b", "ab"),
    "lipogrammatic_translation": ("en", {"forbidden": "e"}, None, "a", "ab"),
    "univocalic_translation": ("en", {"vowel": "a"}, None, "a", "ab"),
    "recombination": (
        "en",
        {},
        "It rains. It rains.",
        "It rains. It snows.",
        "It snows. It rains.",
    ),
    "n_plus_7": ("en", {"dictionary": GARDEN}, "the cat", "the aster", "the hazel"),
    "s_plus_7": ("en", {"dictionary": GARDEN}, "the cat", "the aster", "the hazel"),
}


def test_every_carrying_row_states_its_edge() -> None:
    assert set(EDGES) == set(ROWS)


@pytest.mark.parametrize("pid", ROWS)
def test_a_copy_is_refused_only_where_another_answer_exists(pid: str) -> None:
    lang, params, only_copy, source, other = EDGES[pid]
    strict = {**params, "allow_identity": False}
    # The side that refuses: the copy fails, and the other answer it leaves passes.
    refused = check(pid, source, lang=lang, source=source, **strict)
    assert [v.rule for v in refused.violations] == ["unchanged"], refused.violations
    assert check(pid, other, lang=lang, source=source, **strict).satisfied
    # The side that does not: where the copy is the only answer, it stands.
    if only_copy is not None:
        assert check(pid, only_copy, lang=lang, source=only_copy, **strict).satisfied


def test_a_transposal_under_allow_subset_may_leave_a_letter_out() -> None:
    strict: dict[str, Any] = {"allow_identity": False, "allow_subset": True}
    assert check("anagram", "a", source="a", **strict).satisfied
    assert not check("anagram", "aa", source="aa", **strict).satisfied
    assert check("anagram", "a", source="aa", **strict).satisfied


def test_a_displacement_that_walks_back_to_its_word_leaves_only_the_copy() -> None:
    """Eight nouns, eight places on: every listed word displaces to itself."""
    report = check(
        "n_plus_7",
        "the aster",
        source="the aster",
        dictionary=GARDEN,
        offset=8,
        allow_identity=False,
    )
    assert report.satisfied


@pytest.mark.parametrize(
    "source",
    ["It rains. It rains!", "Go! Go?", "Stop. Stop, stop.", "No. No no.", "Ha. Haha.", "1. 2."],
)
def test_a_recombination_whose_every_order_has_the_copys_letters_keeps_the_copy(
    source: str,
) -> None:
    """Two sentences to the checker, one letter string to `unchanged`: every
    reorder is the copy again, so nothing else could pass."""
    assert check("recombination", source, source=source, allow_identity=False).satisfied


def test_a_recombination_reorder_with_other_letters_is_the_answer_left() -> None:
    source = "No. No yes."
    assert not check("recombination", source, source=source, allow_identity=False).satisfied
    assert check("recombination", "No yes. No.", source=source, allow_identity=False).satisfied
