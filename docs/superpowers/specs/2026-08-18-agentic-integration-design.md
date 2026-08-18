# denckring — agentic integration

**Date:** 2026-08-18
**Status:** draft
**Scope:** a machine-readable surface for the package, exposed as an MCP server and a Claude Code skill

## Purpose

Let a model write under a procedure's constraint, check its own output, read the
violations, and revise — and let it browse the catalogue well enough to choose a procedure
in the first place.

The writing loop is the product. This package is unusually suited to it: the project's
thesis is that the validator is the eval, so every one of the 86 implemented procedures
returns a mechanical verdict with a rule name, an offset, and `found` against `expected`.
That is a gradient a model can follow. Browsing is the thin part that feeds it.

```
model writes a lipogram avoiding "e"
  → check_text("lipogram", text, {"forbidden": "e"})
  → forbidden_letter at offset 34: found "e", expected a line without "e"
model rewrites that word
  → satisfied
```

Two transports ship: an MCP server for any client, and a Claude Code skill wrapping the
CLI. They share the same core functions rather than a common adapter layer, so they cannot
drift.

## What already exists

More than expected. This is mostly a shaping problem.

| Component | What it gives us |
|---|---|
| `Meta` (`core/catalogue.py`) | Per row: `id`, `names`, `definitions`, `source`, `family`, `attribution`, `checkability`, `attested`, `aliases`, `kind`, `languages`, `requires`, `deterministic`, `prompt_hints`, `notes`. `prompt_hints` was added for exactly this use. |
| `params_model().model_json_schema()` | Per-procedure parameter JSON Schema, free from Pydantic, with descriptions already written — `"Treat accented letters as their base letter, and ß as ss."` |
| `Report.model_dump_json()` | The verdict already serialises; `denckring check --json` already emits it. |
| `require_capability` (`core/base.py`) | The capability gate, hardened across the last two batches. |
| Error taxonomy (`core/errors.py`) | `UnknownProcedure`, `InvalidParams`, `MissingCapability`, `InputTooLong`, `NoCandidateWord`, all under `DenckringError`. |

## Decisions

| Decision | Rationale |
|---|---|
| **Four tools, with the procedure as a parameter** | One tool per procedure would put 86 tool definitions in every client's context. Model performance degrades sharply with tool count, and the client would be unusable for anything else. `check_text(procedure=…)` is one definition serving all 86. |
| `procedure` is a **free string, not an enum** | An enum of 86 ids would bloat every tool definition in the model's context window, on every request, to save one `list_procedures` call. `UnknownProcedure` already exists to catch the miss, and gains near-match suggestions drawn from the same aliases `denckring search` uses. |
| `describe()` and `summaries()` live in **core**, not in the server | Four callers need them: the CLI's `show`, `apps/explorer`, the MCP server and the skill. Assembling `Meta` + parameter schema + runnability separately in each is how four copies drift apart. The transports stay thin. |
| `list_procedures()` is **not changed** | It is public, exported in `__all__`, and returns `list[str]`. Changing its return type would break callers silently. `summaries()` is added alongside it. |
| Ships as **`denckring[mcp]`**, a core extra | Matches the existing `denckring[en]` / `denckring[de]` pattern; one package, one version, `pip install denckring[mcp]`. ADR 0013 separated the data packs for their size and their distinct licences — neither applies to a small pure-code server. |
| `describe()` is **lean by default** | The catalogue carries real scholarship — sources, attribution, attestation, contested-history notes — and every field costs a model's context. The default returns what the loop needs; `scholarly=True` returns the apparatus. Nothing is hidden, but browsing eighty procedures does not silently cost eighty provenance records. |
| `apply_procedure` **ships in v1** | Sixteen of the 86 implemented rows are constructive — counted, not estimated: `anagram`, `arca_musarithmica`, `cent_mille_milliards`, `cut_up`, `denckring`, `every_nth_word`, `ideenwuerfeln`, `llull_figure`, `melting_text`, `n_plus_7`, `paragram`, `pasigraphy`, `recombination`, `s_plus_7`, `slenderizing`, `wechselsatz`. That is 19%, not the tenth I first assumed, and it includes the combinatorial devices — `denckring` itself, `ideenwuerfeln`, `llull_figure` — which are the ones a model cannot usefully imitate by writing. `apply` is the only way to reach them. |
| Errors are returned as **structured data** | A traceback is not actionable. `"max_length must be at least 26; you passed 20"` is. Every `DenckringError` gains a stable `code` and serialises to a result the model can act on. |

## Components

### 1. Core additions

`src/denckring/core/describe.py`, exported from `denckring`:

```python
class Summary(BaseModel):
    """One catalogue row, compact enough to list eighty of."""
    id: str
    name: str            # names[lang], falling back to names["en"]
    definition: str      # definitions[lang], first sentence
    family: str
    kind: str            # restrictive | constructive | both
    runnable: bool


class Description(BaseModel):
    """Everything a model needs to use one procedure."""
    id: str
    name: str
    definition: str
    prompt_hints: str | None  # prompt_hints[lang]; the field is dict[Lang, str]
    family: str
    kind: str
    checkability: str
    languages: list[str]
    requires: list[str]
    runnable: bool
    missing: list[str]          # capabilities absent from the installed pack
    params: dict[str, Any]      # JSON Schema from params_model()
    scholarly: Scholarly | None # None unless requested


class Scholarly(BaseModel):
    source: str
    attribution: str
    attested: str
    aliases: list[str]
    notes: str | None
```

Three functions:

- **`describe(procedure_id, *, lang="en", scholarly=False) -> Description`**
- **`summaries(*, query=None, family=None, runnable_only=False, lang="en") -> list[Summary]`** —
  `query` matches ids, names and aliases, the same matching `denckring search` performs, so
  `summaries` subsumes search rather than adding a fifth tool.
- **`runnable(meta, pack) -> tuple[bool, list[str]]`** — the row's `requires` against the
  installed pack's capabilities, returning what is missing rather than raising.

`runnable` matters more than it looks. A model offered `dactylic_hexameter` on a core-only
install would get a `MissingCapability` it cannot fix. The inverse — a working procedure
reported unavailable — is why the syllabic batch's final finding mattered: `renga` and
`haibun` were gated on a capability nothing calls, and would have been hidden from every
model on a core-only install.

### 2. Errors as data

`DenckringError` gains a `code: str` class attribute and a `to_dict()` returning
`{"code", "message", "detail"}`. Codes are stable strings, not class names, so renaming a
class does not break a client.

There are **fifteen** subclasses, not the handful the loop meets most often: `UnknownProcedure`,
`UnknownLanguage`, `MissingCapability`, `InvalidParams`, `DuplicateProcedure`, `UnknownDevice`,
`UnsettablePhrase`, `InputTooLong`, `NoCandidateWord`, `MalformedTable`, `MalformedCorpus`,
`UnknownFigure`, `UnknownLevel`, `DuplicatePack`. Every one gets a code — a test asserts the set
is complete and unique, so a subclass added later without one fails rather than reaching a model
as an unlabelled failure. The table below details only those the agentic surface raises in normal
use; the rest take the obvious snake_case of their class name.

| Error | `code` | `detail` carries |
|---|---|---|
| `UnknownProcedure` | `unknown_procedure` | `procedure_id`, and `suggestions` — near matches from ids and aliases |
| `InvalidParams` | `invalid_params` | The Pydantic validation errors, per field |
| `MissingCapability` | `missing_capability` | `capability`, `lang`, and the extra that supplies it (`denckring[en]`) |
| `InputTooLong` | `input_too_long` | `limit`, `received` |
| `NoCandidateWord` | `no_candidate_word` | `procedure_id` |

`UnknownProcedure` gaining suggestions is the one behavioural change to an existing class.
It is additive: the message keeps its current text and gains a sentence.

### 3. The MCP server

`src/denckring/mcp/server.py`, behind the `mcp` extra.

Verified against the SDK source on 2026-08-18: the current stable line is **v2**, the server
class is **`MCPServer`**, imported as `from mcp.server import MCPServer`, and the install is
`mcp[cli]`. The 2026-07-28 specification revision renamed `FastMCP` to `MCPServer`; code or
documentation naming `FastMCP` is describing the v1 line.

```toml
[project.optional-dependencies]
mcp = ["mcp[cli]>=2"]

[project.scripts]
denckring-mcp = "denckring.mcp.server:main"
```

Four tools, each a thin function over the core:

| Tool | Signature | Returns |
|---|---|---|
| `list_procedures` | `(query: str \| None, family: str \| None, runnable_only: bool = False, lang: Lang = "en")` | `list[Summary]` |
| `describe_procedure` | `(procedure: str, scholarly: bool = False, lang: Lang = "en")` | `Description` |
| `check_text` | `(procedure: str, text: str, params: dict \| None, lang: Lang = "en")` | `Report` |
| `apply_procedure` | `(procedure: str, text: str, params: dict \| None, lang: Lang = "en")` | `{"text": str}` or a structured error |

Every tool catches `DenckringError` and returns `to_dict()` rather than raising, so a model
sees a result it can act on instead of a transport-level failure.

The tool docstrings are the model's instructions and are written as such: `check_text`'s
says that a violation carries an offset into the text and that the fastest repair is usually
the first violation listed.

### 4. The Claude Code skill

`skills/denckring/SKILL.md`, wrapping the CLI. No new dependency and no server process.

The CLI already has `check --json` and `status --json`. It gains `describe --json` and
`list --json`, both calling the same core functions the MCP server calls. That shared floor
is the point: the two transports cannot disagree about what a procedure is, because neither
computes it.

## Error handling

Nothing new is invented. The existing taxonomy is given stable codes and a serialisation.
The one new refusal path is the MCP layer's blanket `DenckringError` catch, which converts
rather than propagates.

A malformed `params` dict reaches `parse_params` and returns `invalid_params` carrying the
per-field detail — which is the loop working as intended: the model reads which field was
wrong and retries.

## Testing

| Test | What it protects |
|---|---|
| `tests/test_describe.py` | `describe` and `summaries` against real catalogue rows: a lean call omits the scholarly block, `scholarly=True` includes it, `query` matches an alias, `runnable_only` filters. |
| `tests/test_runnable.py` | `runnable` against a core-only pack and a data-backed one. `renga` and `haiku` must be runnable on core; `dactylic_hexameter` must not, and must report `stress` as missing. |
| `tests/test_error_codes.py` | Every `DenckringError` subclass has a unique `code` and a `to_dict()` carrying its detail. A subclass added later without a code fails the test. |
| `tests/test_mcp_tools.py` | The four tool functions called directly — they are plain functions under a decorator, so no live client is needed. Each returns serialisable output; each converts a `DenckringError` rather than raising. |
| Round trip | `check_text` on the output of `apply_procedure` is satisfied, for every constructive procedure — the existing round-trip property, reached through the tool surface. |

The suite must not require a running MCP client, and the `mcp` import is guarded so the
tests skip cleanly when the extra is not installed — matching how the data-pack tests behave.

## Out of scope

- The showcase frontend and the documentation restructure. Separate specs; both depend on
  the surface this defines, which is why this one goes first.
- Any transport beyond stdio. SSE and HTTP are a deployment question, and nothing here
  needs them.
- Exposing the 66 catalogued-but-unimplemented rows through `check`. They appear in
  `summaries` with `runnable: false`, which is honest, and attempting one raises
  `UnknownProcedure` from the registry as it does today.
- Prompt engineering the model's constrained writing. The tools report; what the model does
  with a violation is its business.
- Rate limiting, auth, telemetry. A local stdio server run by the user needs none of it.
