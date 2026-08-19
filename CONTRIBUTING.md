# Contributing to denckring

## Two hard rules

1. **One module per procedure.** The module name must equal the procedure id. This is
   enforced at registration, and it is what lets several people — or several agents —
   add procedures at once without ever touching the same file.
2. **`check` is mandatory.** A procedure without a working checker has no acceptance
   criterion, so it is not registered. `apply` is optional and only meaningful when
   `kind` is `constructive` or `both`.

## Adding a procedure

```console
uv run python scripts/new_procedure.py <id>
```

That writes five files from templates — module, test, Hypothesis strategy, golden
fixture and catalogue row — each marked `FILL IN`. Fill them in; invent no structure.

- **Catalogue row** (`src/denckring/data/catalogue.yaml`) — names, definitions, a real
  source with a date, `kind`, `languages`, `requires`, and an English prompt hint. The
  catalogue is the single source of truth for metadata; the module loads it.
- **Module** — a Pydantic `Params` model and `_check`. Language, capability and
  parameter validation already happened in `BaseProcedure.check`; do not repeat them.
  Build the `Report` with `self._report(...)` unless an empty text should be
  *unsatisfied* for your procedure, as it is for `pangram`.
- **Golden fixture** — at least one authentic literary instance that must be satisfied
  and one counterexample that must not. Record the real source. These fixtures are also
  the documentation, so they are worth getting right.
- **Strategies** — `satisfying()` and `violating()`, each yielding `(text, params)`
  pairs. They are the generator half of the procedure and are what closes the loop for
  restrictive procedures that have no `apply`.

Then:

```console
uv run pytest && uv run ruff check && uv run mypy --strict src tests
uv run denckring eval --all
```

The three registry-wide suites — `test_golden.py`, `test_strategies.py` and
`test_invariants.py` — pick your procedure up automatically. You should not need to
edit them.

## Invariants your procedure must hold

- `satisfied == (score == 1.0)`, always.
- `score` is in `[0, 1]` and monotone in violation count.
- `check` is deterministic, and raises nothing but a `DenckringError` subclass on any
  input, including arbitrary Unicode.
- Every capability the procedure uses appears in its catalogue `requires`.

## Before you open a pull request

```console
uv run --with pre-commit pre-commit install
```

That mirrors the lint and typecheck jobs in CI, so a failure locally is a failure there.
The rest of CI — the test matrix, the eval gate, the core-only install and the docs
build — runs on the pull request.

The **core-only** job is worth knowing about: it installs `denckring` without the data
package and asserts that a procedure needing a pronouncing dictionary raises rather than
guessing. If you add a procedure that quietly depends on a capability the core pack does
not have, that job is what catches it.

## Licensing

Code contributions are Apache-2.0, and a contribution is taken as licensed that way
(the licence's own section 5). Catalogue rows are CC BY 4.0 and need a real source. Do not
add lexicons or hyphenation data to core: Wiktionary-derived data is CC BY-SA and pyphen
is copyleft, so both must live behind an extra. Record any new data source in an ADR
under `docs/adr/` before the data lands.
