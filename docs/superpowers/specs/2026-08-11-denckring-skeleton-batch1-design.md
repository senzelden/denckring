# denckring — skeleton and Batch 1

**Date:** 2026-08-11
**Status:** approved
**Scope:** sub-project 1 of 5 (see *Decomposition* below)

## Purpose

`denckring` is a Python library of experimental writing procedures — lipograms,
snowballs, N+7, and several hundred more — where every procedure pairs a generator
with a validator and **the validator is the eval**. A lipogram either contains the
forbidden letter or it does not, so the acceptance criterion is intrinsic to the
procedure and no test has to be invented for it.

This spec covers the first sub-project: the structural core plus Batch 1, the twelve
pure-restriction procedures that need no lexicon, no data files and no model. It ends
with a working library, a working CLI, and a green eval run.

## Decomposition

The repo seed describes work far larger than one spec. It splits along the seams the
seed itself implies:

1. **Skeleton + Batch 1** — this spec.
2. **Catalogue as open data** — the sourced 500-entry YAML as a CC BY release.
3. **Batches 2–3** — lexicon and syllabification procedures; needs the data-licensing
   ADR first.
4. **Language packs `de` and `fr`** — proves the capability interface carries weight.
5. **Public release** — CI matrix, docs gallery, Trusted Publishing, Zenodo DOI.

Each later item gets its own spec, plan and implementation cycle.

## Decisions inherited from the seed

These are settled and not revisited here: English API with multilingual content;
`check` mandatory and `apply` optional; catalogue separate from implementation with
coverage as the project metric; language packs as capability-declaring plugins that
raise rather than silently degrade; continuous `score`; one module per procedure;
MIT for code and CC BY 4.0 for the catalogue.

## Decisions made during brainstorming

| Decision | Rationale |
|---|---|
| Catalogue owns `Meta`; modules load it | One source of truth; the catalogue stays publishable standalone; no drift between a module and its row |
| YAML only, no SQLite | A few hundred read-once rows do not need a database or the build step one implies |
| Batch 1 is `kind: restrictive`; no `apply()` | None of the twelve can generate text without a word list |
| Hypothesis strategies replace `apply()` as the generator | Closes the generator/validator loop with zero data; keeps Hypothesis a dev dependency |
| Strategies live in `tests/strategies/`, not the package | Core keeps its near-zero runtime footprint |
| `satisfied == (score == 1.0)`, always | Makes `score` a usable retry signal and gives one registry-wide invariant to test |
| Repo URLs point at `github.com/senzelden/denckring` | Nothing is pushed by this build |

## Architecture

```
src/denckring/
  __init__.py          get() · check() · list_procedures() · __version__
  core/
    protocol.py        Lang · Kind · Violation · Report · Meta · Procedure · LanguagePack
    registry.py        @register decorator + pkgutil autodiscovery over procedures/
    catalogue.py       loads data/catalogue.yaml, Meta lookup, status counts
    errors.py          DenckringError · UnknownProcedure · UnknownLanguage ·
                       MissingCapability · InvalidParams
    text.py            letters() · words() · lines() · offset bookkeeping
  lang/
    base.py            capability constants, pack registry, get_pack()
    en.py              EnglishPack
  procedures/          twelve modules, one per procedure, no collector module
  eval/
    harness.py         every procedure × fixture × declared language; scoreboard; exit code
    fixtures/golden/<id>.yaml
  scaffold/templates/  module · test · fixture · catalogue-row templates
  cli.py               typer app
data/catalogue.yaml
tests/
  strategies/<id>.py   satisfying() and violating() Hypothesis strategies
  test_golden.py       every golden fixture, over the whole registry
  test_strategies.py   strategies agree with check(), over the whole registry
  test_invariants.py   universal invariants, over the whole registry
  test_<id>.py         per-procedure specifics
docs/adr/              seven ADRs
```

**Adding a procedure edits no shared file.** The three generic suites iterate the
registry, autodiscovery finds the module, and the catalogue row is a row. This is the
property that makes parallel unattended agent batches safe, and it is the reason there
are no collector modules.

### Core types

Per the seed's §3, unchanged in shape:

```python
Lang = Literal["en", "de", "fr"]
Kind = Literal["constructive", "restrictive", "both"]

class Violation(BaseModel):
    rule: str
    offset: int | None
    found: str
    expected: str
    note: str | None = None

class Report(BaseModel):
    procedure: str
    satisfied: bool
    score: float          # 0.0–1.0, monotone in violation count
    violations: list[Violation]
    metrics: dict[str, float]

class Meta(BaseModel):
    id: str
    names: dict[Lang, str]
    definitions: dict[Lang, str]
    source: str
    kind: Kind
    languages: list[Lang]
    requires: list[str]
    deterministic: bool
    prompt_hints: dict[Lang, str]
```

Each procedure additionally declares a Pydantic `Params` model and exposes
`params_schema()` as JSON Schema, so non-Python callers can drive it over HTTP —
consumer shape (3) in the seed's §11.

### Language packs

```python
class LanguagePack(Protocol):
    lang: Lang
    capabilities: frozenset[str]
    def tokenize(self, text: str) -> list[str]: ...
    def syllables(self, word: str) -> list[str]: ...
    def nouns(self) -> Iterable[str]: ...
    def fold_diacritics(self, ch: str) -> str: ...
```

The English pack ships in core and declares `{"tokens", "alphabet",
"fold_diacritics", "letter_shapes"}`. A pack implements every protocol method, but a
method whose capability it does not declare raises `MissingCapability` rather than
returning an approximation. The English pack does not declare `syllables` or
`lexicon.nouns`; calling a procedure that requires them raises `MissingCapability`
naming procedure, pack and capability. `lang="de"` raises `UnknownLanguage` pointing
at `pip install denckring[de]`. No silent fallback anywhere — that single rule is what
makes the package trustworthy across languages.

`letter_shapes` exists because of `prisoners_constraint`: the forbidden set is
ascenders and descenders, which is a property of the orthography's glyph shapes, not
of the language. A German pack must extend it for ß and the umlauts. It is the
concrete proof that packs are an interface rather than a dictionary.

### Scoring

`score` is continuous and monotone in violation count, and `satisfied` is exactly
`score == 1.0` for every procedure in the catalogue. The general form is
`1 - violating_units / total_units` over a unit the procedure documents in `metrics`;
`pangram` inverts it to coverage (`letters_present / alphabet_size`). Binary pass/fail
cannot drive a retry loop — a caller needs to know whether a text missed by one word
or by fifty.

Empty input is defined per procedure and asserted in the golden fixtures: vacuously
satisfied for the restriction procedures, unsatisfied at score 0.0 for `pangram`.

## The twelve procedures

All lexicon-free, all parameterised, all `kind: restrictive`.

| id | constraint | key params |
|---|---|---|
| `lipogram` | omits a given letter | `forbidden="e"` |
| `univocalic` | uses one vowel only | `vowel` |
| `tautogram` | every word starts with the same letter | `initial` |
| `pangram` | contains every letter of the alphabet | `perfect=False` |
| `heterogram` | no letter repeats | `scope="text"\|"word"` |
| `palindrome` | reads identically reversed | `unit="letter"\|"word"` |
| `snowball` | each word one letter longer than the last | `start=1`, `step=1` |
| `reverse_snowball` | each word one letter shorter | `start`, `step` |
| `prisoners_constraint` | no ascenders or descenders | — |
| `beau_present` | uses only the letters of a dedicatee's name | `name` |
| `acrostic` | initials of lines spell a target | `target`, `unit="line"` |
| `telestich` | final letters of lines spell a target | `target`, `unit="line"` |

Each carries a real literary source in its catalogue row (Perec, Oulipo, the
Rhetoriqueurs, and so on) and at least one genuine literary instance as a golden
example.

## Eval harness

**Level 1 — golden examples.** Per procedure, at least one authentic instance that
must return `satisfied=True` and one counterexample that must return `False`. Stored
as YAML in `eval/fixtures/golden/<id>.yaml` and shipped, because these fixtures are
also the documentation: the docs gallery is generated from them, so every procedure
page shows a real input and a real report with no extra maintenance.

**Level 2 — property tests.** Hypothesis strategies in `tests/strategies/<id>.py`
generate conforming and violating texts; the generic suite asserts `check()` agrees
with each. Plus the universal invariants: determinism, `satisfied == (score == 1.0)`,
`0.0 <= score <= 1.0`, `report.procedure == meta.id`, `meta.id` equals the module
name, `requires` is a subset of every declared pack's capabilities, and `check()`
raises nothing but `DenckringError` on arbitrary Unicode input.

The seed's round-trip property `check(apply(text))` is **deferred to Batch 2**, when
`apply()` first becomes implementable. This spec substitutes strategy agreement, which
tests the same relationship from the other direction.

**Level 3 — scoreboard.** `denckring eval --all --json` runs every registered
procedure over every fixture in every declared language, reports pass rate and
coverage, and exits non-zero on regression. This is the CI gate and the acceptance
criterion for unattended agent runs.

## Catalogue

`data/catalogue.yaml` holds roughly 38 rows: the twelve above, plus the Batch 2–4
procedures the seed's §10 names — N+7, S+7, anagram, larding, définitionnelle,
cut-up, fold-in, diastic reading, mesostic, syllable constraints, alexandrine, blank
verse, rhyme scheme, sonnet, haiku, terza rima, and the Denckring itself — each with a
real source, catalogued but unimplemented.

Status per entry: `catalogued` → `implemented` → `validated` (has golden examples).
`denckring status` prints the three counts, so the coverage metric is exercised
against a genuine gap from the first commit rather than a self-congratulatory 12/12.

## CLI

```
denckring check <id> [FILE|-] [--lang en] [--param k=v]... [--json]
denckring apply <id> [FILE|-] [--lang en] [--seed N] [--param k=v]...
denckring list [--lang] [--kind] [--status]
denckring show <id> [--json]         # meta, params schema, golden examples
denckring status [--json]
denckring eval [--all] [--json]
denckring new <id>                   # scaffolds module, test, fixture, catalogue row
```

`check` exits 1 when the text is unsatisfied, so it composes in shell pipelines.
`apply` on a restrictive procedure fails with a message naming the procedure's `kind`.
`new` emits from templates so an agent fills in logic and invents no structure.

## Error handling

| Condition | Raised |
|---|---|
| Unknown procedure id | `UnknownProcedure` |
| Language with no installed pack | `UnknownLanguage`, naming the extra to install |
| Pack lacks a declared capability | `MissingCapability`, naming procedure, pack, capability |
| Bad parameters | `InvalidParams`, wrapping the Pydantic error |

All inherit `DenckringError`. `check()` raises nothing else, on any input.

## Build sequence

A vertical slice first, so the contract is proven before it is copied twelve times:

1. Project scaffold — `uv init`, `src/` layout, hatchling, ruff, mypy strict, pytest,
   `py.typed`, MIT `LICENSE`, seven ADRs.
2. `core/` — protocol, errors, catalogue loader, registry with autodiscovery.
3. `lang/` — pack protocol, capability constants, English pack.
4. `lipogram` end to end — module, catalogue row, golden fixture, strategies.
5. The three generic suites, green on the single procedure.
6. `eval/harness.py` and `cli.py`, with `eval --all` and `status` green on one row.
7. `scaffold/` and `denckring new`, verified by generating the second procedure with it.
8. The remaining ten, each via `denckring new`.
9. Catalogue filled out to ~38 rows; README with a runnable three-line example.

## Acceptance

- `uv run pytest` green, `ruff check` clean, `mypy --strict` clean — output shown.
- `uv run denckring eval --all` green across twelve procedures.
- `uv run denckring status` prints `N catalogued · 12 implemented · 12 validated`,
  where `N` is the exact row count of `data/catalogue.yaml` and every implemented id
  has a catalogue row.
- `denckring new demo` produces a module, test, fixture and catalogue row that fail
  informatively until filled in, rather than passing vacuously.
- A three-line README example runs as written.

## Out of scope

GitHub Actions, the mkdocs gallery, `CITATION.cff`, Trusted Publishing, PyPI upload,
the German and French packs, any procedure implementing `apply()` (the CLI command
exists and always errors, since every Batch 1 procedure is restrictive), and
anything Verlagsspiel-specific. No network calls at runtime or test time.
