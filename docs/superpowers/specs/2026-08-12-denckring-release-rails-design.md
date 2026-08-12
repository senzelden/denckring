# denckring — release rails

**Date:** 2026-08-12
**Status:** approved
**Scope:** sub-project 8 of 8

## Purpose

Make the project verifiable by someone other than its author, and publishable without
a manual step. The repository has no CI: nothing checks that any of the last six
chapters works on a machine that is not this one, on a Python that is not 3.11, or in
an install that lacks the data package.

## The gallery is the point

The seed's argument was that the fixtures are the documentation. After six chapters
that is literally true: 153 golden cases, each carrying a real source, an input, and a
recorded result that CI already enforces. A generator turns the catalogue and the
fixtures into a page per procedure showing a genuine worked example, and the gallery
therefore cannot drift — a fixture that stopped matching would fail the test suite
before it reached the docs.

Nothing in the gallery is written by hand. That is what keeps 145 entries maintainable.

## Decisions

| Decision | Rationale |
|---|---|
| Generated docs are gitignored and rebuilt every time | A committed generated file is a file that can be stale |
| `mkdocs build --strict` in CI | A broken link or missing page fails the build rather than shipping |
| A dedicated core-only CI job | Nothing currently tests the install without `denckring[en]`, and that is the path most likely to break silently |
| `denckring eval --all` is its own CI gate | It is the acceptance criterion the seed named for unattended runs; a pytest pass is not the same claim |
| Trusted Publishing with OIDC, no API tokens | The seed asked for it, and a token in repository secrets is a standing liability |
| Both distributions publish from one tagged workflow | They must stay version-locked: the data package subclasses the core pack |
| Workflow files are marked unverified until first push | They cannot be executed here, and saying otherwise would be a false claim about what has been tested |

## Design

### Continuous integration

`.github/workflows/ci.yml`, on push and pull request:

- **lint** — `ruff check`, `ruff format --check`
- **typecheck** — `mypy --strict` over both packages
- **test** — matrix of Python 3.11, 3.12, 3.13 across Ubuntu, macOS and Windows
- **eval** — `denckring eval --all` and `denckring status`, as a distinct gate
- **core-only** — install `denckring` alone in a clean environment, assert the German
  and lipogram paths work and that a metre procedure raises `MissingCapability`
- **docs** — regenerate the gallery and `mkdocs build --strict`
- **build** — build both distributions and run `twine check`

### The gallery generator

`scripts/build_gallery.py` reads the catalogue and the golden fixtures and writes
`docs/gallery/`:

- an index grouped by family, with the coverage line at the top
- a page per catalogued procedure: names, definition, source, attribution, family,
  checkability, capabilities required, status, parameter schema where implemented, and
  every golden example with its recorded result

Unimplemented entries get a page too, marked as catalogued, because the catalogue is a
survey of the field and the gaps are part of what it documents.

### Release

`.github/workflows/release.yml`, on tag `v*`: build both distributions, publish with
`pypa/gh-action-pypi-publish` using `id-token: write` and attestations enabled.

### Repository hygiene

`CITATION.cff`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue and pull request templates,
`.github/dependabot.yml` for actions and dependencies, and `.pre-commit-config.yaml`
mirroring the lint and typecheck jobs.

## Acceptance

- The gallery generator runs and produces a page per catalogued procedure.
- `mkdocs build --strict` succeeds locally.
- `pre-commit run --all-files` passes.
- A clean virtual environment with only `denckring` installed checks a lipogram and a
  German pangram, and raises `MissingCapability` for `iambic_pentameter`.
- Both distributions build and pass `twine check`.
- Every workflow file is valid YAML and its steps are internally consistent — with the
  README and the commit message stating plainly that they have not been executed.

## Out of scope

Actually publishing to PyPI, creating the GitHub repository, registering the Zenodo
DOI, and the remaining procedure chapters. No network at runtime or test time; the docs
build is a development task, not a runtime one.
