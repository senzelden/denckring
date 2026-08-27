# The Apply Spine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `apply()` the template method `check()` already has, so no generator can forget its pack, its capabilities, its parameters, or that it must actually transform its input.

**Architecture:** A new `ConstructiveProcedure` base class in `core/base.py` carries a concrete `apply()` that resolves the pack, enforces `meta.requires` and a new `meta.apply_requires`, validates parameters through pydantic, and refuses output identical to the input. The 27 generators rename `apply` → `_apply` and delete their hand-rolled preambles. `seed` stops being a signature keyword — where it was unvalidatable — and becomes an ordinary field on a `SeedParams` mixin carried only by the ten procedures that draw at random.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, hypothesis, mypy, ruff, uv.

**Spec:** `docs/superpowers/specs/2026-08-27-apply-spine-design.md`

## Global Constraints

- **Python floor is 3.11.** PEP 696 TypeVar defaults are 3.13+ and must not be used.
- **One module per procedure, module name == procedure id.** Enforced by `register` in `core/registry.py` — see ADR 0007.
- **`check()` behaviour must not change.** No task in this plan may alter what any checker accepts or rejects. The round-trip suite and all golden fixtures stay green throughout.
- **No generator's output may change**, except the four in Task 7 that currently return their input and will start raising instead.
- **Every new error class needs a unique, stable, snake_case `code`.** `tests/test_error_codes.py` asserts this.
- **Comments explain why, not what.** This codebase's comments carry reasoning and cite ADRs; match that register.
- **Gate before every commit:** `uv run pytest -q`, `uv run mypy src`, `uv run ruff check .`
- **The 27 generators** are: `anagram`, `arca_musarithmica`, `boustrophedon`, `cent_mille_milliards`, `column_reading`, `cut_up`, `denckring`, `diastic`, `every_nth_word`, `fold_in`, `haikuization`, `ideenwuerfeln`, `llull_figure`, `mathews_algorithm`, `melting_text`, `mesostic`, `n_plus_7`, `paragram`, `pasigraphy`, `poesie_automat`, `recombination`, `s_plus_7`, `slenderizing`, `spoonerism`, `text_folding`, `wechselsatz`, `word_ladder`.
- **The ten that draw at random** (and only these get `SeedParams`): `arca_musarithmica`, `cent_mille_milliards`, `cut_up`, `denckring`, `ideenwuerfeln`, `llull_figure`, `melting_text`, `poesie_automat`, `recombination`, `wechselsatz`.
- **The nine that declare a generative `kind` with no generator:** `buchstabwechsel`, `definitional_expansion`, `definitional_literature`, `homoconsonantism`, `homovocalism`, `larding`, `lipogrammatic_translation`, `tmesis`, `univocalic_translation`.

---

### Task 1: `apply_requires` — the field with nowhere to live

`anagram.apply` uses the word lexicon and cannot say so: `meta.requires` gates `check` too, and adding `lexicon.words` there would break a checker that has always run on core alone. Its own docstring explains this. The fix is a second field.

**Files:**
- Modify: `src/denckring/core/protocol.py` (the `Meta` model)
- Modify: `src/denckring/core/describe.py` (`Description`, `describe`, new `apply_runnable`)
- Modify: `src/denckring/data/catalogue.yaml` (the `anagram` row)
- Modify: `src/denckring/procedures/anagram.py:120-128` (the docstring paragraph that explains the workaround)
- Test: `tests/test_apply_requires.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `Meta.apply_requires: list[str]`; `denckring.core.describe.apply_runnable(meta, lang) -> tuple[bool, list[str]]`; `Description.apply_missing: list[str]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_apply_requires.py`:

```python
"""The generator's requirements are not the checker's.

`anagram` checks with core alone and generates only with a word lexicon. One
`requires` list could not say both, so the generator's need went undeclared and
`missing` reported nothing — the defect this file pins.
"""

import pytest

from denckring import check, describe
from denckring.core import catalogue
from denckring.core.describe import apply_runnable
from denckring.lang.en import EnglishPack


def test_anagram_declares_the_lexicon_its_generator_uses() -> None:
    assert "lexicon.words" in catalogue.get("anagram").apply_requires


def test_declaring_it_does_not_gate_the_checker() -> None:
    """The whole reason it could not go in `requires`. A core-only install must
    still check an anagram."""
    assert "lexicon.words" not in catalogue.get("anagram").requires
    report = check("anagram", "silent", source="listen")
    assert report.satisfied


def test_apply_runnable_reports_what_the_generator_lacks() -> None:
    meta = catalogue.get("anagram")
    core_only = EnglishPack()
    assert "lexicon.words" not in core_only.capabilities
    ok, missing = apply_runnable(meta, pack=core_only)
    assert not ok
    assert missing == ["lexicon.words"]


def test_apply_missing_reaches_the_description() -> None:
    described = describe("anagram")
    assert hasattr(described, "apply_missing")
    assert isinstance(described.apply_missing, list)


def test_rows_without_a_generator_requirement_default_to_empty() -> None:
    assert catalogue.get("lipogram").apply_requires == []


@pytest.mark.parametrize("procedure_id", sorted(catalogue.ids()))
def test_apply_requires_names_only_real_capabilities(procedure_id: str) -> None:
    """Matches the existing rule for `requires`: a capability no pack can answer
    is a promise the catalogue cannot keep."""
    known = {
        "tokens", "alphabet", "fold_diacritics", "letter_shapes",
        "syllables", "syllables.heuristic", "syllables.dictionary",
        "phonemes", "stress", "lexicon.words", "lexicon.nouns", "lexicon.glosses",
    }
    assert set(catalogue.get(procedure_id).apply_requires) <= known
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_apply_requires.py -v`
Expected: FAIL — `AttributeError: 'Meta' object has no attribute 'apply_requires'`, and `ImportError` for `apply_runnable`.

- [ ] **Step 3: Add the field to `Meta`**

In `src/denckring/core/protocol.py`, in `class Meta`, directly after the existing `requires` line:

```python
    requires: list[str] = Field(default_factory=list)
    #: What the *generator* needs, which is not what the checker needs.
    #: `anagram` checks with core alone and generates only with a word lexicon;
    #: one list could not say both, so the generator's requirement went
    #: undeclared and `missing` reported nothing. ADR 0002 makes `apply` the
    #: optional half, and this is the field that lets the optional half be
    #: honest about its own cost.
    apply_requires: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Add `apply_runnable` and `apply_missing` to describe**

In `src/denckring/core/describe.py`, add after the existing `runnable` function:

```python
def apply_runnable(meta: Meta, lang: Lang = "en", *, pack: LanguagePack | None = None) -> tuple[bool, list[str]]:
    """Whether this install can *generate* with the procedure, and what it lacks.

    Separate from `runnable` because the two halves have different costs: a
    core-only install checks an anagram perfectly well and cannot generate one.
    Takes an optional pack so a test can ask about an install it is not running.
    """
    if pack is None:
        from denckring.lang import get_pack

        try:
            pack = get_pack(lang)
        except Exception:
            return False, [*meta.requires, *meta.apply_requires]
    missing = [
        capability
        for capability in (*meta.requires, *meta.apply_requires)
        if capability not in pack.capabilities
    ]
    return not missing, missing
```

Add the import at the top of the file: `from denckring.core.protocol import Lang, LanguagePack, Meta`.

In `class Description`, after the `missing: list[str]` line:

```python
    apply_requires: list[str]
    apply_missing: list[str]
```

In `describe()`, after the existing `ok, missing = runnable(meta, lang)`:

```python
    _, apply_missing = apply_runnable(meta, lang)
```

and add to the `Description(...)` construction:

```python
        apply_requires=list(meta.apply_requires),
        apply_missing=apply_missing,
```

- [ ] **Step 5: Declare it on the anagram row**

In `src/denckring/data/catalogue.yaml`, find the row with `id: anagram` and add beneath its existing `requires:` block:

```yaml
    apply_requires:
      - lexicon.words
```

- [ ] **Step 6: Correct the docstring that documented the workaround**

In `src/denckring/procedures/anagram.py`, replace the paragraph in `apply`'s docstring beginning "`lexicon.words` is required here but deliberately NOT added" with:

```
        `lexicon.words` is declared on the catalogue row's `apply_requires`, not
        its `requires`: the latter gates `check` too, and `check` has always run
        on core alone. ADR 0002 makes `apply` the optional half, and
        `apply_requires` is how the optional half states its own cost.
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_apply_requires.py -v && uv run pytest -q && uv run mypy src && uv run ruff check .`
Expected: PASS throughout. The full suite must stay green — nothing here changes behaviour.

- [ ] **Step 8: Commit**

```bash
git add src/denckring/core/protocol.py src/denckring/core/describe.py \
        src/denckring/data/catalogue.yaml src/denckring/procedures/anagram.py \
        tests/test_apply_requires.py
git commit -m "feat: apply_requires, so the generator can state a cost the checker does not pay"
```

---

### Task 2: Tell the truth about the nine

Nine rows declare `kind: both` and have no generator. `kind` is right — a homoconsonantism genuinely can be generated — so the catalogue is not what is wrong. What is wrong is that nothing reports whether *this install* has a generator, so `describe` says `missing: []` and `apply_procedure` then answers `not_constructive`.

**Files:**
- Modify: `src/denckring/core/describe.py` (`Description`, `Summary`, `describe`, `summaries`)
- Modify: `src/denckring/mcp/server.py:82-84` (the docstring claiming sixteen)
- Modify: `src/denckring/cli.py:141-144` (the self-contradicting message)
- Test: `tests/test_constructive_truth.py` (create)

**Interfaces:**
- Consumes: `Description.apply_missing` from Task 1.
- Produces: `Description.constructive: bool`, `Summary.constructive: bool`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_constructive_truth.py`:

```python
"""`kind` is a claim about the form; `constructive` is a claim about the install.

Nine rows say `kind: both` and have no generator behind them. Rewriting `kind`
would trade a true statement about the form for a true statement about the
install and lose the first, so both are reported.
"""

import pytest

from denckring import describe, summaries
from denckring.core.protocol import Constructive
from denckring.core.registry import all_procedures

WITHOUT_GENERATORS = {
    "buchstabwechsel", "definitional_expansion", "definitional_literature",
    "homoconsonantism", "homovocalism", "larding", "lipogrammatic_translation",
    "tmesis", "univocalic_translation",
}


@pytest.mark.parametrize("procedure_id", sorted(all_procedures()))
def test_constructive_matches_reality(procedure_id: str) -> None:
    """The assertion that stops the nine drifting again."""
    expected = isinstance(all_procedures()[procedure_id], Constructive)
    assert describe(procedure_id).constructive is expected


def test_the_nine_say_both_things_at_once() -> None:
    for procedure_id in sorted(WITHOUT_GENERATORS):
        described = describe(procedure_id)
        assert described.kind in {"constructive", "both"}, procedure_id
        assert described.constructive is False, procedure_id


def test_summaries_carry_it_too() -> None:
    rows = {row.id: row for row in summaries()}
    assert rows["anagram"].constructive is True
    assert rows["homoconsonantism"].constructive is False


def test_the_count_of_generators_is_twenty_seven() -> None:
    """`apply_procedure`'s docstring claimed sixteen. Pin the real number so the
    prose cannot drift from it again."""
    generators = [p for p in all_procedures().values() if isinstance(p, Constructive)]
    assert len(generators) == 27
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_constructive_truth.py -v`
Expected: FAIL — `AttributeError: 'Description' object has no attribute 'constructive'`.

- [ ] **Step 3: Add `constructive` to the models**

In `src/denckring/core/describe.py`, add to `class Summary` after `kind: str`:

```python
    constructive: bool
```

and to `class Description` after `kind: str`:

```python
    #: Whether *this install* has a generator. Distinct from `kind`, which says
    #: whether the form admits one at all: nine rows are honestly `both` and
    #: honestly have no `apply` here, and a single field could not say both.
    constructive: bool
```

- [ ] **Step 4: Populate it**

In `describe()`, add near the top after `procedure = get(procedure_id)`:

```python
    from denckring.core.protocol import Constructive

    is_constructive = isinstance(procedure, Constructive)
```

and pass `constructive=is_constructive,` in the `Description(...)` construction.

In `summaries()`, inside the loop, add `from denckring.core.protocol import Constructive` at the top of the module and pass to `Summary(...)`:

```python
                constructive=isinstance(get(procedure_id), Constructive),
```

- [ ] **Step 5: Correct the two messages that contradict themselves**

In `src/denckring/mcp/server.py`, replace the second paragraph of `apply_procedure_tool`'s docstring:

```
    Twenty-seven of the procedures have a generator here. `kind` says whether the
    form admits one; `constructive` in `describe_procedure` says whether this
    install has it. Read `constructive`, not `kind`, before calling this.
```

In `src/denckring/cli.py:141-144`, replace the message body:

```python
        typer.echo(
            f"Procedure {procedure_id!r} has no generator in this install. "
            f"Its kind is {procedure.meta.kind}, so the form admits one, but none is "
            f"implemented here — see `describe {procedure_id}`, field `constructive`."
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_constructive_truth.py -v && uv run pytest -q && uv run mypy src && uv run ruff check .`
Expected: PASS. Note `tests/test_mcp_tools.py` and `tests/test_describe.py` may need updating if they assert on exact model fields — update them rather than weakening the new assertions.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/core/describe.py src/denckring/mcp/server.py \
        src/denckring/cli.py tests/test_constructive_truth.py
git commit -m "feat: describe says whether this install has a generator, not only whether the form admits one"
```

---

### Task 3: The spine, and `cut_up` as its pilot

`cut_up` is the worst of the 27 and therefore the right pilot: it never calls `parse_params` so it accepts any parameter at all, and it carries `CutUpApplyParams` — a params model for the apply half that nothing has ever used. It also draws at random, so it exercises `SeedParams` in the same task.

The round-trip harness calls `apply(text, lang=lang, seed=0)` on all 27. Once any deterministic procedure stops accepting `seed`, those calls raise `InvalidParams`, which is a `DenckringError` and would be swallowed by the harness's `except DenckringError: continue` — silently making the property vacuous for 17 rows. The harness is therefore fixed in this task, before any migration can hide behind it.

**Files:**
- Modify: `src/denckring/core/base.py` (add `SeedParams`, `ApplyParams`, `ConstructiveProcedure`; extract `_parse`)
- Modify: `src/denckring/core/protocol.py` (the `Constructive` protocol signature)
- Modify: `src/denckring/procedures/cut_up.py`
- Modify: `tests/test_round_trip.py`
- Test: `tests/test_apply_spine.py` (create)

**Interfaces:**
- Consumes: `Meta.apply_requires` from Task 1.
- Produces:
  - `denckring.core.base.SeedParams` — field `seed: int | None = None`
  - `denckring.core.base.ApplyParams` — field `allow_identity: bool = False`
  - `denckring.core.base.ConstructiveProcedure(BaseProcedure[P], Generic[P, A])` with
    `apply(self, text: str, *, lang: Lang = "en", **params: Any) -> str`,
    abstract `_apply(self, text: str, pack: LanguagePack, params: A) -> str`,
    classmethod `apply_params_model(cls) -> type[A]`,
    and `parse_apply_params(self, text: str, params: dict[str, Any]) -> A`.
  - `Constructive.apply` protocol signature loses its explicit `seed`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_apply_spine.py`:

```python
"""`apply` gets the checks `check` has had all along.

Before this, every generator hand-rolled its own preamble and each forgot
something different: `cut_up` never validated parameters, four hand-rolled
`require_capability`, and all 27 let `seed` bind to the signature where pydantic
could never see it.
"""

import pytest

from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams
from denckring.core.errors import InvalidParams
from denckring.core.registry import get


def test_cut_up_is_on_the_spine() -> None:
    assert isinstance(get("cut_up"), ConstructiveProcedure)


def test_cut_up_refuses_an_unknown_parameter() -> None:
    """It accepted anything at all, because it never called parse_params."""
    with pytest.raises(InvalidParams) as caught:
        get("cut_up").apply("one two three four", nonsense=1)
    assert "nonsense" in str(caught.value)


def test_seed_is_type_checked_now_it_is_a_field() -> None:
    """As a signature keyword it bound before `**params` and was never validated,
    so every generator accepted `seed="not-an-int"`."""
    with pytest.raises(InvalidParams):
        get("cut_up").apply("one two three four", seed="not-an-int")


def test_seed_still_fixes_the_draw() -> None:
    text = "one two three four five six seven eight"
    assert get("cut_up").apply(text, seed=7) == get("cut_up").apply(text, seed=7)


def test_the_mixins_carry_what_they_say() -> None:
    assert SeedParams.model_fields["seed"].default is None
    assert ApplyParams.model_fields["allow_identity"].default is False


def test_apply_params_are_visible_to_a_non_python_caller() -> None:
    """The point of a field over a signature keyword: it reaches the schema."""
    schema = get("cut_up").apply_params_model().model_json_schema()
    assert "seed" in schema["properties"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_apply_spine.py -v`
Expected: FAIL — `ImportError: cannot import name 'ApplyParams' from 'denckring.core.base'`.

- [ ] **Step 3: Add the mixins and the spine**

In `src/denckring/core/base.py`, add after the existing `SourceParams` class:

```python
class SeedParams(BaseModel):
    """Mixed into every procedure that draws at random.

    A field, not a signature keyword. `Constructive.apply` used to name `seed`
    explicitly, and Python binds a keyword matching an explicit parameter to that
    parameter before any of it reaches `**params` — silently. So `seed` reached
    no params model, pydantic never typed it, and all 27 generators accepted
    `seed="not-an-int"`. `diastic` documented the collision and renamed its own
    field around it; this removes the collision instead.

    Carried only by the ten procedures that draw, so `seed` cannot be passed to
    the other seventeen at all — the same exclusion-by-type ADR 0009 gives
    `fold_diacritics`.
    """

    seed: int | None = Field(
        default=None, description="Fixes the draw, for a repeatable result."
    )


class ApplyParams(BaseModel):
    """Mixed into every generator's apply-params model.

    A generator that returns its input has not run the procedure, and says
    nothing a caller can act on. Refusing it is the default; `allow_identity`
    is for the caller who genuinely wants the degenerate case.
    """

    allow_identity: bool = Field(
        default=False,
        description="Permit output identical to the input, which normally means the procedure did not run.",
    )
```

Add `A = TypeVar("A", bound=BaseModel)` beside the existing `P` TypeVar, and `from typing import cast` to the imports.

Refactor `BaseProcedure.parse_params` so the spine can reuse its validation. Replace the body with a call to a new module-level helper, keeping `parse_params`' behaviour and error text exactly as they are:

```python
def parse_into(
    model: type[BaseModel], params: dict[str, Any], procedure_id: str
) -> BaseModel:
    """Validate `params` against `model`, raising `InvalidParams` either way.

    Extracted from `BaseProcedure.parse_params` so `apply` validates by exactly
    the rule `check` does. Silently dropping a mistyped parameter would let a
    caller believe a constraint was applied when it was not.
    """
    unknown = sorted(set(params) - set(model.model_fields))
    if unknown:
        raise InvalidParams(
            procedure_id,
            f"unknown parameter(s) {unknown}; this procedure accepts "
            f"{sorted(model.model_fields)}",
        )
    try:
        return model.model_validate(params)
    except ValidationError as exc:
        raise InvalidParams(procedure_id, str(exc)) from exc
```

and make `parse_params` delegate:

```python
    def parse_params(self, params: dict[str, Any]) -> P:
        """Validate parameters, raising `InvalidParams` like `check` does."""
        return cast(P, parse_into(self.params_model(), params, self.id))
```

Then add the spine at the end of the module:

```python
class ConstructiveProcedure(BaseProcedure[P], Generic[P, A]):
    """A procedure that generates as well as checks.

    `apply` is the template method `check` has always had: it resolves the pack,
    enforces both capability lists, validates parameters, and refuses output
    identical to the input — so an individual procedure module cannot forget any
    of it. ADR 0002 is amended rather than reversed: `apply` is still optional,
    but a procedure that has one inherits this.
    """

    @classmethod
    def apply_params_model(cls) -> type[A]:
        """The parameters `apply` accepts.

        Defaults to the checker's model widened by `ApplyParams`. A generator
        with parameters of its own — a seed, a target word — declares its own
        model and inherits `ApplyParams` explicitly.
        """
        combined = create_model(
            f"{cls.__name__}ApplyParams", __base__=(cls.params_model(), ApplyParams)
        )
        return cast(type[A], combined)

    def parse_apply_params(self, text: str, params: dict[str, Any]) -> A:
        """Validate, supplying `source` from the text being transformed.

        Every generator did this by hand as `parse_params({"source": text,
        **params})`. Doing it here is what makes it impossible to forget.
        """
        model = self.apply_params_model()
        if "source" in model.model_fields:
            params = {"source": text, **params}
        return cast(A, parse_into(model, params, self.id))

    @abstractmethod
    def _apply(self, text: str, pack: LanguagePack, params: A) -> str:
        """Procedure-specific generation. Language and parameters are already valid."""

    def apply(self, text: str, *, lang: Lang = "en", **params: Any) -> str:
        """Generate text with this procedure."""
        from denckring.lang import get_pack

        pack = get_pack(lang)
        for capability in (*self.meta.requires, *self.meta.apply_requires):
            require_capability(pack, capability, self.id)
        parsed = self.parse_apply_params(text, params)
        return self._guard_degenerate(text, self._apply(text, pack, parsed), parsed)

    def _guard_degenerate(self, text: str, produced: str, params: A) -> str:
        """Deliberately inert here, so this task changes no generator's output.

        Task 6 gives it teeth once every generator is on the spine; enforcing it
        before the migration would fail rows for a reason unrelated to the
        migration, and the two would be indistinguishable in the same commit.
        """
        return produced
```

Add `from pydantic import BaseModel, Field, ValidationError, create_model` to the imports.

- [ ] **Step 4: Widen the `Constructive` protocol**

In `src/denckring/core/protocol.py`, replace the `Constructive.apply` signature:

```python
    def apply(self, text: str, *, lang: Lang = "en", **params: Any) -> str: ...
```

and extend its docstring with:

```
    `seed` was an explicit keyword here and is now an ordinary parameter on
    `SeedParams`, carried by the ten procedures that draw. A keyword named in
    this signature binds before `**params` and so can never be validated, which
    is what made `seed` unvalidatable for all 27.
```

- [ ] **Step 5: Migrate `cut_up`**

In `src/denckring/procedures/cut_up.py`, replace `CutUpApplyParams` (which nothing used) and the class declaration and `apply`:

```python
class CutUpApplyParams(CutUpParams, SeedParams, ApplyParams):
    """What the scissors accept. `CutUpParams` alone could not carry `seed`,
    because `seed` was a signature keyword no params model ever saw."""


@register
class CutUp(ConstructiveProcedure[CutUpParams, CutUpApplyParams]):
```

```python
    @classmethod
    def apply_params_model(cls) -> type[CutUpApplyParams]:
        return CutUpApplyParams

    def _apply(self, text: str, pack: LanguagePack, params: CutUpApplyParams) -> str:
        """Shuffle the source's own words. Deterministic under a fixed seed."""
        words = [word for _, word in word_spans(text, pack)]
        random.Random(params.seed).shuffle(words)
        return " ".join(words)
```

Update the imports to bring in `ApplyParams`, `ConstructiveProcedure`, `SeedParams` from `denckring.core.base`, and drop the now-unused `Lang` import if ruff flags it.

- [ ] **Step 6: Fix the round-trip harness before it can hide a regression**

In `tests/test_round_trip.py`, add a helper after `_check_args` and use it at all three `apply` call sites:

```python
def _apply_args(procedure_id: str, seed: int) -> dict[str, int]:
    """`seed` only where the procedure draws.

    It used to be a signature keyword every generator accepted and none
    validated. Now it is a field on the ten that randomise, so passing it to the
    other seventeen is an `InvalidParams` — which this harness would swallow in
    its `except DenckringError`, making the property silently vacuous for those
    seventeen rows.
    """
    procedure = all_procedures()[procedure_id]
    model = procedure.apply_params_model() if hasattr(procedure, "apply_params_model") else None
    return {"seed": seed} if model is not None and "seed" in model.model_fields else {}
```

Replace `procedure.apply(text, lang=lang, seed=0)` with `procedure.apply(text, lang=lang, **_apply_args(procedure_id, 0))` in both `collect` and `test_apply_output_satisfies_check`, and `seed=7` likewise in `test_apply_is_deterministic_under_a_fixed_seed`.

Add to that last test's docstring:

```
    For the seventeen procedures that do not draw, this asserts only that two
    identical calls agree — which is what determinism means for them, and is now
    checked rather than assumed via a seed they ignored.
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_apply_spine.py tests/test_round_trip.py tests/test_cut_up.py -v && uv run pytest -q && uv run mypy src && uv run ruff check .`
Expected: PASS. If `test_the_named_coverage_gap_is_the_whole_coverage_gap` fails, it is telling you a row became unreachable — read its message and fix the cause, do not widen `PARAMETER_GATED`.

- [ ] **Step 8: Commit**

```bash
git add src/denckring/core/base.py src/denckring/core/protocol.py \
        src/denckring/procedures/cut_up.py tests/test_round_trip.py \
        tests/test_apply_spine.py
git commit -m "feat: the apply spine, and cut_up as its first inhabitant"
```

---

### Task 4: Migrate the seventeen that do not draw

Mechanical and repetitive. Each procedure: change the base class, add `_apply` in place of `apply`, delete the preamble. None of them gains `SeedParams`, so each stops accepting `seed` — which is the intended behaviour change, and why the harness was fixed first.

**The seventeen:** `anagram`, `boustrophedon`, `column_reading`, `diastic`, `every_nth_word`, `fold_in`, `haikuization`, `mathews_algorithm`, `mesostic`, `n_plus_7`, `paragram`, `pasigraphy`, `s_plus_7`, `slenderizing`, `spoonerism`, `text_folding`, `word_ladder`.

**Files:**
- Modify: each of `src/denckring/procedures/<id>.py` above
- Test: `tests/test_apply_spine.py` (extend)

**Interfaces:**
- Consumes: `ConstructiveProcedure`, `ApplyParams`, `parse_into` from Task 3.
- Produces: no new names. Every one of the seventeen is an instance of `ConstructiveProcedure`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_apply_spine.py`:

```python
import inspect

from denckring.core.protocol import Constructive
from denckring.core.registry import all_procedures

DOES_NOT_DRAW = [
    "anagram", "boustrophedon", "column_reading", "diastic", "every_nth_word",
    "fold_in", "haikuization", "mathews_algorithm", "mesostic", "n_plus_7",
    "paragram", "pasigraphy", "s_plus_7", "slenderizing", "spoonerism",
    "text_folding", "word_ladder",
]


@pytest.mark.parametrize("procedure_id", DOES_NOT_DRAW)
def test_a_procedure_that_does_not_draw_refuses_a_seed(procedure_id: str) -> None:
    """It accepted one before and ignored it, which is the worse of the two."""
    with pytest.raises(InvalidParams):
        get(procedure_id).apply("one two three four five", seed=3)


@pytest.mark.parametrize("procedure_id", sorted(all_procedures()))
def test_every_generator_is_on_the_spine(procedure_id: str) -> None:
    procedure = all_procedures()[procedure_id]
    if not isinstance(procedure, Constructive):
        return
    assert isinstance(procedure, ConstructiveProcedure), (
        f"{procedure_id} defines apply() without inheriting the spine"
    )


@pytest.mark.parametrize("procedure_id", sorted(all_procedures()))
def test_no_generator_hand_rolls_the_preamble(procedure_id: str) -> None:
    """The spine does the pack, the capabilities and the parameters. A `_apply`
    that does any of it again has a second opinion the spine cannot see."""
    procedure = all_procedures()[procedure_id]
    if not isinstance(procedure, ConstructiveProcedure):
        return
    body = inspect.getsource(type(procedure)._apply)
    for forbidden in ("get_pack(", "parse_params(", "require_capability("):
        assert forbidden not in body, f"{procedure_id}._apply still calls {forbidden}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_apply_spine.py -v -k "seed or spine or preamble"`
Expected: FAIL — sixteen of the seventeen still accept `seed`, and `test_every_generator_is_on_the_spine` fails for every unmigrated row.

- [ ] **Step 3: Migrate each of the seventeen**

For each file, apply this transformation. Worked example, `every_nth_word.py` — before:

```python
@register
class EveryNthWord(BaseProcedure[EveryNthWordParams]):
    ...
    def apply(self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: Any) -> str:
        from denckring.lang import get_pack

        parsed = self.parse_params({"source": text, **params})
        pack = get_pack(lang)
        ...
```

after:

```python
@register
class EveryNthWord(ConstructiveProcedure[EveryNthWordParams, EveryNthWordParams]):
    ...
    def _apply(self, text: str, pack: LanguagePack, params: EveryNthWordParams) -> str:
        ...
```

The rules, applied uniformly:

1. Base class becomes `ConstructiveProcedure[<CheckParams>, <CheckParams>]`. Where the generator needs a parameter the checker does not, declare `class <Name>ApplyParams(<CheckParams>, ApplyParams)`, use it as the second argument, and override `apply_params_model`.

   Naming the check model twice is correct and not a copy-paste slip. The default `apply_params_model` builds `create_model(..., __base__=(cls.params_model(), ApplyParams))`, whose result is a *subclass* of the check model — so `_apply(self, ..., params: <CheckParams>)` receives an instance that satisfies the annotation, and gains `allow_identity` besides. `_guard_degenerate` reads that field through `getattr`, which is why no `_apply` needs to see it statically.
2. `def apply(self, text, *, lang=..., seed=None, **params)` becomes `def _apply(self, text: str, pack: LanguagePack, params: <ApplyModel>) -> str`.
3. Delete the local `from denckring.lang import get_pack` and the `pack = get_pack(lang)` line — `pack` is a parameter now.
4. Delete `parsed = self.parse_params({"source": text, **params})`; rename every later use of `parsed` to `params`.
5. Delete any `require_capability(...)` call — `anagram`, `paragram`, `spoonerism` and `word_ladder` have one. Move the capability it named onto that row's `apply_requires` in `catalogue.yaml` if it is not already in `requires`. For `anagram` this is `lexicon.words`, already done in Task 1.
6. Fix imports: add `ConstructiveProcedure` (and `ApplyParams` where used) from `denckring.core.base`, add `LanguagePack` from `denckring.core.protocol`, and drop `BaseProcedure`, `Lang` and `Any` where ruff reports them unused.

Do these one file at a time, running `uv run pytest -q -k <procedure_id>` after each.

- [ ] **Step 4: Run the full gate**

Run: `uv run pytest -q && uv run mypy src && uv run ruff check .`
Expected: PASS. `tests/test_round_trip.py` in particular must stay green — it is the harness that proves no generator's output changed.

- [ ] **Step 5: Commit**

```bash
git add src/denckring/procedures/ src/denckring/data/catalogue.yaml tests/test_apply_spine.py
git commit -m "refactor: the seventeen deterministic generators move onto the spine"
```

---

### Task 5: Migrate the ten that draw

Same transformation, plus `SeedParams`. These are the only ten that keep a `seed`.

**The ten:** `arca_musarithmica`, `cent_mille_milliards`, `denckring`, `ideenwuerfeln`, `llull_figure`, `melting_text`, `poesie_automat`, `recombination`, `wechselsatz` — and `cut_up`, already done in Task 3.

**Files:**
- Modify: each of `src/denckring/procedures/<id>.py` above
- Test: `tests/test_apply_spine.py` (extend)

**Interfaces:**
- Consumes: `ConstructiveProcedure`, `SeedParams`, `ApplyParams` from Task 3.
- Produces: a `<Name>ApplyParams` class in each of the nine modules.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_apply_spine.py`:

```python
DRAWS = [
    "arca_musarithmica", "cent_mille_milliards", "cut_up", "denckring",
    "ideenwuerfeln", "llull_figure", "melting_text", "poesie_automat",
    "recombination", "wechselsatz",
]


@pytest.mark.parametrize("procedure_id", DRAWS)
def test_a_procedure_that_draws_carries_seed_as_a_field(procedure_id: str) -> None:
    model = get(procedure_id).apply_params_model()
    assert "seed" in model.model_fields
    assert "seed" in model.model_json_schema()["properties"]


@pytest.mark.parametrize("procedure_id", DRAWS)
def test_a_drawn_seed_is_type_checked(procedure_id: str) -> None:
    with pytest.raises(InvalidParams):
        get(procedure_id).apply("one two three\nfour five six\n", seed="not-an-int")


def test_the_two_sets_partition_the_generators() -> None:
    """No generator may be in both lists or in neither."""
    assert set(DRAWS) & set(DOES_NOT_DRAW) == set()
    generators = {
        pid for pid, p in all_procedures().items() if isinstance(p, Constructive)
    }
    assert set(DRAWS) | set(DOES_NOT_DRAW) == generators
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_apply_spine.py -v -k "draws or partition"`
Expected: FAIL — nine of the ten have no `apply_params_model`, and `seed="not-an-int"` is still silently accepted by them.

- [ ] **Step 3: Migrate each of the nine**

Apply Task 4's six rules, plus:

7. Declare `class <Name>ApplyParams(<CheckParams>, SeedParams, ApplyParams)` in the module, override `apply_params_model` to return it, and use it as the second type argument.
8. Replace every use of the old `seed` argument with `params.seed`.

Worked example, `melting_text.py` — after:

```python
class MeltingTextApplyParams(MeltingTextParams, SeedParams, ApplyParams):
    """What the melt accepts. `seed` is a field here because as a signature
    keyword it bound before `**params` and pydantic never saw it."""


@register
class MeltingText(ConstructiveProcedure[MeltingTextParams, MeltingTextApplyParams]):
    ...
    @classmethod
    def apply_params_model(cls) -> type[MeltingTextApplyParams]:
        return MeltingTextApplyParams

    def _apply(self, text: str, pack: LanguagePack, params: MeltingTextApplyParams) -> str:
        chooser = random.Random(params.seed)
        ...
```

`denckring` and `poesie_automat` pass their seed to `devices.spin(machine, seed)` rather than `random.Random`; substitute `params.seed` at those call sites the same way. `denckring.py:92-93` nudges a fixed seed to keep it deterministic — leave that logic alone, only change where the value comes from.

- [ ] **Step 4: Run the full gate**

Run: `uv run pytest -q && uv run mypy src && uv run ruff check .`
Expected: PASS, including `test_apply_is_deterministic_under_a_fixed_seed`.

- [ ] **Step 5: Commit**

```bash
git add src/denckring/procedures/ tests/test_apply_spine.py
git commit -m "refactor: the ten drawing generators move onto the spine, and seed becomes a field"
```

---

### Task 6: Non-degeneracy

The eval harness asserts that `check(apply(text))` is satisfied for every constructive procedure. The identity passes that trivially, which is how `apply anagram "astronomer"` returning `"astronomer"` survived every gate this project runs. This gives the round-trip property its missing companion.

**Files:**
- Modify: `src/denckring/core/errors.py` (add `DegenerateOutput`)
- Modify: `src/denckring/core/base.py` (`_guard_degenerate`)
- Modify: `tests/test_round_trip.py` (the companion property)
- Test: `tests/test_non_degeneracy.py` (create)

**Interfaces:**
- Consumes: `ConstructiveProcedure._guard_degenerate` from Task 3, `ApplyParams.allow_identity` from Task 3.
- Produces: `denckring.core.errors.DegenerateOutput` with `code = "degenerate_output"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_non_degeneracy.py`:

```python
"""A generator that returns its input has not run the procedure.

The round-trip property — `check(apply(text))` is satisfied — is passed
trivially by the identity, which is how a generator returning its own input
survived every gate this project runs.
"""

import pytest

from denckring.core.errors import DegenerateOutput
from denckring.core.registry import get


def test_the_error_carries_what_a_caller_needs() -> None:
    error = DegenerateOutput("anagram")
    assert error.code == "degenerate_output"
    assert error.to_dict()["detail"]["procedure_id"] == "anagram"
    assert "allow_identity" in str(error)


def test_allow_identity_is_the_way_through() -> None:
    """`every_nth_word` with n=1 keeps every word, which is the honest identity
    and the reason the escape hatch exists."""
    produced = get("every_nth_word").apply("one two three", n=1, allow_identity=True)
    assert produced.split() == ["one", "two", "three"]


def test_without_the_flag_that_same_call_is_refused() -> None:
    with pytest.raises(DegenerateOutput):
        get("every_nth_word").apply("one two three", n=1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_non_degeneracy.py -v`
Expected: FAIL — `ImportError: cannot import name 'DegenerateOutput'`.

- [ ] **Step 3: Add the error**

In `src/denckring/core/errors.py`, following the shape of `NoCandidateWord`:

```python
class DegenerateOutput(DenckringError):
    """`apply` produced its own input.

    Raised rather than returned, for the reason `diastic` raises
    `NoCandidateWord` rather than returning "": handing back text that
    misrepresents what the procedure did is the failure, not a mild version of
    success. Usually it means the input could not feed the procedure.
    """

    code = "degenerate_output"

    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(
            f"{procedure_id!r} produced text identical to its input, so the procedure "
            f"did not run. Pass allow_identity=true if the degenerate case is wanted."
        )

    def detail(self) -> dict[str, Any]:
        return {"procedure_id": self.procedure_id}
```

- [ ] **Step 4: Give the guard teeth**

In `src/denckring/core/base.py`, replace the placeholder `_guard_degenerate`:

```python
    def _guard_degenerate(self, text: str, produced: str, params: A) -> str:
        """Refuse output identical to the input.

        Compared on stripped text, because trailing whitespace is not a
        transformation. `allow_identity` is on `ApplyParams`, so every generator
        carries the escape whether or not it declares its own model.
        """
        if getattr(params, "allow_identity", False):
            return produced
        if produced.strip() == text.strip():
            raise DegenerateOutput(self.id)
        return produced
```

Add `from denckring.core.errors import DegenerateOutput, InvalidParams, MissingCapability` to the imports.

- [ ] **Step 5: Add the companion property**

In `tests/test_round_trip.py`, add beside `test_apply_output_satisfies_check`:

```python
@settings(max_examples=50, deadline=None)
@given(TEXT)
def test_apply_does_not_return_its_input(text: str) -> None:
    """The companion the round-trip property never had.

    `check(apply(text))` is satisfied by the identity, so on its own it accepts a
    generator that does nothing. Here `DegenerateOutput` is *not* swallowed: the
    spine raising it is the guard working, and any other refusal is allowed for
    the same reason it is above.
    """
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            produced = procedure.apply(text, lang=lang, **_apply_args(procedure_id, 0))
        except DegenerateOutput:
            continue
        except DenckringError:
            continue
        assert produced.strip() != text.strip(), (
            f"{procedure_id}: apply returned its input past the guard: {produced!r}"
        )
```

Add `from denckring.core.errors import DegenerateOutput, DenckringError` to that module's imports.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_non_degeneracy.py tests/test_round_trip.py -v && uv run pytest -q && uv run mypy src && uv run ruff check .`
Expected: PASS, **except** that `test_the_named_coverage_gap_is_the_whole_coverage_gap` may now report `boustrophedon`, `cent_mille_milliards`, `recombination` or `wechselsatz` as unreached, because the guard turns their silent no-op into a raise. That is Task 7's work. If it fires here, note which rows and proceed to Task 7 rather than widening `PARAMETER_GATED`.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/core/errors.py src/denckring/core/base.py \
        tests/test_round_trip.py tests/test_non_degeneracy.py
git commit -m "feat: apply refuses to return its own input, which the round-trip property never could"
```

---

### Task 7: The four that no-op on input they cannot use

Measured against a single-sentence English input, four generators return their input: `boustrophedon`, `cent_mille_milliards`, `recombination`, `wechselsatz`. All four for one reason — the input was too small to feed the procedure. `boustrophedon` needs more than one line, `cent_mille_milliards` needs fourteen, `recombination` needs several sentences.

Fix the cause, not the symptom. `allow_identity=True` would silence the guard and keep the lie.

**Files:**
- Modify: `src/denckring/core/errors.py` (add `InputTooShort`)
- Modify: `src/denckring/procedures/boustrophedon.py`, `cent_mille_milliards.py`, `recombination.py`, `wechselsatz.py`
- Test: `tests/test_input_adequacy.py` (create)

**Interfaces:**
- Consumes: `DegenerateOutput` from Task 6.
- Produces: `denckring.core.errors.InputTooShort` with `code = "input_too_short"`, signature `InputTooShort(procedure_id: str, needed: str, found: str)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_input_adequacy.py`:

```python
"""Say what the input lacked, rather than handing it back unchanged.

Four generators returned their input when it could not feed them. That is
indistinguishable from a procedure that ran and changed nothing, which is why
the caller could not tell and neither could the eval.
"""

import pytest

from denckring.core.errors import InputTooShort
from denckring.core.registry import get

ONE_SENTENCE = "The quick brown fox jumps over the lazy dog and the cat sat still."


#: `boustrophedon` does not draw, so it takes no seed. The other three do.
DRAWN = {"cent_mille_milliards": {"seed": 0}, "recombination": {"seed": 0}, "wechselsatz": {"seed": 0}}


@pytest.mark.parametrize(
    "procedure_id",
    ["boustrophedon", "cent_mille_milliards", "recombination", "wechselsatz"],
)
def test_it_says_what_it_needed(procedure_id: str) -> None:
    with pytest.raises(InputTooShort) as caught:
        get(procedure_id).apply(ONE_SENTENCE, **DRAWN.get(procedure_id, {}))
    detail = caught.value.to_dict()["detail"]
    assert detail["procedure_id"] == procedure_id
    assert detail["needed"]
    assert detail["found"]


def test_the_error_reads_as_a_sentence() -> None:
    error = InputTooShort("boustrophedon", needed="more than one line", found="1 line")
    assert error.code == "input_too_short"
    assert "more than one line" in str(error)
    assert "1 line" in str(error)


def test_adequate_input_still_works() -> None:
    """The guard must not have made these procedures unusable."""
    produced = get("boustrophedon").apply("one two three\nfour five six\nseven eight\n")
    assert produced.strip() != "one two three\nfour five six\nseven eight"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_input_adequacy.py -v`
Expected: FAIL — `ImportError: cannot import name 'InputTooShort'`.

- [ ] **Step 3: Add the error**

In `src/denckring/core/errors.py`, beside the existing `InputTooLong`:

```python
class InputTooShort(DenckringError):
    """The input could not feed the procedure.

    The counterpart to `InputTooLong`, and the honest form of what four
    generators used to do instead: return the input unchanged, which reads
    exactly like a procedure that ran and had no effect.
    """

    code = "input_too_short"

    def __init__(self, procedure_id: str, needed: str, found: str) -> None:
        self.procedure_id = procedure_id
        self.needed = needed
        self.found = found
        super().__init__(
            f"{procedure_id!r} needs {needed}; found {found}."
        )

    def detail(self) -> dict[str, Any]:
        return {"procedure_id": self.procedure_id, "needed": self.needed, "found": self.found}
```

- [ ] **Step 4: Raise it from the four**

In each `_apply`, add a guard naming what the procedure needs, positioned after the local it inspects. The two "sheet of alternatives" machines — `cent_mille_milliards` and `wechselsatz` — do not fail on line count: they fail when no position offers a choice, which is why a plain prose sentence comes back unchanged from both.

`boustrophedon.py` — it turns alternate lines, and a single line has no alternate.
Its existing `lines` comes from `line_spans`, not `splitlines`; put the guard after it:

```python
        lines = [line for _, line in line_spans(text)]
        if len(lines) < 2:
            raise InputTooShort(
                self.id, needed="more than one line, so there is an alternate to turn",
                found=f"{len(lines)} line",
            )
```

`cent_mille_milliards.py` — `text` is the sheet of alternatives, not a poem, and
`alternatives()` returns one list per line split on `SEPARATOR` (`"|"`). A sheet where no
position offers a choice has nothing to draw, so the draw returns the sheet:

```python
        options = alternatives(text)
        if not any(len(position) > 1 for position in options):
            raise InputTooShort(
                self.id,
                needed=f"at least one position offering alternatives, separated by {SEPARATOR!r}",
                found=f"{len(options)} positions, none with a choice",
            )
```

`recombination.py` — it permutes sentences, so it needs more than one. Its existing local
is `parts`; put the guard directly after that list comprehension:

```python
        if len(parts) < 2:
            raise InputTooShort(
                self.id, needed="more than one sentence to recombine",
                found=f"{len(parts)} sentence",
            )
```

`wechselsatz.py` — the same shape as `cent_mille_milliards`: `slots` splits each
whitespace-separated token on `SEPARATOR`, and a frame where no slot offers a choice can
only give the frame back. Put the guard after `slots`:

```python
        if not any(len(options) > 1 for options in slots):
            raise InputTooShort(
                self.id,
                needed=f"at least one slot offering a choice, separated by {SEPARATOR!r}",
                found=f"{len(slots)} slots, none with a choice",
            )
```

Add `from denckring.core.errors import InputTooShort` to each module.

- [ ] **Step 5: Re-measure the round-trip coverage gap**

Run: `uv run pytest tests/test_round_trip.py -v`
Expected: PASS, with `test_the_named_coverage_gap_is_the_whole_coverage_gap` green — the four are reachable again on multi-line drawn text, which `TEXT`'s alphabet includes for exactly this reason.

If a row is still unreached, its guard is too strict for the text Hypothesis can draw. Loosen the guard to the procedure's true minimum; do not add the row to `PARAMETER_GATED`, which is reserved for rows needing a parameter this harness does not supply.

- [ ] **Step 6: Run the full gate**

Run: `uv run pytest -q && uv run mypy src && uv run ruff check .`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/core/errors.py src/denckring/procedures/ tests/test_input_adequacy.py
git commit -m "fix: four generators say what the input lacked instead of handing it back"
```

---

### Task 8: The ADR and the changelog

ADR 0002 said `apply` is optional and lives off the base class. It stays optional; it no longer lives off the base class. That is an amendment and the record should carry it, in the way ADR 0016 amends 0010 and ADR 0022 amends the German-pack decision.

**Files:**
- Create: `docs/adr/0025-the-apply-spine.md`
- Modify: `docs/adr/0002-check-mandatory-apply-optional.md` (an amendment pointer)
- Modify: `CHANGELOG.md` (the `[Unreleased]` section)

**Interfaces:**
- Consumes: everything above.
- Produces: no code.

- [ ] **Step 1: Write the ADR**

Create `docs/adr/0025-the-apply-spine.md`:

```markdown
# 25. `apply` gets the spine `check` has

## Context

ADR 0002 made `apply` optional and left it off `BaseProcedure`. `check` is a
template method that resolves the pack, enforces `meta.requires` and refuses
unknown parameters, so — in its own docstring — "an individual procedure module
cannot forget those checks". `apply` had none of that, and all 27 generators
hand-rolled the same preamble.

Each forgot something different. `cut_up` never validated parameters at all.
Four hand-rolled `require_capability`. `anagram` could not declare the lexicon
its generator uses, because `requires` gates `check` too. And `seed`, named
explicitly in the `Constructive` signature, bound before `**params` on every
call, so no params model ever saw it and all 27 accepted `seed="not-an-int"`.

The codebase had reached for this twice. `diastic` carries a twelve-line comment
documenting the `seed` collision and renames its field to dodge it; `cut_up`
carried `CutUpApplyParams`, a params model for the apply half that nothing used.

Separately, the eval harness asserted `check(apply(text))` is satisfied for every
constructive procedure — a property the identity passes trivially. A generator
returning its input satisfied every gate the project ran.

## Decision

`ConstructiveProcedure` carries a concrete `apply()` delegating to an abstract
`_apply()`, mirroring `check()`/`_check()`. It resolves the pack, enforces
`meta.requires` and `meta.apply_requires`, validates parameters, and refuses
output identical to its input.

`seed` becomes a field on `SeedParams`, carried only by the ten procedures that
draw. `allow_identity` is a field on `ApplyParams`, carried by all of them.

ADR 0002 is amended, not reversed: `apply` is still optional, and a procedure
without one is still registered on its checker alone. What changes is that a
procedure which *has* one inherits the spine rather than rebuilding it.

## Consequences

`seed` is typed, reaches `params_schema()`, and cannot be passed to a procedure
that does not draw — the exclusion-by-type ADR 0009 gives `fold_diacritics`,
applied again. This is a break: `apply(text, seed=5)` on a deterministic
procedure used to be accepted and ignored, and now raises.

`apply_requires` lets `anagram` declare `lexicon.words` without gating a checker
that has always run on core alone, which is what makes `missing` honest for the
generator half.

The non-degeneracy guard surfaced four generators that returned their input when
it could not feed them — `boustrophedon`, `cent_mille_milliards`,
`recombination`, `wechselsatz`. They now raise `InputTooShort` naming what they
needed. Finding them is the argument for the guard: each had been silently
no-opping, and the round-trip property called it a pass.

`kind` is untouched. It is a claim about the form, and nine rows are honestly
`both` with honestly no generator here; `describe` reports `constructive`
alongside it so both statements can be true at once.
```

- [ ] **Step 2: Point ADR 0002 at it**

Append to `docs/adr/0002-check-mandatory-apply-optional.md`:

```markdown
## Amendment

ADR 0025 keeps `apply` optional and moves it onto a `ConstructiveProcedure` base
class. The sentence above about `apply` living off `BaseProcedure` no longer
describes the code; the decision it was serving — that a procedure with only a
checker is a complete procedure — is unchanged.
```

- [ ] **Step 3: Record it in the changelog**

Add to `CHANGELOG.md` under `## [Unreleased]`, in `### Added`:

```markdown
- `ConstructiveProcedure`, the template method for `apply` that `check` has always
  had: it resolves the pack, enforces both capability lists, validates parameters
  and refuses output identical to the input, so a generator cannot forget any of
  it. ADR 0025.
- `Meta.apply_requires`, so a generator can declare a capability its checker does
  not need — `anagram` generates only with a word lexicon and checks with core
  alone, and one list could not say both.
- `Description.constructive` and `Summary.constructive`, reporting whether *this
  install* has a generator, distinct from `kind`, which says whether the form
  admits one. Nine rows are honestly `both` with no generator here.
- `DegenerateOutput` and `InputTooShort`.
```

and a `### Changed` entry:

```markdown
- **Breaking:** `seed` is a parameter on `SeedParams` rather than a keyword in the
  `Constructive.apply` signature, carried only by the ten procedures that draw at
  random. A keyword named in the signature bound before `**params`, so `seed` was
  never validated and all 27 generators accepted `seed="not-an-int"`. Passing
  `seed` to a procedure that does not draw now raises `InvalidParams` instead of
  being silently ignored.
- `boustrophedon`, `cent_mille_milliards`, `recombination` and `wechselsatz` raise
  `InputTooShort` where they used to return their input unchanged.
```

- [ ] **Step 4: Run the full gate**

Run: `uv run pytest -q && uv run mypy src && uv run ruff check . && uv run denckring eval --all && uv run denckring status`
Expected: PASS throughout; `status` reports the same counts as at the branch point, since this chapter implements no new procedure.

- [ ] **Step 5: Commit**

```bash
git add docs/adr/0025-the-apply-spine.md docs/adr/0002-check-mandatory-apply-optional.md CHANGELOG.md
git commit -m "docs: ADR 0025, the apply spine, amending 0002"
```

---

## Notes for the executor

**The round-trip harness is the safety net.** `tests/test_round_trip.py` is unusually well built: `test_the_named_coverage_gap_is_the_whole_coverage_gap` re-derives its own documented coverage gap from what `apply` actually produces, so a row that silently stops being reachable fails loudly with a message naming it. When it fires, read the message and fix the cause. Widening `PARAMETER_GATED` to make it pass would destroy exactly the property that makes this migration safe.

**What must not change.** No checker's verdict, and no generator's output except the four in Task 7. If a golden fixture moves, something is wrong with the migration, not with the fixture.

**Out of scope, and deliberately so.** The `anagram` generator still searches `pack.nouns()` instead of the word lexicon, which is why `apply anagram "astronomer"` returns `"astronomer"`. Task 6's guard will now refuse that output rather than return it — which is correct, and is not the fix. The fix is chapter 2. The same goes for `paragram` appending instead of substituting, `spoonerism` truncating past two words, `arca_musarithmica` leaking a Python list repr, `wechselsatz`'s missing template grammar, and `denckring`'s `combinations` metric ignoring `require_all_rings`.
