# The Production Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `apply` a structured counterpart so a generator with many valid answers can return all of them, while the string surface keeps returning exactly one.

**Architecture:** `_apply(...) -> str` becomes `_produce(...) -> list[str]`, ordered best first, as the single primitive on `ConstructiveProcedure`. A new public `produce()` wraps it in a `Production` — `Report`'s counterpart — and `apply()` becomes `produce(...).texts[0]`. The degeneracy guard stops being all-or-nothing and filters instead, so a multi-result generator drops its bad candidates rather than failing the whole call. `paragram`, which already scores every candidate and discards all but the best, is the pilot.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, hypothesis, mypy, ruff, uv.

**Spec:** `docs/superpowers/specs/2026-08-27-production-surface-design.md`

## Global Constraints

- **Python floor is 3.11.** PEP 696 TypeVar defaults are 3.13+ and must not be used.
- **`check()` behaviour must not change.** No checker's verdict may move.
- **No generator's `apply()` output may change.** The 26 single-result generators must return byte-identically what they return today. `paragram` (Task 5) must keep `texts[0]` equal to its current single result.
- **No field on any apply-params model may be named `lang`.** `ConstructiveProcedure.apply` and `produce` both take `lang` as an explicit signature keyword, and a keyword matching an explicit parameter binds there before reaching `**params` — silently. This is documented on `ApplyParams`.
- **Every new error class needs a unique, stable, snake_case `code`.** `tests/test_error_codes.py` pins the subclass count and asserts uniqueness.
- **`tests/conftest.py:61-64`** auto-parametrises any test argument named `procedure_id`. Writing `@pytest.mark.parametrize("procedure_id", ...)` raises "duplicate parametrization" — use `pid`.
- **Comments explain why, not what**, and cite ADRs by number. Match the surrounding register.
- **Gate before every commit:** `uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .`
- **The 27 generators** are: `anagram`, `arca_musarithmica`, `boustrophedon`, `cent_mille_milliards`, `column_reading`, `cut_up`, `denckring`, `diastic`, `every_nth_word`, `fold_in`, `haikuization`, `ideenwuerfeln`, `llull_figure`, `mathews_algorithm`, `melting_text`, `mesostic`, `n_plus_7`, `paragram`, `pasigraphy`, `poesie_automat`, `recombination`, `s_plus_7`, `slenderizing`, `spoonerism`, `text_folding`, `wechselsatz`, `word_ladder`.

---

### Task 1: `Production` and `NotConstructive`

Two data types, no behaviour. `Production` is what `produce` will return; `NotConstructive` replaces a hand-built dict literal in the MCP tool.

**Files:**
- Modify: `src/denckring/core/protocol.py` (add `Production` beside `Report`)
- Modify: `src/denckring/core/errors.py` (add `NotConstructive`)
- Modify: `tests/test_error_codes.py` (the subclass-count pin)
- Modify: `docs/superpowers/specs/2026-08-18-agentic-integration-design.md` (its error-code table)
- Test: `tests/test_production.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `denckring.core.protocol.Production` with fields `procedure: str`, `texts: list[str]`, `truncated: bool = False`, `metrics: dict[str, float]`; `denckring.core.errors.NotConstructive(procedure_id: str)` with `code = "not_constructive"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_production.py`:

```python
"""What a generator turned out. `Report`'s counterpart for the other half."""

import pytest

from denckring.core.errors import NotConstructive
from denckring.core.protocol import Production


def test_production_carries_what_a_caller_needs() -> None:
    produced = Production(procedure="paragram", texts=["a", "b"])
    assert produced.procedure == "paragram"
    assert produced.texts == ["a", "b"]
    assert produced.truncated is False
    assert produced.metrics == {}


def test_truncated_is_carried_when_set() -> None:
    assert Production(procedure="anagram", texts=["a"], truncated=True).truncated is True


def test_it_serialises_for_a_caller_who_never_touches_python() -> None:
    """The reason this is a pydantic model and not a tuple."""
    dumped = Production(procedure="cut_up", texts=["a"], metrics={"found": 3.0}).model_dump()
    assert dumped == {
        "procedure": "cut_up",
        "texts": ["a"],
        "truncated": False,
        "metrics": {"found": 3.0},
    }


def test_not_constructive_names_the_procedure() -> None:
    error = NotConstructive("lipogram")
    assert error.code == "not_constructive"
    assert error.to_dict()["detail"]["procedure_id"] == "lipogram"
    assert "lipogram" in str(error)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_production.py -v`
Expected: FAIL — `ImportError: cannot import name 'Production' from 'denckring.core.protocol'`.

- [ ] **Step 3: Add `Production`**

In `src/denckring/core/protocol.py`, directly after `class Report`:

```python
class Production(BaseModel):
    """What a generator turned out. `Report`'s counterpart for the other half.

    `check` has returned a structured verdict since the beginning while `apply`
    returned a bare string, so a generator that found several valid answers had
    one place to put one of them. `paragram` scores every candidate it finds and
    discards all but the best; `anagram` will have thirty-two two-word covers of
    `dormitory` behind it. This is where the rest go.
    """

    procedure: str
    #: Best first — `apply` returns `texts[0]`, so the order is the contract.
    #: Never empty: a generator with nothing to return raises, and an empty list
    #: would be a fourth way of saying a failure that has three honest names.
    texts: list[str]
    #: Whether more were found than `max_results` let through. Without it a
    #: truncated search is indistinguishable from an exhaustive one.
    truncated: bool = False
    metrics: dict[str, float] = Field(default_factory=dict)
```

- [ ] **Step 4: Add `NotConstructive`**

In `src/denckring/core/errors.py`, following the shape of the neighbouring classes:

```python
class NotConstructive(DenckringError):
    """Asked to generate with a procedure that only checks.

    The MCP tool built this dict by hand and returned it, which meant one
    failure mode in this package was not a `DenckringError` and could not be
    caught with the others. `kind` says whether the *form* admits a generator;
    `constructive` in `describe` says whether this install has one.
    """

    code = "not_constructive"

    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(
            f"{procedure_id!r} only checks; it has no generator in this install. "
            f"Read `constructive` in describe({procedure_id!r}) before generating."
        )

    def detail(self) -> dict[str, Any]:
        return {"procedure_id": self.procedure_id}
```

- [ ] **Step 5: Move the two inventories that count error classes**

`tests/test_error_codes.py` pins the number of `DenckringError` subclasses — currently eighteen. Find that test, read its docstring for what else it requires moving, and raise it to nineteen. Its docstring names the error-code table in `docs/superpowers/specs/2026-08-18-agentic-integration-design.md`; add `not_constructive` there in the same format the existing rows use.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_production.py tests/test_error_codes.py -v && uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .`
Expected: PASS throughout. Nothing behavioural changed.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/core/protocol.py src/denckring/core/errors.py \
        tests/test_production.py tests/test_error_codes.py \
        docs/superpowers/specs/2026-08-18-agentic-integration-design.md
git commit -m "feat: Production, and not-constructive becomes a real error"
```

---

### Task 2: `produce` on the spine, with `_apply` still in place

The spine gains `produce()`, `max_results`, and a filtering guard — while `_produce` keeps a default that wraps each generator's existing `_apply`. Nothing in `src/denckring/procedures/` changes yet, so all 27 keep working untouched and this task is green on its own.

**Files:**
- Modify: `src/denckring/core/base.py` (`ApplyParams`, `ConstructiveProcedure`)
- Modify: `src/denckring/core/protocol.py` (the `Constructive` protocol)
- Test: `tests/test_production.py` (extend)

**Interfaces:**
- Consumes: `Production` from Task 1.
- Produces:
  - `ApplyParams.max_results: int = 10` (`ge=1`)
  - `ConstructiveProcedure.produce(self, text: str, *, lang: Lang = "en", **params: Any) -> Production`
  - `ConstructiveProcedure._produce(self, text: str, pack: LanguagePack, params: A) -> list[str]` — defaulted here, made abstract in Task 3
  - `ConstructiveProcedure._guard_degenerate(self, text: str, produced: list[str], params: A) -> list[str]` — signature changes from `str` to `list[str]`
  - `Constructive` protocol gains `produce`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_production.py`:

```python
from denckring.core.errors import DegenerateOutput, InvalidParams
from denckring.core.registry import get


def test_produce_returns_a_production_for_a_single_result_generator() -> None:
    produced = get("every_nth_word").produce("one two three four", n=2)
    assert produced.procedure == "every_nth_word"
    assert produced.texts == ["two four"]
    assert produced.truncated is False


def test_apply_is_the_first_text() -> None:
    """The string surface is defined in terms of the structured one, not beside it."""
    procedure = get("every_nth_word")
    assert procedure.apply("one two three four", n=2) == procedure.produce(
        "one two three four", n=2
    ).texts[0]


def test_max_results_is_a_parameter_of_every_generator() -> None:
    assert get("cut_up").apply_params_model().model_fields["max_results"].default == 10


def test_max_results_below_one_is_refused() -> None:
    """Zero results is not a smaller answer, it is no answer — and `texts[0]`
    would raise IndexError rather than say so."""
    with pytest.raises(InvalidParams):
        get("every_nth_word").produce("one two three four", n=2, max_results=0)


def test_the_guard_still_refuses_when_nothing_survives() -> None:
    """A single-result generator whose one candidate is degenerate must behave
    exactly as it did before the guard learned to filter."""
    with pytest.raises(DegenerateOutput):
        get("every_nth_word").produce("one two three", n=1)


def test_metrics_report_what_was_found() -> None:
    assert get("every_nth_word").produce("one two three four", n=2).metrics["found"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_production.py -v -k "produce or max_results or guard or metrics"`
Expected: FAIL — `AttributeError: 'EveryNthWord' object has no attribute 'produce'`.

- [ ] **Step 3: Add `max_results` to `ApplyParams`**

In `src/denckring/core/base.py`, in `class ApplyParams`, after the `allow_identity` field:

```python
    max_results: int = Field(
        default=10,
        ge=1,
        description="How many results to return at most. `apply` returns the first.",
    )
```

Extend that class's docstring with a sentence saying why ten:

```
    `max_results` defaults to ten rather than one because a caller asking a
    procedure that has many valid answers expects more than one of them, and
    rather than unbounded because `dormitory` alone has thirty-two exact
    two-word covers before any deeper search. `Production.truncated` is what
    keeps a capped search from reading as an exhaustive one.
```

- [ ] **Step 4: Add `produce`, `_produce` and the filtering guard**

In `src/denckring/core/base.py`, in `class ConstructiveProcedure`:

```python
    def _produce(self, text: str, pack: LanguagePack, params: A) -> list[str]:
        """Procedure-specific generation, best first.

        Defaulted here only while the generators migrate; Task 3 makes it
        abstract and removes `_apply`. A list even where there is one answer:
        `apply` returns `texts[0]`, so the order is the contract, and a
        generator that ranks its candidates puts its winner at the front.
        """
        return [self._apply(text, pack, params)]

    def produce(self, text: str, *, lang: Lang = "en", **params: Any) -> Production:
        """Generate with this procedure, returning every result it found.

        Carries the preamble `apply` used to: `apply` is now defined in terms of
        this, so there is one path through the pack, the capabilities, the
        parameters and the guard rather than two that can drift.
        """
        from denckring.lang import get_pack

        pack = get_pack(lang)
        for capability in (*self.meta.requires, *self.meta.apply_requires):
            require_capability(pack, capability, self.id)
        parsed = self.parse_apply_params(text, params)
        found = self._guard_degenerate(text, self._produce(text, pack, parsed), parsed)
        # `getattr`, falling back to one rather than ten, for the reason
        # `_guard_degenerate` reads `allow_identity` the same way: a generator
        # may declare an apply-params model that does not inherit `ApplyParams`,
        # and the safe reading of a missing limit is the old single-result
        # behaviour rather than a larger one it never asked for.
        limit = getattr(parsed, "max_results", 1)
        return Production(
            procedure=self.id,
            texts=found[:limit],
            truncated=len(found) > limit,
            metrics={"found": float(len(found))},
        )

    def apply(self, text: str, *, lang: Lang = "en", **params: Any) -> str:
        """Generate one text with this procedure — the best one it found.

        One and not several: `check` reads what `apply` returned as a single
        text, so three anagrams joined by newlines are a text with three times
        the letters, which its own checker scores 0.333. The round-trip property
        that has guarded every generator here through two migrations depends on
        this staying one text. `produce` is where the rest go.
        """
        return self.produce(text, lang=lang, **params).texts[0]
```

Change `_guard_degenerate` to take and return a list. Keep its existing docstring and extend it; keep the `ignores_input` and `allow_identity` behaviour exactly:

```python
    def _guard_degenerate(self, text: str, produced: list[str], params: A) -> list[str]:
        if getattr(params, "allow_identity", False):
            return produced
        kept = [candidate for candidate in produced if not self._is_degenerate(text, candidate)]
        if not kept:
            raise DegenerateOutput(self.id)
        return kept

    def _is_degenerate(self, text: str, produced: str) -> bool:
        """One candidate's worth of the judgement the guard used to make wholesale.

        Filtering rather than refusing is what a multi-result generator needs: an
        anagram search that finds its own source among the covers should drop
        that one and return the others, not fail the call. For a generator with
        one candidate the two are the same thing — nothing survives, so the
        guard raises exactly as before.
        """
        if not produced.strip() and text.strip():
            return True
        return not self.ignores_input and produced.strip() == text.strip()
```

Move the body of the old `_guard_degenerate` docstring's reasoning onto `_is_degenerate` where it now belongs, and add `Production` to the `protocol` import at the top of the module.

- [ ] **Step 5: Add `produce` to the `Constructive` protocol**

In `src/denckring/core/protocol.py`, in `class Constructive`, beside `apply`:

```python
    def produce(self, text: str, *, lang: Lang = "en", **params: Any) -> Production: ...
```

`Constructive` is `runtime_checkable`, and `isinstance` against it checks method presence only. Every `ConstructiveProcedure` has both methods, so the set it matches is unchanged — confirm that with `tests/test_constructive_truth.py`, which pins `describe(...).constructive` against this protocol for all 119 rows.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_production.py -v && uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .`
Expected: PASS. `tests/test_round_trip.py` must stay green — nothing any generator returns has changed.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/core/base.py src/denckring/core/protocol.py tests/test_production.py
git commit -m "feat: produce, where the results apply cannot carry go"
```

---

### Task 3: Migrate the 27 to `_produce`

Mechanical. Twenty-six are a one-line change; `paragram` moves in Task 5 and here does the same one-line wrap as the rest.

**Files:**
- Modify: each of the 27 `src/denckring/procedures/<id>.py`
- Modify: `src/denckring/core/base.py` (make `_produce` abstract, delete `_apply` and the default)
- Test: `tests/test_apply_spine.py` (extend)

**Interfaces:**
- Consumes: `_produce` from Task 2.
- Produces: no new names. `ConstructiveProcedure._apply` no longer exists; `_produce` is abstract.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_apply_spine.py`:

```python
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
def test_produce_is_annotated_as_returning_a_list(pid: str) -> None:
    """Catches a generator migrated in body but not in signature — the annotation
    is what `mypy --strict` reads, and a stale `-> str` there passes at runtime."""
    procedure = get(pid)
    assert isinstance(procedure, ConstructiveProcedure)
    import inspect

    signature = inspect.signature(type(procedure)._produce)
    assert signature.return_annotation in ("list[str]", list[str])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_apply_spine.py -v -k "produce or primitive"`
Expected: FAIL — every generator still defines `_apply`.

- [ ] **Step 3: Migrate each generator**

For each of the 27, apply this transformation. Worked example, `every_nth_word.py` — before:

```python
    def _apply(self, text: str, pack: LanguagePack, params: EveryNthWordApplyParams) -> str:
        spans = word_spans(text, pack)
        return " ".join(word for index, (_, word) in enumerate(spans, 1) if index % params.n == 0)
```

after:

```python
    def _produce(
        self, text: str, pack: LanguagePack, params: EveryNthWordApplyParams
    ) -> list[str]:
        spans = word_spans(text, pack)
        return [
            " ".join(word for index, (_, word) in enumerate(spans, 1) if index % params.n == 0)
        ]
```

The rules:

1. Rename `_apply` → `_produce`.
2. Change the return annotation from `-> str` to `-> list[str]`.
3. Wrap each `return <expr>` in a list: `return [<expr>]`. A method with several return statements gets each one wrapped.
4. Leave every `raise` untouched — a generator that refuses still refuses, and `texts` is never empty precisely because those raises stay.
5. Leave docstrings' reasoning intact; where one says "returns" of a single text, adjust the wording only if it becomes false.

Do these one file at a time, running `uv run pytest -q -k <procedure_id>` after each.

- [ ] **Step 4: Make `_produce` abstract and delete `_apply`**

In `src/denckring/core/base.py`, replace the defaulted `_produce` with:

```python
    @abstractmethod
    def _produce(self, text: str, pack: LanguagePack, params: A) -> list[str]:
        """Procedure-specific generation, best first. Language and parameters are already valid.

        A list even where there is one answer: `apply` returns `texts[0]`, so the
        order is the contract, and a generator that ranks its candidates puts its
        winner at the front. One primitive rather than a `str` one beside a
        `list` one, because two would make every consumer ask which a given
        procedure implements.
        """
```

and delete the abstract `_apply` declaration entirely.

- [ ] **Step 5: Run the full gate**

Run: `uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .`
Expected: PASS. `tests/test_round_trip.py` is the proof no generator's output moved; if `test_the_named_coverage_gap_is_the_whole_coverage_gap` fails it is naming a row that became unreachable — fix the cause, and never widen `PARAMETER_GATED`.

- [ ] **Step 6: Commit**

```bash
git add src/denckring/procedures/ src/denckring/core/base.py tests/test_apply_spine.py
git commit -m "refactor: list is the primitive, so the many have somewhere to be"
```

---

### Task 4: The three surfaces

Python, CLI and MCP each reach `produce`. The Python one also closes an older gap: the package has exported `check` since the beginning and has never exported `apply`, so every Python caller has had to reach through `registry.get(...)`.

**Files:**
- Modify: `src/denckring/__init__.py`
- Modify: `src/denckring/cli.py` (`apply_command`)
- Modify: `src/denckring/mcp/server.py` (`apply_procedure_tool`)
- Test: `tests/test_production.py`, `tests/test_cli.py`, `tests/test_mcp_tools.py` (extend)

**Interfaces:**
- Consumes: `produce` from Task 2, `NotConstructive` from Task 1.
- Produces: `denckring.apply(procedure_id, text, *, lang="en", **params) -> str`; `denckring.produce(procedure_id, text, *, lang="en", **params) -> Production`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_production.py`:

```python
import denckring
from denckring.core.errors import UnknownProcedure


def test_the_package_exports_both_surfaces() -> None:
    """`check` has been exported since the beginning and `apply` never was, so
    every Python caller reached through the registry to generate anything."""
    assert denckring.apply("every_nth_word", "one two three four", n=2) == "two four"
    produced = denckring.produce("every_nth_word", "one two three four", n=2)
    assert produced.texts == ["two four"]
    assert "apply" in denckring.__all__
    assert "produce" in denckring.__all__


def test_generating_with_a_checker_only_procedure_is_an_error_not_a_dict() -> None:
    with pytest.raises(NotConstructive):
        denckring.apply("lipogram", "a text")
    with pytest.raises(NotConstructive):
        denckring.produce("lipogram", "a text")


def test_an_unknown_id_still_raises_unknown_procedure() -> None:
    with pytest.raises(UnknownProcedure):
        denckring.produce("no_such_procedure", "a text")
```

Append to `tests/test_cli.py`. **Read that file first and copy how its existing tests
feed input to `apply`** — `apply`'s file argument is `str | None` with `-` documented for
stdin, and the working invocation is already in that file. The two tests below show what to
assert, not how to invoke; take the invocation from the existing tests:

```python
def test_apply_json_emits_a_production() -> None:
    import json

    result = runner.invoke(app, ["apply", "every_nth_word", "-p", "n=2", "--json"], input="one two three four")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["procedure"] == "every_nth_word"
    assert payload["texts"] == ["two four"]
    assert payload["truncated"] is False


def test_apply_without_json_still_prints_one_text() -> None:
    result = runner.invoke(app, ["apply", "every_nth_word", "-p", "n=2"], input="one two three four")
    assert result.exit_code == 0
    assert result.stdout.strip() == "two four"
```

Append to `tests/test_mcp_tools.py`:

```python
def test_apply_procedure_carries_the_other_results() -> None:
    from denckring.mcp.server import apply_procedure_tool

    out = apply_procedure_tool("every_nth_word", "one two three four", {"n": 2})
    assert out["text"] == "two four"
    assert out["texts"] == ["two four"]
    assert out["truncated"] is False


def test_apply_procedure_text_is_still_the_first_text() -> None:
    """Additive: `text` keeps its meaning, so no existing caller breaks."""
    from denckring.mcp.server import apply_procedure_tool

    out = apply_procedure_tool("cut_up", "one two three four", {"seed": 1})
    assert out["text"] == out["texts"][0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_production.py tests/test_cli.py tests/test_mcp_tools.py -v -k "export or constructive or json or carries"`
Expected: FAIL — `AttributeError: module 'denckring' has no attribute 'apply'`.

- [ ] **Step 3: Export both from the package**

In `src/denckring/__init__.py`, beside `check`:

```python
def apply(procedure_id: str, text: str, *, lang: Lang = "en", **params: Any) -> str:
    """Generate one text with a procedure by id — the best result it found."""
    return _constructive(procedure_id).apply(text, lang=lang, **params)


def produce(procedure_id: str, text: str, *, lang: Lang = "en", **params: Any) -> Production:
    """Generate with a procedure by id, returning every result it found."""
    return _constructive(procedure_id).produce(text, lang=lang, **params)


def _constructive(procedure_id: str) -> Constructive:
    """The procedure, or `NotConstructive` if it only checks.

    Raised rather than returned as a value, so a caller catches one kind of
    failure for one kind of mistake — `UnknownProcedure` and this are both
    `DenckringError`.
    """
    procedure = get(procedure_id)
    if not isinstance(procedure, Constructive):
        raise NotConstructive(procedure_id)
    return procedure
```

Add `apply`, `produce` and `Production` to `__all__`, and the imports they need.

- [ ] **Step 4: Add `--json` to the CLI**

In `src/denckring/cli.py`, in `apply_command`, add the option and branch. Keep the existing `drawn` seed handling exactly as it is:

```python
    as_json: Annotated[bool, typer.Option("--json")] = False,
```

```python
    try:
        produced = procedure.produce(
            _read(file), lang=_lang(lang), **drawn, **_parse_params(param or [])
        )
    except DenckringError as exc:
        _fail(exc)
        return
    typer.echo(produced.model_dump_json(indent=2) if as_json else produced.texts[0])
```

Replace the `isinstance(procedure, Constructive)` branch's hand-written message with `_fail(NotConstructive(procedure_id))`, so the CLI and the library report it identically.

- [ ] **Step 5: Widen the MCP tool**

In `src/denckring/mcp/server.py`, replace `apply_procedure_tool`'s body:

```python
    try:
        produced = produce(procedure, text, lang=lang, **(params or {}))
    except DenckringError as exc:
        return exc.to_dict()
    return {
        "text": produced.texts[0],
        "texts": produced.texts,
        "truncated": produced.truncated,
    }
```

The `getattr`-and-branch that built a `not_constructive` dict by hand goes away: `produce` raises `NotConstructive`, which is a `DenckringError`, so the existing `except` converts it to the same payload it built before. Extend the docstring to say that `text` is the first of `texts` and that `truncated` says whether more were found than `max_results` allowed.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/denckring/__init__.py src/denckring/cli.py src/denckring/mcp/server.py \
        tests/test_production.py tests/test_cli.py tests/test_mcp_tools.py
git commit -m "feat: produce reaches Python, the command line and the model"
```

---

### Task 5: `paragram`, the pilot

Its `_produce` currently tracks `best_score`/`best_offset`/`best_word`/`best_swapped` through three nested loops and returns one insertion. Everything needed to return several is already computed and already totally ordered — the change is to stop discarding.

**Files:**
- Modify: `src/denckring/procedures/paragram.py`
- Test: `tests/test_paragram.py` (extend)

**Interfaces:**
- Consumes: `_produce` from Task 3.
- Produces: no new names.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_paragram.py`:

```python
def test_it_returns_more_than_one_candidate() -> None:
    """The search already found these and the old return type discarded them."""
    produced = get("paragram").produce("The cat is great.")
    assert len(produced.texts) > 1
    assert len(set(produced.texts)) == len(produced.texts), "candidates must be distinct"


def test_the_best_is_still_first() -> None:
    """`apply`'s result must not move: it is the same winner, now with the
    runners-up behind it rather than thrown away."""
    procedure = get("paragram")
    assert procedure.produce("The cat is great.").texts[0] == "The cat is great treat."


def test_the_order_is_the_score_it_already_computed() -> None:
    """`CandidateScore` is `(pronounced, is_noun, length)` and totally ordered.
    Sorting must be stable, so equal scores keep the search's own order and two
    runs of the same input agree."""
    procedure = get("paragram")
    first = procedure.produce("The cat is great.").texts
    assert first == procedure.produce("The cat is great.").texts


def test_max_results_caps_and_says_so() -> None:
    produced = get("paragram").produce("The cat is great.", max_results=2)
    assert len(produced.texts) == 2
    assert produced.truncated is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_paragram.py -v -k "candidate or first or order or caps"`
Expected: FAIL — `assert len(produced.texts) > 1` fails, because `_produce` returns a one-element list.

- [ ] **Step 3: Collect every candidate rather than the best one**

In `src/denckring/procedures/paragram.py`, replace the `best_*` tracking with collection. Keep the `pronounced`/`is_noun`/`score` computation and the `NoCandidateWord` raise exactly as they are:

```python
        found: list[tuple[CandidateScore, int, str, str]] = []
        for offset, word in word_spans(text, pack):
            if not word.isalpha():
                continue
            lowered = word.lower()
            for position in range(len(word)):
                for letter in string.ascii_lowercase:
                    if letter == lowered[position]:
                        continue
                    swapped = lowered[:position] + letter + lowered[position + 1 :]
                    if not pack.is_word(swapped):
                        continue
                    # `syllable_count`'s second element is True only when the
                    # pronouncing dictionary itself listed the word, not when a
                    # spelling heuristic guessed at one — the same distinction
                    # every syllabic procedure's `estimated_words` metric rests on.
                    pronounced = has_syllables and pack.syllable_count(swapped)[1]
                    is_noun = has_nouns and pack.noun_index(swapped) is not None
                    score: CandidateScore = (pronounced, is_noun, len(swapped))
                    found.append((score, offset, word, swapped))
        if not found:
            raise NoCandidateWord(self.id)
        # Stable, so candidates that score equally keep the order the search
        # walked them in and two runs of the same input agree. `CandidateScore`
        # is a plain tuple and totally ordered, so this needs no key beyond it.
        found.sort(key=lambda candidate: candidate[0], reverse=True)
        return [
            text[: offset + len(word)] + " " + swapped + text[offset + len(word) :]
            for _, offset, word, swapped in found
        ]
```

Update the method's docstring: the paragraph explaining that "the best-scoring one wins — not the first one found" should now say that every candidate is returned in that order, and that `apply` takes the winner. The reasoning about why a first-match search surfaced noise is still true and worth keeping.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_paragram.py -v && uv run pytest -q`
Expected: PASS. `tests/test_round_trip.py` must stay green — if it fails, a candidate beyond the first produces text its own checker rejects, which is a real finding about `paragram` and not a test to weaken.

- [ ] **Step 5: Run the full gate**

Run: `uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/denckring/procedures/paragram.py tests/test_paragram.py
git commit -m "feat: paragram returns the candidates it was already scoring"
```

---

### Task 6: Strengthen the eval

Today `check` is asserted against `apply`'s single result. With a generator that returns several, that leaves everything after the first unchecked — which is exactly where a multi-result search would hide a bad candidate.

**Files:**
- Modify: `tests/test_round_trip.py`
- Test: same file

**Interfaces:**
- Consumes: `produce` from Task 2, `paragram`'s several results from Task 5.
- Produces: no new names.

- [ ] **Step 1: Write the failing test**

In `tests/test_round_trip.py`, add beside `test_apply_output_satisfies_check`:

```python
@settings(max_examples=50, deadline=None)
@given(TEXT)
def test_every_produced_text_satisfies_check(text: str) -> None:
    """Strictly stronger than the property above, which sees only `texts[0]`.

    A multi-result generator hides its bad candidates behind the first one, and
    the first one is the only one `apply` ever returned. This is the property
    that keeps a search honest once there is a search.
    """
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            produced = procedure.produce(text, lang=lang, **_apply_args(procedure_id, 0))
        except DenckringError:
            continue
        for candidate in produced.texts:
            report = procedure.check(candidate, lang=lang, **_check_args(procedure_id, text))
            assert report.satisfied, (
                f"{procedure_id}: produced text its own check rejects: {candidate!r}"
            )


@settings(max_examples=50, deadline=None)
@given(TEXT)
def test_every_produced_text_differs_from_the_input(text: str) -> None:
    """The non-degeneracy companion, over all candidates rather than the first."""
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            produced = procedure.produce(text, lang=lang, **_apply_args(procedure_id, 0))
        except DenckringError:
            continue
        for candidate in produced.texts:
            assert candidate.strip() != text.strip(), (
                f"{procedure_id}: produced its input past the guard: {candidate!r}"
            )
```

- [ ] **Step 2: Run test to verify it fails or reveals something**

Run: `uv run pytest tests/test_round_trip.py -v`
Expected: PASS if every `paragram` candidate round-trips. **If it fails, that is a real finding about `paragram`, not a test to weaken** — read which candidate its own checker rejects and fix the generator. Report the finding either way.

- [ ] **Step 3: Update the module docstring**

That file's docstring explains what the properties cover and has twice been wrong about it in ways the tests then caught. Add a paragraph saying that the two new properties range over `produce`'s whole list where the older two see only `apply`'s first result, and that `paragram` is currently the only row where those differ.

- [ ] **Step 4: Run the full gate**

Run: `uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_round_trip.py
git commit -m "test: the round trip covers every candidate, not only the first"
```

---

### Task 7: ADR 0026 and the changelog

**Files:**
- Create: `docs/adr/0026-the-production-surface.md`
- Modify: `docs/adr/0025-the-apply-spine.md` (an amendment pointer)
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: everything above.
- Produces: no code.

- [ ] **Step 1: Read the branch before writing**

Run `git log --oneline <base>..HEAD` and `git diff --stat <base>..HEAD`, and read `src/denckring/core/base.py` and `src/denckring/core/protocol.py` as they now stand. The ADR's job is to be true about what landed, not to restate this plan. Where the two differ, the code wins and the ADR records the code.

Confirm 0026 is the next free ADR number. Read `docs/adr/0015-lexicon-capabilities.md` first — it is the house model for admitting a cost as fact rather than softening it.

- [ ] **Step 2: Write the ADR**

Create `docs/adr/0026-the-production-surface.md` with the house structure — Context stating a real problem, Decision, Consequences that admit costs. It must cover:

- The measurement that forced the shape: `check anagram text:"silent\ntinsel\nenlist" source:"listen"` scores 0.333 with `surplus_letter` violations, so the string surface cannot carry several results without making the project's central property conditional on procedure kind.
- That `_produce -> list[str]` is the single primitive, and why not two.
- That `apply` is now defined as `produce(...).texts[0]` rather than a second path.
- That the guard filters rather than refusing wholesale, and what that changes for a single-result generator (nothing).
- `max_results` defaulting to ten, and `truncated` as what keeps a capped search from reading as exhaustive.
- The cost to admit: `apply` builds a whole `Production` to return one string, and `paragram` now scores and renders every candidate on every call where it previously kept one. Both are small; state them rather than leaving them for a reader to find.
- That `NotConstructive` makes a failure mode a `DenckringError` that previously was a hand-built dict.

- [ ] **Step 3: Amend ADR 0025**

Append to `docs/adr/0025-the-apply-spine.md`:

```markdown
## Amendment

ADR 0026 replaces `_apply(...) -> str` with `_produce(...) -> list[str]` as the
primitive, and defines `apply` as `produce(...).texts[0]`. The spine this ADR
describes is unchanged in what it enforces — pack, both capability lists,
parameters, and a guard against output that misrepresents what ran. Only the
shape of what `_apply` returned has moved.
```

- [ ] **Step 4: Update the changelog**

Under `## [Unreleased]`, in `### Added`:

```markdown
- `Production`, `Report`'s counterpart for the generating half: `procedure`, `texts`
  (best first, never empty), `truncated`, `metrics`. ADR 0026.
- `produce()` on every generator, and `denckring.produce()` at the package level,
  returning every result a generator found rather than only the first.
- `denckring.apply()` at the package level. `check` has been exported since the
  beginning and `apply` never was, so every Python caller reached through the
  registry to generate anything.
- `denckring apply --json`, emitting the `Production`, matching `describe --json`.
- `max_results` on `ApplyParams`, defaulting to 10.
- `NotConstructive`, replacing a dict literal the MCP server built by hand — one
  failure mode in this package was not a `DenckringError` and could not be caught
  with the others.
```

and in `### Changed`:

```markdown
- `apply_procedure` (MCP) returns `texts` and `truncated` alongside `text`. Additive:
  `text` keeps its meaning and value as the first of `texts`.
- `paragram` returns every candidate it scores, best first, where it scored them all
  and returned one. `apply`'s result is unchanged.
```

- [ ] **Step 5: Run the full gate**

Run: `uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check . && uv run denckring eval --all && uv run denckring status`
Expected: PASS; `status` unchanged at 154 catalogued · 128 implementable · 119 implemented · 119 validated, since this chapter implements no new procedure.

- [ ] **Step 6: Commit**

```bash
git add docs/adr/0026-the-production-surface.md docs/adr/0025-the-apply-spine.md CHANGELOG.md
git commit -m "docs: ADR 0026, the production surface, amending 0025"
```

---

## Notes for the executor

**What must not change.** No checker's verdict, and no generator's `apply()` output — `paragram` included, whose `texts[0]` must equal what it returned before Task 5. `tests/test_round_trip.py` is the net that proves it.

**`PARAMETER_GATED` is not a knob.** If `test_the_named_coverage_gap_is_the_whole_coverage_gap` fails it is naming a row that became unreachable, which is a real finding. That file has twice lost coverage silently and has a test built specifically to catch it happening again.

**Out of scope, deliberately.** The anagram multi-cover search is chapter 3: at the end of this chapter `apply anagram "astronomer"` still raises `DegenerateOutput`, because its generator still searches `pack.nouns()` and finds only the identity there. The surface will be ready; the search rests on a lexicon decision recorded in `docs/expansion_ideas/anagram-generation-research.md`. Also out: per-candidate scores or provenance in `Production.texts`, a generator-side truncation signal for searches with an internal budget, and `lang` remaining a reserved signature keyword.
