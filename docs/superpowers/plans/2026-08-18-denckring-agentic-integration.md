# Agentic Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Give the package a machine-readable surface — `describe`, `summaries`, structured errors — and expose it as an MCP server and a Claude Code skill, so a model can write under a constraint, check its own output, and revise.

**Architecture:** The reusable work lands in core, where four callers need it: the CLI's `show`, `apps/explorer`, the MCP server and the skill. The two transports are thin — the server maps four tools onto core functions and converts `DenckringError` into data; the skill shells out to the CLI, which calls the same core functions. Neither transport computes anything, so they cannot disagree about what a procedure is.

**Tech Stack:** Python 3.11+, Pydantic v2, MCP Python SDK v2 (`mcp[cli]`), typer, pytest, hypothesis, ruff, mypy --strict, uv.

**Spec:** `docs/superpowers/specs/2026-08-18-agentic-integration-design.md`

## Global Constraints

- Python 3.11+; `mypy --strict`, `ruff check src tests`, `ruff format --check src tests` all clean.
- **Do not change `list_procedures()`.** It is public, exported in `__all__`, and returns `list[str]`. `summaries()` is added alongside it.
- **MCP SDK facts, verified against `modelcontextprotocol/python-sdk` on 2026-08-18:** the current stable line is **v2**; the server class is **`MCPServer`**, imported `from mcp.server import MCPServer`; the install is `mcp[cli]`. The 2026-07-28 specification revision renamed `FastMCP` to `MCPServer` — any example naming `FastMCP` describes the v1 line and must not be copied.
- `Meta.prompt_hints` is `dict[Lang, str]`, `Meta.names` is `dict[Lang, str]`, `Meta.definitions` is `dict[Lang, str]`. All three are keyed by language.
- `Lang` is `Literal["en", "de", "fr"]` from `denckring.core.protocol`.
- Errors are never raised out of an MCP tool. Every tool catches `DenckringError` and returns `to_dict()`.
- Baseline is **2193 tests passing** at branch point `bbe3ae8`.
- The `mcp` import must be guarded so the suite skips cleanly when the extra is absent, matching how the data-pack tests behave.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/denckring/core/describe.py` (create) | `Summary`, `Description`, `Scholarly` models; `describe()`, `summaries()`, `runnable()`. |
| `src/denckring/core/errors.py` (modify) | `code` on every subclass; `to_dict()` on the base; suggestions on `UnknownProcedure`. |
| `src/denckring/__init__.py` (modify) | Export `describe`, `summaries`, and the three models. |
| `src/denckring/mcp/__init__.py`, `server.py` (create) | The four tools and `main()`. Imports `mcp`, so it lives behind the extra. |
| `src/denckring/cli.py` (modify) | `describe --json` and `list --json` for skill parity. |
| `skills/denckring/SKILL.md` (create) | The Claude Code skill. |
| `pyproject.toml` (modify) | The `mcp` extra and the `denckring-mcp` script. |
| `tests/test_describe.py`, `test_error_codes.py`, `test_mcp_tools.py` (create) | One per component. |

---

### Task 1: Structured errors

**Files:**
- Modify: `src/denckring/core/errors.py`
- Test: `tests/test_error_codes.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `DenckringError.code: str`, `DenckringError.to_dict() -> dict[str, Any]`, and `UnknownProcedure.suggestions: list[str]`.

- [x] **Step 1: Write the failing test**

Create `tests/test_error_codes.py`:

```python
"""Every failure the agentic surface can return must be labelled.

A model cannot act on a traceback. It can act on
`{"code": "invalid_params", "detail": {...}}`.
"""

import inspect

import pytest

from denckring.core import errors
from denckring.core.errors import (
    DenckringError,
    InvalidParams,
    MissingCapability,
    UnknownProcedure,
)


def subclasses() -> list[type[DenckringError]]:
    return [
        value
        for _, value in inspect.getmembers(errors, inspect.isclass)
        if issubclass(value, DenckringError) and value is not DenckringError
    ]


def test_every_subclass_has_a_code() -> None:
    """A subclass added later without a code would reach a model unlabelled."""
    missing = [cls.__name__ for cls in subclasses() if not getattr(cls, "code", "")]
    assert not missing, f"no code on: {missing}"


def test_codes_are_unique() -> None:
    codes = [cls.code for cls in subclasses()]
    duplicates = {code for code in codes if codes.count(code) > 1}
    assert not duplicates, f"duplicate codes: {duplicates}"


def test_there_are_fifteen_subclasses() -> None:
    """Pins the inventory. If this fails, a class was added or removed and the
    codes table in the spec needs the same edit."""
    assert len(subclasses()) == 15


def test_to_dict_carries_code_and_message() -> None:
    payload = UnknownProcedure("nosuch").to_dict()
    assert payload["code"] == "unknown_procedure"
    assert "nosuch" in payload["message"]


def test_unknown_procedure_suggests_near_matches() -> None:
    """The single most likely model error is a slightly wrong id."""
    payload = UnknownProcedure("lipogramm").to_dict()
    assert "lipogram" in payload["detail"]["suggestions"]


def test_unknown_procedure_survives_a_hopeless_id() -> None:
    payload = UnknownProcedure("zzzzzz").to_dict()
    assert payload["detail"]["suggestions"] == []


def test_missing_capability_names_the_extra_that_supplies_it() -> None:
    payload = MissingCapability("dactylic_hexameter", "en", "stress").to_dict()
    assert payload["code"] == "missing_capability"
    assert payload["detail"]["capability"] == "stress"
    assert "denckring[en]" in payload["message"]


def test_invalid_params_carries_the_field_errors() -> None:
    from denckring import check

    with pytest.raises(InvalidParams) as caught:
        check("pangrammatic_window", "text", max_length=3)
    payload = caught.value.to_dict()
    assert payload["code"] == "invalid_params"
    assert payload["detail"]
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_error_codes.py -v`
Expected: FAIL — `code` does not exist.

- [x] **Step 3: Add `code` and `to_dict()` to the base**

In `src/denckring/core/errors.py`, replace the base class:

```python
class DenckringError(Exception):
    """Base class for every error the library raises.

    `code` is a stable string rather than the class name, so renaming a class
    does not break a client reading the JSON. `to_dict` is what an agentic
    caller sees instead of a traceback.
    """

    #: Stable, snake_case, unique across subclasses. Asserted by the suite.
    code: str = ""

    def detail(self) -> dict[str, Any]:
        """Machine-readable specifics. Subclasses override; the base has none."""
        return {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "detail": self.detail()}
```

Add `from typing import Any` at the top of the file in the same edit — a repo hook strips imports that are momentarily unused.

- [x] **Step 4: Give every subclass its code**

Add one `code` line to each of the fifteen. Use the snake_case of the class name unless the table below says otherwise:

| Class | `code` |
|---|---|
| `UnknownProcedure` | `unknown_procedure` |
| `UnknownLanguage` | `unknown_language` |
| `MissingCapability` | `missing_capability` |
| `InvalidParams` | `invalid_params` |
| `DuplicateProcedure` | `duplicate_procedure` |
| `UnknownDevice` | `unknown_device` |
| `UnsettablePhrase` | `unsettable_phrase` |
| `InputTooLong` | `input_too_long` |
| `NoCandidateWord` | `no_candidate_word` |
| `MalformedTable` | `malformed_table` |
| `MalformedCorpus` | `malformed_corpus` |
| `UnknownFigure` | `unknown_figure` |
| `UnknownLevel` | `unknown_level` |
| `DuplicatePack` | `duplicate_pack` |
| `MalformedDevice` | `malformed_device` |
| `MalformedFigure` | `malformed_figure` |

- [x] **Step 5: Override `detail()` where there is something to say**

```python
class UnknownProcedure(DenckringError):
    code = "unknown_procedure"

    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        self.suggestions = _near(procedure_id)
        hint = f" Did you mean: {', '.join(self.suggestions)}?" if self.suggestions else ""
        super().__init__(
            f"No procedure with id {procedure_id!r}. "
            f"Run `denckring list` to see the registered procedures.{hint}"
        )

    def detail(self) -> dict[str, Any]:
        return {"procedure_id": self.procedure_id, "suggestions": self.suggestions}
```

And the helper, above the class:

```python
def _near(procedure_id: str, limit: int = 3) -> list[str]:
    """Ids whose id, name or alias contains the needle, then closest by edit distance.

    Imported lazily because `core.catalogue` imports this module — a module-level
    import would be circular.
    """
    from difflib import get_close_matches

    from denckring.core import catalogue

    needle = procedure_id.casefold()
    contains = [
        candidate
        for candidate in catalogue.ids()
        if needle in candidate.casefold()
        or any(
            needle in field.casefold()
            for field in [*catalogue.get(candidate).names.values(), *catalogue.get(candidate).aliases]
        )
    ]
    if contains:
        return contains[:limit]
    return get_close_matches(needle, list(catalogue.ids()), n=limit, cutoff=0.7)
```

`MissingCapability.detail()` returns `{"capability", "lang", "procedure_id"}`; `InvalidParams.detail()` returns `{"errors": self.errors}` if it carries them, otherwise `{}`; `InputTooLong.detail()` returns `{"limit", "received"}`. Read each class before writing its `detail()` — use the attributes it already sets, do not invent new ones.

- [x] **Step 6: Run the tests**

Run: `uv run pytest tests/test_error_codes.py -v`
Expected: PASS.

If `test_there_are_fifteen_subclasses` fails, count them with
`uv run python -c "import inspect; from denckring.core import errors; print(len([c for _,c in inspect.getmembers(errors, inspect.isclass) if issubclass(c, errors.DenckringError) and c is not errors.DenckringError]))"`
and fix the **assertion** to the real number — then say so in your report, because the spec's inventory needs the same correction.

- [x] **Step 7: Full suite, lint, type-check**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
```

- [x] **Step 8: Commit**

```bash
git add src/denckring/core/errors.py tests/test_error_codes.py
git commit -m "feat: give every error a stable code and a machine-readable form"
```

---

### Task 2: `describe`, `summaries` and `runnable`

**Files:**
- Create: `src/denckring/core/describe.py`
- Modify: `src/denckring/__init__.py`
- Test: `tests/test_describe.py` (create)

**Interfaces:**
- Consumes: Task 1's error codes (only indirectly — `describe` raises `UnknownProcedure` unchanged).
- Produces:
  - `Summary(BaseModel)` with `id, name, definition, family, kind, runnable`
  - `Scholarly(BaseModel)` with `source, attribution, attested, aliases, notes`
  - `Description(BaseModel)` with `id, name, definition, prompt_hints, family, kind, checkability, languages, requires, runnable, missing, params, scholarly`
  - `describe(procedure_id: str, *, lang: Lang = "en", scholarly: bool = False) -> Description`
  - `summaries(*, query: str | None = None, family: str | None = None, runnable_only: bool = False, lang: Lang = "en") -> list[Summary]`
  - `runnable(meta: Meta, lang: Lang = "en") -> tuple[bool, list[str]]`

- [x] **Step 1: Write the failing test**

Create `tests/test_describe.py`:

```python
"""The machine-readable view of the catalogue."""

import pytest

from denckring import describe, summaries
from denckring.core.describe import runnable
from denckring.core.errors import UnknownProcedure
from denckring.core.catalogue import get as meta_for


def test_describe_carries_what_the_loop_needs() -> None:
    described = describe("lipogram")
    assert described.id == "lipogram"
    assert described.name
    assert described.definition
    assert described.kind in {"restrictive", "constructive", "both"}
    assert "properties" in described.params


def test_the_param_schema_is_the_real_one() -> None:
    """Free from Pydantic, and the descriptions are already written."""
    described = describe("serial_lipogram")
    assert "unit" in described.params["properties"]
    assert described.params["properties"]["unit"]["enum"] == ["paragraph", "line"]


def test_scholarly_is_absent_unless_asked_for() -> None:
    """Browsing eighty procedures must not silently cost eighty provenance records."""
    assert describe("lipogram").scholarly is None
    assert describe("lipogram", scholarly=True).scholarly is not None


def test_scholarly_carries_the_apparatus() -> None:
    apparatus = describe("lipogram", scholarly=True).scholarly
    assert apparatus is not None
    assert apparatus.source


def test_an_unknown_id_raises_with_suggestions() -> None:
    with pytest.raises(UnknownProcedure):
        describe("lipogramm")


def test_summaries_lists_every_implemented_procedure() -> None:
    rows = summaries()
    assert len(rows) == 86
    assert all(row.id and row.name for row in rows)


def test_query_matches_ids_names_and_aliases() -> None:
    found = {row.id for row in summaries(query="lipogram")}
    assert "lipogram" in found
    assert "serial_lipogram" in found


def test_family_filters() -> None:
    rows = summaries(family="form")
    assert rows
    assert all(row.family == "form" for row in rows)


def test_runnable_only_hides_what_this_install_cannot_run() -> None:
    """A model offered a procedure it cannot run gets an error it cannot fix."""
    every = summaries()
    only = summaries(runnable_only=True)
    assert len(only) <= len(every)
    assert all(row.runnable for row in only)


def test_runnable_reports_what_is_missing() -> None:
    ok, missing = runnable(meta_for("dactylic_hexameter"))
    if not ok:
        assert "stress" in missing


def test_renga_is_runnable_wherever_haiku_is() -> None:
    """The syllabic batch's last defect: renga and haibun were gated on a
    capability nothing calls, which would have hidden two working procedures
    from every model on a core-only install."""
    assert runnable(meta_for("renga"))[0] == runnable(meta_for("haiku"))[0]
    assert runnable(meta_for("haibun"))[0] == runnable(meta_for("haiku"))[0]
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_describe.py -v`
Expected: FAIL — `cannot import name 'describe'`.

- [x] **Step 3: Write the module**

Create `src/denckring/core/describe.py`:

```python
"""The catalogue as a machine reads it.

Four callers need this assembly — the CLI's `show`, the explorer, the MCP
server and the skill — so it lives here rather than in any one of them.
Computing it four times is how four copies drift apart.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from denckring.core import catalogue
from denckring.core.protocol import Lang, Meta
from denckring.core.registry import all_procedures, get


class Scholarly(BaseModel):
    """Where a procedure comes from. Returned only when asked for."""

    source: str
    attribution: str
    attested: str
    aliases: list[str]
    notes: str | None


class Summary(BaseModel):
    """One catalogue row, compact enough to list eighty of."""

    id: str
    name: str
    definition: str
    family: str
    kind: str
    runnable: bool


class Description(BaseModel):
    """Everything a model needs to use one procedure."""

    id: str
    name: str
    definition: str
    prompt_hints: str | None
    family: str
    kind: str
    checkability: str
    languages: list[str]
    requires: list[str]
    runnable: bool
    missing: list[str]
    params: dict[str, Any]
    scholarly: Scholarly | None = None


def runnable(meta: Meta, lang: Lang = "en") -> tuple[bool, list[str]]:
    """Whether this install can run the procedure, and what it lacks.

    Returns rather than raises, because the caller is deciding what to offer
    rather than executing anything.
    """
    from denckring.lang import get_pack

    try:
        pack = get_pack(lang)
    except Exception:
        return False, list(meta.requires)
    missing = [cap for cap in meta.requires if cap not in pack.capabilities]
    return not missing, missing


def _text(mapping: dict[Lang, str], lang: Lang) -> str:
    """The requested language, falling back to English, then to anything."""
    if lang in mapping:
        return mapping[lang]
    if "en" in mapping:
        return mapping["en"]
    return next(iter(mapping.values()), "")


def describe(procedure_id: str, *, lang: Lang = "en", scholarly: bool = False) -> Description:
    """One procedure, in full. Raises `UnknownProcedure` for an unknown id."""
    meta = catalogue.get(procedure_id)
    procedure = get(procedure_id)
    ok, missing = runnable(meta, lang)
    return Description(
        id=meta.id,
        name=_text(meta.names, lang),
        definition=_text(meta.definitions, lang),
        prompt_hints=meta.prompt_hints.get(lang) or meta.prompt_hints.get("en"),
        family=meta.family,
        kind=meta.kind,
        checkability=meta.checkability,
        languages=list(meta.languages),
        requires=list(meta.requires),
        runnable=ok,
        missing=missing,
        params=procedure.params_model().model_json_schema(),
        scholarly=(
            Scholarly(
                source=meta.source,
                attribution=meta.attribution,
                attested=meta.attested,
                aliases=list(meta.aliases),
                notes=meta.notes,
            )
            if scholarly
            else None
        ),
    )


def _matches(meta: Meta, needle: str) -> bool:
    haystack = [meta.id, *meta.names.values(), *meta.aliases]
    return any(needle in field.casefold() for field in haystack)


def summaries(
    *,
    query: str | None = None,
    family: str | None = None,
    runnable_only: bool = False,
    lang: Lang = "en",
) -> list[Summary]:
    """The implemented procedures, filtered. `query` subsumes search.

    Only implemented rows appear: the other 66 catalogued forms have no checker,
    so offering them would be offering something that cannot run.
    """
    needle = query.casefold() if query else None
    rows: list[Summary] = []
    for procedure_id in all_procedures():
        meta = catalogue.get(procedure_id)
        if needle and not _matches(meta, needle):
            continue
        if family and meta.family != family:
            continue
        ok, _ = runnable(meta, lang)
        if runnable_only and not ok:
            continue
        rows.append(
            Summary(
                id=meta.id,
                name=_text(meta.names, lang),
                definition=_text(meta.definitions, lang),
                family=meta.family,
                kind=meta.kind,
                runnable=ok,
            )
        )
    return rows
```

- [x] **Step 4: Export from the package**

In `src/denckring/__init__.py`, add to the imports and to `__all__`:

```python
from denckring.core.describe import Description, Scholarly, Summary, describe, summaries
```

`__all__` gains `"Description"`, `"Scholarly"`, `"Summary"`, `"describe"`, `"summaries"`, keeping the list alphabetical as it already is. **Do not touch `list_procedures`.**

- [x] **Step 5: Run the tests**

Run: `uv run pytest tests/test_describe.py -v`
Expected: PASS.

If `test_summaries_lists_every_implemented_procedure` fails on the count, the registry has grown — fix the assertion to `len(all_procedures())` rather than a literal, and say so in your report.

- [x] **Step 6: Full suite, lint, type-check**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
```

- [x] **Step 7: Commit**

```bash
git add src/denckring/core/describe.py src/denckring/__init__.py tests/test_describe.py
git commit -m "feat: add describe and summaries, the catalogue as a machine reads it"
```

---

### Task 3: CLI parity — `describe --json` and `list --json`

**Files:**
- Modify: `src/denckring/cli.py`
- Test: `tests/test_cli_json.py` (create)

**Interfaces:**
- Consumes: `describe`, `summaries` from Task 2.
- Produces: `denckring describe <id> [--json] [--scholarly]` and `denckring list [--json]`, which the skill in Task 5 shells out to.

- [x] **Step 1: Write the failing test**

Create `tests/test_cli_json.py`:

```python
"""The skill reaches the package through these, so their JSON is a contract."""

import json

from typer.testing import CliRunner

from denckring.cli import app

runner = CliRunner()


def test_describe_json_is_parseable_and_complete() -> None:
    result = runner.invoke(app, ["describe", "lipogram", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["id"] == "lipogram"
    assert "params" in payload
    assert payload["scholarly"] is None


def test_describe_scholarly_flag() -> None:
    result = runner.invoke(app, ["describe", "lipogram", "--json", "--scholarly"])
    payload = json.loads(result.stdout)
    assert payload["scholarly"]["source"]


def test_list_json_is_a_list_of_summaries() -> None:
    result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert payload[0]["id"]
    assert "runnable" in payload[0]


def test_describe_reports_an_unknown_id_without_a_traceback() -> None:
    result = runner.invoke(app, ["describe", "nosuch", "--json"])
    assert result.exit_code != 0
    assert "Traceback" not in result.stdout
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_cli_json.py -v`
Expected: FAIL — no `describe` command.

- [x] **Step 3: Add the command and the flag**

In `src/denckring/cli.py`, add beside the existing `show` command:

```python
@app.command("describe")
def describe_command(
    procedure_id: str,
    as_json: Annotated[bool, typer.Option("--json")] = False,
    scholarly: Annotated[bool, typer.Option("--scholarly")] = False,
    lang: Annotated[str, typer.Option("--lang")] = "en",
) -> None:
    """A procedure as a machine reads it: definition, hints, parameter schema."""
    try:
        described = describe(procedure_id, lang=_lang(lang), scholarly=scholarly)
    except DenckringError as exc:
        _fail(exc)
        return
    if as_json:
        typer.echo(described.model_dump_json(indent=2))
        return
    typer.echo(f"{described.id}  {described.name}")
    typer.echo(described.definition)
    if described.prompt_hints:
        typer.echo(f"\nHint: {described.prompt_hints}")
    if not described.runnable:
        typer.echo(f"\nNot runnable here — missing: {', '.join(described.missing)}")
```

Add `--json` to the existing `list` command, emitting `summaries()`:

```python
    if as_json:
        rows = summaries(family=family, lang=_lang(lang))
        typer.echo(json.dumps([row.model_dump() for row in rows], indent=2))
        return
```

Read the existing `list_command` before editing — reuse whatever parameters it already has for family and language rather than adding duplicates. Add `import json` and the `describe`/`summaries` imports in the same edit.

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/test_cli_json.py -v`
Expected: PASS.

- [x] **Step 5: Full suite, lint, type-check, then commit**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
git add src/denckring/cli.py tests/test_cli_json.py
git commit -m "feat: add describe --json and list --json to the CLI"
```

---

### Task 4: The MCP server

**Files:**
- Create: `src/denckring/mcp/__init__.py`, `src/denckring/mcp/server.py`
- Modify: `pyproject.toml`
- Test: `tests/test_mcp_tools.py` (create)

**Interfaces:**
- Consumes: `describe`, `summaries` (Task 2); `to_dict()` (Task 1).
- Produces: `list_procedures_tool`, `describe_procedure_tool`, `check_text_tool`, `apply_procedure_tool`, and `main()`.

**The tool functions must be importable and callable without a running client.** Define each as a plain module-level function, then register it with the decorator — do not define the body inside a decorator call. The tests call the plain functions.

- [x] **Step 1: Add the extra and the script**

In `pyproject.toml`:

```toml
[project.optional-dependencies]
# Exact syllable counts and rhyme, from the CMU Pronouncing Dictionary.
en = ["denckring-en-data"]
# Word membership and a noun list for German, from Wikidata Lexemes.
de = ["denckring-de-data"]
# An MCP server, so a model can check its own constrained writing.
mcp = ["mcp[cli]>=2"]

[project.scripts]
denckring = "denckring.cli:app"
denckring-mcp = "denckring.mcp.server:main"
```

Then `uv sync --extra mcp` and confirm `uv run python -c "from mcp.server import MCPServer; print('ok')"` prints `ok`. **If that import fails, stop and report it** — the class was renamed by the 2026-07-28 spec revision and the plan's assumption needs correcting rather than working around.

- [x] **Step 2: Write the failing test**

Create `tests/test_mcp_tools.py`:

```python
"""The four tools, called directly. No client, no transport."""

import pytest

pytest.importorskip("mcp", reason="needs denckring[mcp]")

from denckring.mcp.server import (  # noqa: E402
    apply_procedure_tool,
    check_text_tool,
    describe_procedure_tool,
    list_procedures_tool,
)


def test_list_returns_summaries() -> None:
    rows = list_procedures_tool()
    assert rows
    assert rows[0]["id"]


def test_list_filters_by_query() -> None:
    rows = list_procedures_tool(query="lipogram")
    assert {row["id"] for row in rows} >= {"lipogram", "serial_lipogram"}


def test_describe_returns_the_param_schema() -> None:
    described = describe_procedure_tool("lipogram")
    assert "properties" in described["params"]


def test_check_returns_a_report() -> None:
    report = check_text_tool("lipogram", "brown fox", {"forbidden": "e"})
    assert report["satisfied"] is True


def test_check_reports_a_violation_a_model_can_act_on() -> None:
    report = check_text_tool("lipogram", "the fence", {"forbidden": "e"})
    assert report["satisfied"] is False
    assert report["violations"][0]["rule"] == "forbidden_letter"
    assert report["violations"][0]["offset"] is not None


def test_an_unknown_procedure_is_data_not_an_exception() -> None:
    """A raised error reaches the model as a transport failure it cannot read."""
    result = check_text_tool("nosuch", "text")
    assert result["code"] == "unknown_procedure"
    assert result["detail"]["suggestions"] == []


def test_bad_params_are_data_not_an_exception() -> None:
    result = check_text_tool("pangrammatic_window", "text", {"max_length": 3})
    assert result["code"] == "invalid_params"


def test_apply_returns_text() -> None:
    result = apply_procedure_tool("n_plus_7", "the cat sleeps")
    assert result["text"]
    assert result["text"] != "the cat sleeps"


def test_apply_on_a_restrictive_procedure_is_data_not_an_exception() -> None:
    result = apply_procedure_tool("lipogram", "text", {"forbidden": "e"})
    assert "code" in result
```

- [x] **Step 3: Run to verify it fails**

Run: `uv run pytest tests/test_mcp_tools.py -v`
Expected: FAIL — no module `denckring.mcp.server`.

- [x] **Step 4: Write the server**

Create `src/denckring/mcp/__init__.py` containing only a docstring, and `src/denckring/mcp/server.py`:

```python
"""An MCP server over the catalogue.

Four tools, with the procedure as a parameter. One tool per procedure would put
eighty-six definitions in every client's context; model performance degrades
sharply with tool count.

Nothing here computes anything. The tools call `describe`, `summaries` and
`check`, and convert `DenckringError` into data — a model can act on
`{"code": "invalid_params", ...}` and cannot act on a traceback.
"""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from denckring import check, describe, summaries
from denckring.core.errors import DenckringError
from denckring.core.protocol import Lang
from denckring.core.registry import get

server = MCPServer("denckring")


def list_procedures_tool(
    query: str | None = None,
    family: str | None = None,
    runnable_only: bool = False,
    lang: Lang = "en",
) -> list[dict[str, Any]] | dict[str, Any]:
    """List the writing procedures this install can run.

    `query` matches ids, names and aliases. Call this before `check_text` if you
    do not already know a procedure's id.
    """
    try:
        rows = summaries(query=query, family=family, runnable_only=runnable_only, lang=lang)
    except DenckringError as exc:
        return exc.to_dict()
    return [row.model_dump() for row in rows]


def describe_procedure_tool(
    procedure: str, scholarly: bool = False, lang: Lang = "en"
) -> dict[str, Any]:
    """Describe one procedure: what it constrains, and its parameter schema.

    `params` is JSON Schema — pass parameters matching it to `check_text`. Set
    `scholarly` for the form's source, attribution and history.
    """
    try:
        return describe(procedure, lang=lang, scholarly=scholarly).model_dump()
    except DenckringError as exc:
        return exc.to_dict()


def check_text_tool(
    procedure: str,
    text: str,
    params: dict[str, Any] | None = None,
    lang: Lang = "en",
) -> dict[str, Any]:
    """Check whether a text satisfies a procedure's constraint.

    Returns `satisfied`, a `score`, and `violations`. Each violation names the
    rule it broke, what it `found` and what was `expected`, and usually carries
    an `offset` into the text. Fixing the first violation listed is normally the
    fastest route to a satisfied report.
    """
    try:
        return check(procedure, text, lang=lang, **(params or {})).model_dump()
    except DenckringError as exc:
        return exc.to_dict()


def apply_procedure_tool(
    procedure: str,
    text: str,
    params: dict[str, Any] | None = None,
    lang: Lang = "en",
) -> dict[str, Any]:
    """Run a procedure that generates rather than only checks.

    Sixteen of the procedures are constructive; the rest only check. Use
    `describe_procedure` and read `kind` before calling this.
    """
    try:
        procedure_object = get(procedure)
        apply = getattr(procedure_object, "apply", None)
        if apply is None:
            return {
                "code": "not_constructive",
                "message": f"{procedure!r} only checks; it has no generator.",
                "detail": {"procedure_id": procedure},
            }
        return {"text": apply(text, lang=lang, **(params or {}))}
    except DenckringError as exc:
        return exc.to_dict()


for _tool in (
    list_procedures_tool,
    describe_procedure_tool,
    check_text_tool,
    apply_procedure_tool,
):
    server.tool()(_tool)


def main() -> None:
    """Entry point for `denckring-mcp`."""
    server.run()
```

If `server.tool()` or `server.run()` does not exist under SDK v2, read the SDK's own quickstart and use what it documents — then report the difference. Do not guess a third name.

- [x] **Step 5: Run the tests**

Run: `uv run pytest tests/test_mcp_tools.py -v`
Expected: PASS.

- [x] **Step 6: Confirm the suite still skips cleanly without the extra**

Run: `uv run --no-extra mcp pytest tests/test_mcp_tools.py -q`
Expected: all tests SKIPPED, none errored. If they error instead of skipping, the `importorskip` is in the wrong place — it must precede the `denckring.mcp.server` import.

- [x] **Step 7: Full suite, lint, type-check, then commit**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy --strict src tests packages/denckring-en-data/src packages/denckring-de-data/src
git add pyproject.toml src/denckring/mcp tests/test_mcp_tools.py
git commit -m "feat: add an MCP server behind denckring[mcp]"
```

---

### Task 5: The Claude Code skill

**Files:**
- Create: `skills/denckring/SKILL.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the CLI commands from Task 3.
- Produces: nothing later tasks use.

- [x] **Step 1: Write the skill**

Create `skills/denckring/SKILL.md`. There is no `skills/` directory yet — create it.

```markdown
---
name: denckring
description: Use when writing under a formal constraint — a lipogram, a haiku, a sestina, a metre — or when a text must be checked against one. Gives 86 procedures with mechanical validators that say exactly which rule broke and where.
---

# Writing under constraint with denckring

`denckring` catalogues 152 formal writing procedures and implements 86 of them.
Every implemented one has a validator, so a constrained text can be checked
rather than guessed at.

## Finding a procedure

```bash
denckring list --json                  # every runnable procedure
denckring list --json | jq '.[] | select(.family=="form")'
denckring describe haiku --json        # definition, hints, parameter schema
```

`describe` returns `params` as JSON Schema. Pass parameters matching it.

## Checking a text

```bash
denckring check lipogram poem.txt --json -p forbidden=e
echo "brown fox" | denckring check lipogram - --json -p forbidden=e
```

The text comes from a **positional file path**, or `-` for stdin. There is no
`--text` flag. Parameters are `-p key=value`, repeatable.

The report gives `satisfied`, a `score`, and `violations`. Each violation names
the rule, what it `found`, what was `expected`, and usually an `offset` into the
text.

**Work the loop:** write, check, read the first violation, fix that, check
again. The offset points at the character that broke the rule.

## Generating

Sixteen procedures generate as well as check — including the combinatorial
devices (`denckring`, `ideenwuerfeln`, `llull_figure`) which cannot sensibly be
imitated by writing prose.

```bash
denckring apply n_plus_7 poem.txt
echo "the cat sleeps" | denckring apply n_plus_7 -
```

Read `kind` from `describe` first: `restrictive` procedures only check.

## When a procedure is not available

Some need extra data. `describe` reports `runnable` and `missing`; install the
extra it names, e.g. `pip install denckring[en]` for syllable and stress data.
```

- [x] **Step 2: Verify every command in the skill actually runs**

Run each one and confirm the output is what the skill claims:

```bash
denckring list --json | head -20
denckring describe haiku --json
echo "brown fox" | denckring check lipogram - --json -p forbidden=e
echo "the cat sleeps" | denckring apply n_plus_7 -
```

The last two are **verified working** as written — the third prints a report with
`"satisfied": true`. `check` and `apply` both take a positional file path or `-`
for stdin; neither has a `--text` flag, and parameters are `-p key=value`. A skill
whose commands do not run is worse than no skill: if any command here fails, fix
the **document**, never the CLI.

- [x] **Step 3: Note the skill in the README**

Add a short section under the existing usage documentation pointing at
`skills/denckring/SKILL.md` and at `pip install denckring[mcp]` for the server.
Match the README's existing voice.

- [x] **Step 4: Full suite and commit**

```bash
uv run pytest -q
git add skills README.md
git commit -m "docs: add the Claude Code skill and note both agentic entry points"
```

---

### Task 6: CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

- [x] **Step 1: Read the established format**

```bash
git show 6432a49 -- CHANGELOG.md
git show 68bbf40 -- CHANGELOG.md
```

Match their format and voice — prose in bullets, explaining why, not bare list items.

- [x] **Step 2: Write the entry**

Cover: `describe` and `summaries` in core; stable `code` and `to_dict()` on all
fifteen error classes, with near-match suggestions on `UnknownProcedure`;
`describe --json` and `list --json`; the MCP server behind `denckring[mcp]` with
its four tools and why it is four rather than eighty-six; the Claude Code skill.
Note that `list_procedures()` is unchanged.

- [x] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: record the agentic integration"
```

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: core additions to Task 2;
errors as data to Task 1; the MCP server to Task 4; the skill to Task 5; CLI
parity — which the spec names as the skill's requirement — to Task 3; the
CHANGELOG to Task 6. The spec's testing table maps to `tests/test_describe.py`
(Task 2), `tests/test_error_codes.py` (Task 1) and `tests/test_mcp_tools.py`
(Task 4). The spec's `tests/test_runnable.py` is folded into `test_describe.py`
rather than given its own file, because `runnable` is three lines and its tests
read naturally beside `summaries`'. The round-trip-through-the-tools test the
spec mentions is **not** included: the existing `tests/test_round_trip.py`
already proves the property directly, and re-proving it through a transport
tests the transport, not the property.

**Ordering.** Task 1 before Task 2 only loosely — `describe` raises
`UnknownProcedure` but does not read its code. Task 3 needs Task 2. Task 4 needs
both 1 and 2. Task 5 needs Task 3. Sequential execution satisfies all of it.

**Type consistency.** `Description`, `Summary` and `Scholarly` are defined in
Task 2 and used by name in Tasks 3 and 4. `to_dict() -> dict[str, Any]` is
defined in Task 1 and called in Task 4. `runnable(meta, lang) -> tuple[bool,
list[str]]` is defined and used only in Task 2. The tool functions' names carry
a `_tool` suffix in Tasks 4's tests and implementation alike.

**Two places the implementer must determine rather than transcribe**, both
bounded by a test:

- Task 4 Step 1 asks for confirmation that `from mcp.server import MCPServer`
  imports. The class was renamed by the 2026-07-28 spec revision and I verified
  it against the SDK repository on 2026-08-18, but a v2 point release could move
  it again. The instruction is to stop and report rather than guess.
- Task 5's CLI examples were wrong in the first draft — I wrote `--text`, which
  does not exist. Corrected and verified by running: `check` and `apply` take a
  positional file path or `-` for stdin, and parameters are `-p key=value`.
  `echo "brown fox" | denckring check lipogram - --json -p forbidden=e` returns
  `"satisfied": true`. The implementer transcribes rather than determines.
