## What this changes

<!-- One or two sentences. -->

## Checklist

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check` and `uv run ruff format --check` pass
- [ ] `uv run mypy --strict src tests packages/denckring-en-data/src` passes
- [ ] `uv run denckring eval --all` is green

If this adds a procedure:

- [ ] One module, named for the procedure id
- [ ] A catalogue row with a real source, an `attribution` and a `checkability`
- [ ] Golden fixtures: at least one genuine instance and one counterexample
- [ ] Hypothesis strategies under `tests/strategies/`
- [ ] The catalogue definition claims no more than the checker verifies
