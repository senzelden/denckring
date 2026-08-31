"""`apply` gets the checks `check` has had all along.

Before this, every generator hand-rolled its own preamble and each forgot
something different: `cut_up` never validated parameters, four hand-rolled
`require_capability`, and all 27 let `seed` bind to the signature where pydantic
could never see it.
"""

import inspect
from typing import Any

import pytest
from pydantic import BaseModel

from denckring import describe
from denckring.core.base import ApplyParams, ConstructiveProcedure, plain
from denckring.core.errors import DegenerateOutput, InvalidParams
from denckring.core.protocol import LanguagePack, Produced, Report
from denckring.core.registry import all_procedures, get


def constructive(pid: str) -> ConstructiveProcedure[Any, Any]:
    """`get` is typed as the base class, which has no `apply` — narrow it once here.

    The same `assert isinstance` every other suite does before calling a
    generator; only the type it narrows to has moved. Generalised from a
    `cut_up`-only helper once Task 4 put real non-drawing generators on the
    spine for `test_a_procedure_that_does_not_draw_refuses_a_seed` to narrow too.
    """
    procedure = get(pid)
    assert isinstance(procedure, ConstructiveProcedure)
    return procedure


def cut_up() -> ConstructiveProcedure[Any, Any]:
    return constructive("cut_up")


def test_cut_up_is_on_the_spine() -> None:
    assert isinstance(get("cut_up"), ConstructiveProcedure)


def test_cut_up_refuses_an_unknown_parameter() -> None:
    """It accepted anything at all, because it never called parse_params."""
    with pytest.raises(InvalidParams) as caught:
        cut_up().apply("one two three four", nonsense=1)
    assert "nonsense" in str(caught.value)


def test_seed_is_type_checked_now_it_is_a_field() -> None:
    """As a signature keyword it bound before `**params` and was never validated,
    so every generator accepted `seed="not-an-int"`."""
    with pytest.raises(InvalidParams):
        cut_up().apply("one two three four", seed="not-an-int")


def test_seed_still_fixes_the_draw() -> None:
    text = "one two three four five six seven eight"
    assert cut_up().apply(text, seed=7) == cut_up().apply(text, seed=7)


def test_a_second_source_is_refused_rather_than_silently_losing_one() -> None:
    """`apply` supplies `source` from the text it is transforming, so a caller who
    supplies one too has named two sources; only one can be used and nothing would
    say which. `cut_up` reads `text`, so this is invisible until Task 4 migrates a
    generator whose `_produce` reads `params.source` — hence closed now."""
    with pytest.raises(InvalidParams) as caught:
        cut_up().apply("one two three", source="four five six")
    assert "source" in str(caught.value)


def test_apply_params_are_visible_to_a_non_python_caller() -> None:
    """The point of a field over a signature keyword: it reaches the schema, and
    the schema reaches a caller who cannot import the model.

    Asserted through `describe()` — what `denckring describe` prints and what
    MCP's `describe_procedure` returns — rather than through
    `apply_params_model().model_json_schema()`, which is the Python path this
    test took while its name claimed the other one. ADR 0025 said `seed`
    reached `params_schema()`; it did not, and until `Description.apply_params`
    no non-Python surface carried it at all.
    """
    described = describe("cut_up")
    assert "seed" in described.apply_params["properties"]
    assert "allow_identity" in described.apply_params["properties"]
    assert "seed" not in described.params["properties"]


#: pytest's own "pid" spelling, not "procedure_id" — the shared conftest's
#: pytest_generate_tests auto-parametrises any argument literally named
#: "procedure_id", and colliding with it raises "duplicate parametrization".
DOES_NOT_DRAW = [
    "anagram",
    "boustrophedon",
    "column_reading",
    "diastic",
    "every_nth_word",
    "fold_in",
    "haikuization",
    "mathews_algorithm",
    "mesostic",
    "n_plus_7",
    "paragram",
    "pasigraphy",
    "proteus_verse",
    "s_plus_7",
    "slenderizing",
    "spoonerism",
    "text_folding",
    "word_ladder",
]


@pytest.mark.parametrize("pid", DOES_NOT_DRAW)
def test_a_procedure_that_does_not_draw_refuses_a_seed(pid: str) -> None:
    """It accepted one before and ignored it, which is the worse of the two.

    Asserts the message names `seed`, not merely that some `InvalidParams` was
    raised: `pasigraphy`, `slenderizing` and `word_ladder` each have a required
    field of their own (`table`, `deleted`, `target`) that this call never
    supplies either, so a bare `pytest.raises(InvalidParams)` would stay green
    for those three even if `seed` were silently accepted and the failure came
    from the missing field instead.
    """
    with pytest.raises(InvalidParams) as caught:
        constructive(pid).apply("one two three four five", seed=3)
    assert "seed" in str(caught.value)


DRAWS = [
    "arca_musarithmica",
    "cent_mille_milliards",
    "cut_up",
    "denckring",
    "ideenwuerfeln",
    "llull_figure",
    "melting_text",
    "poesie_automat",
    "recombination",
    "wechselsatz",
]


@pytest.mark.parametrize("pid", DRAWS)
def test_a_procedure_that_draws_carries_seed_as_a_field(pid: str) -> None:
    model = constructive(pid).apply_params_model()
    assert "seed" in model.model_fields
    assert "seed" in model.model_json_schema()["properties"]


@pytest.mark.parametrize("pid", DRAWS)
def test_a_drawn_seed_is_type_checked(pid: str) -> None:
    """Asserts the message names `seed`, not merely that some `InvalidParams` was
    raised: `arca_musarithmica` also requires `pinakes`, which this call never
    supplies, so a bare `pytest.raises(InvalidParams)` would stay green for that
    row even if `seed` were silently accepted and the failure came from the
    missing field instead — the same hazard `test_a_procedure_that_does_not_draw_refuses_a_seed`
    above already guards against."""
    with pytest.raises(InvalidParams) as caught:
        constructive(pid).apply("one two three\nfour five six\n", seed="not-an-int")
    assert "seed" in str(caught.value)


def test_the_two_sets_partition_the_generators() -> None:
    """No generator may be in both lists or in neither."""
    assert set(DRAWS) & set(DOES_NOT_DRAW) == set()
    generators = {
        pid for pid, p in all_procedures().items() if isinstance(p, ConstructiveProcedure)
    }
    assert set(DRAWS) | set(DOES_NOT_DRAW) == generators


@pytest.mark.parametrize("pid", sorted(all_procedures()))
def test_every_generator_is_on_the_spine(pid: str) -> None:
    """Unscoped now that Task 5 has migrated the ten that draw: every one of
    the 27 constructive rows, not merely `DOES_NOT_DRAW`'s seventeen, must
    inherit the spine rather than hand-roll `apply`. A row with no `apply` at
    all (most of the catalogue) is not a candidate for this check, hence the
    guard before the nominal assertion — a plain `getattr` rather than
    `isinstance(procedure, Constructive)`, which chained against the
    `ConstructiveProcedure` assert below makes `mypy --strict` report the
    assert unreachable (it reasons the narrowed intersection type could not
    exist, the same finding Task 4 hit and worked around the same way)."""
    procedure = all_procedures()[pid]
    if getattr(procedure, "apply", None) is None:
        return
    assert isinstance(procedure, ConstructiveProcedure), (
        f"{pid} defines apply() without inheriting the spine"
    )


@pytest.mark.parametrize("pid", sorted(all_procedures()))
def test_no_generator_hand_rolls_the_preamble(pid: str) -> None:
    """The spine does the pack, the capabilities and the parameters. A `_produce`
    that does any of it again has a second opinion the spine cannot see.

    Read `_produce`, not `_apply` — Task 3 moved the generation primitive, and
    the hazard this guards against moved with it.
    """
    procedure = all_procedures()[pid]
    if not isinstance(procedure, ConstructiveProcedure):
        return
    body = inspect.getsource(type(procedure)._produce)
    for forbidden in ("get_pack(", "parse_params(", "require_capability("):
        assert forbidden not in body, f"{pid}._produce still calls {forbidden}"


def test_every_generator_defines_produce_and_not_apply() -> None:
    """One primitive. Two would mean every consumer has to ask which a given
    procedure implements — the seam this codebase has twice had to remove."""
    for pid, procedure in sorted(all_procedures().items()):
        if not isinstance(procedure, ConstructiveProcedure):
            continue
        assert "_produce" in type(procedure).__dict__, f"{pid} does not define _produce"
        assert "_apply" not in type(procedure).__dict__, f"{pid} still defines _apply"


def test_the_base_class_has_no_apply_primitive_left() -> None:
    assert not hasattr(ConstructiveProcedure, "_apply")


@pytest.mark.parametrize("pid", sorted(DRAWS + DOES_NOT_DRAW))
def test_produce_is_annotated_as_returning_produced(pid: str) -> None:
    """Catches a generator migrated in body but not in signature — the annotation
    is what `mypy --strict` reads, and a stale `-> str` there passes at runtime.

    `Produced` rather than `list[str]` since ADR 0027. This ranges over the
    DRAWS/DOES_NOT_DRAW split rather than the registry, so it is also what
    catches a generator that fell out of either list."""
    procedure = get(pid)
    assert isinstance(procedure, ConstructiveProcedure)
    signature = inspect.signature(type(procedure)._produce)
    assert signature.return_annotation in ("Produced", Produced)


class _EmptyParams(BaseModel):
    pass


class _EmptyApplyParams(_EmptyParams, ApplyParams):
    pass


class _ProducesNothing(ConstructiveProcedure[_EmptyParams, _EmptyApplyParams]):
    """A throwaway procedure whose `_produce` finds no candidate at all.

    Reuses `cut_up`'s catalogue id rather than inventing one: `catalogue.get`
    only needs a row that exists, and this class is never `@register`ed, so it
    never touches the real registry `cut_up` lives in.
    """

    id = "cut_up"

    @classmethod
    def params_model(cls) -> type[_EmptyParams]:
        return _EmptyParams

    def _check(self, text: str, pack: LanguagePack, params: _EmptyParams) -> Report:
        raise NotImplementedError

    @classmethod
    def apply_params_model(cls) -> type[_EmptyApplyParams]:
        return _EmptyApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: _EmptyApplyParams) -> Produced:
        return Produced(candidates=[])


def test_an_empty_produce_raises_degenerate_output_naming_nothing() -> None:
    """Task 2's reviewer found this hole: an empty list is not a candidate
    `_guard_degenerate` judged and rejected, it is no candidate at all, and
    `observed` must say that rather than defaulting to `IDENTICAL` — which
    would be false, since there was nothing to compare against the input."""
    with pytest.raises(DegenerateOutput) as caught:
        _ProducesNothing().produce("some text")
    assert caught.value.observed == DegenerateOutput.NOTHING


def test_allow_identity_cannot_waive_an_empty_produce() -> None:
    """`allow_identity` waives a candidate the caller judged degenerate but
    still wanted; an empty list offers no candidate to want, so the flag must
    not reach it. Checked ahead of `_guard_degenerate`, not through it — see
    `ConstructiveProcedure.produce`."""
    with pytest.raises(DegenerateOutput) as caught:
        _ProducesNothing().produce("some text", allow_identity=True)
    assert caught.value.observed == DegenerateOutput.NOTHING


class _ProducesTheInputCasefolded(_ProducesNothing):
    """A throwaway procedure that returns its input with the case flattened.

    `anagram` is the real one — its covers are built from a casefolded lexicon —
    but the hole was the spine's, so it is pinned here on a double rather than
    only on the row that fell into it.
    """

    def _produce(self, text: str, pack: LanguagePack, params: _EmptyApplyParams) -> Produced:
        return plain([text.casefold()])


def test_output_differing_from_the_input_only_in_case_is_degenerate() -> None:
    """The guard compared case-sensitively, so a casefolding generator handed
    back its own input and was never caught: `anagram.apply("Dormitory")`
    returned `dormitory`, which is the defect the guard exists to refuse."""
    with pytest.raises(DegenerateOutput) as caught:
        _ProducesTheInputCasefolded().produce("Some Text")
    assert caught.value.observed == DegenerateOutput.IDENTICAL


def test_allow_identity_still_waives_a_case_only_difference() -> None:
    """Widening what counts as the identity must not narrow the escape from it:
    a caller who asked for the degenerate result still gets it."""
    production = _ProducesTheInputCasefolded().produce("Some Text", allow_identity=True)
    assert production.texts == ["some text"]
