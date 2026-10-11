# 60. What the bench may lean on

## Context

`denckring-bench` mints instances from a seed and scores model output with this
library's checkers. To do that it reads four surfaces the README lists as "published, not
yet promised": `golden_cases` and `GoldenCase`, `Description.reading`, and
`pack_provenance` with `PackProvenance`. It also imports one name from inside the
package, `denckring.eval.harness.unmet_requirements`, to say why a golden case cannot
run under a pack, and it reads `core.fields.ROLES` to know what an `x-denckring-role`
value in a parameter schema means. Nothing promised any of these, so at every pin bump
the bench re-checked each by hand, and a rename here would have broken it with no
changelog line obliged to say so.

## Decision

**D1: export the two names that live in `core` and `eval`.** `denckring.unmet_requirements`
is the existing function, re-exported with its signature unchanged:
`(case: GoldenCase, pack: LanguagePack) -> list[str]`. `denckring.PARAMETER_ROLES` is a
read-only mapping (`types.MappingProxyType`) over `core.fields.ROLES`, so a caller can
look a role up but cannot edit the table the hint rules read. Both are in `__all__`.

**D2: promote the four surfaces.** `golden_cases`, `GoldenCase`, `Description.reading`
and `pack_provenance`/`PackProvenance` move from "published, not yet promised" into
the README's promised list, with the two names above. A role may be added to
`PARAMETER_ROLES`; none is removed or renamed without a **Breaking:** changelog entry.
`tests/test_published_surface.py` holds the roles to that: a snapshot of the role names
(`tests/data/published-roles.json`) must stay a subset of what the mapping publishes,
and every role a parameter schema names must be in it. Adding a role needs no change to
the snapshot, as with `tests/data/published-rules.json`.

**D3: rows promise named metrics, and defaults are under the promise.** A row declares
`promised_metrics`, key to meaning, published as `Description.metrics`. The README's
"not stable: `metrics` keys" now excepts them. `chronogram` promises `total` and
`numerals`; the eleven rows whose every golden report carries `letters` promise it,
each with the meaning true for that row (some count after folding, `heterogram` sums
per word, `prisoners_constraint` counts grapheme clusters). A guard fails if any golden
report lacks a promised key as a float, and a snapshot (`tests/data/published-metrics.json`)
fails if a promised key is removed. The same promise now covers each parameter's
`default` in `describe().params`: changing one is **Breaking:**, since it moves verdicts
for callers who left the parameter unset.

The record is extended below by later decisions in this branch.

### D4. Packs carry content digests

`PackProvenance.data` maps distribution to version, and versions move in lockstep with
every release, so a snapshot keyed on them is invalidated by releases that changed no
word. `denckring.pack_provenance(lang)` now also fills `digests`: SHA-256 over canonical
JSON of `graded_words()` and of `sorted(nouns())`, and over the bytes of each data
distribution's files. The canonical forms are documented (README, `pack_digests`) so a
caller can recompute them; the promise is that a digest changes exactly when that
surface's content does. A `Report` carries none: hashing costs milliseconds to a
tenth of a second per language, once per process, which is nothing beside a lexicon load
but not nothing beside a check. `pack_digests` stays in `denckring.core.provenance`,
not in `__all__`.

Costs. `files` also moves when packaging metadata inside the distribution changes
(`METADATA`, licences) though no word did; that is conservative, and stated. An editable
install lists no package data, so its `files` hashes the import package's files instead
and differs from a wheel's for identical data: digests compare within one install kind.
A digest says the content changed, never what changed.

## Consequences

These names can no longer change in a minor release without a **Breaking:** line. That
is the point, and it is a cost: `GoldenCase` is a Pydantic model the corpus is built
from, so a field added to it is part of the promise the day it ships, and a field
removed or retyped is a breaking change even though only the test suite constructed it
before.

`unmet_requirements` stays importable from `denckring.eval.harness`, but that path is
not covered; the promise is on the name in `denckring`.

The role snapshot guards names, not meanings. A role whose description is reworded
passes; a role whose meaning is reversed under the same name does not fail anything. The
README says meaning is promised, and only review holds it.

`Description.reading` was published in 0.3.2 and grew fields in 0.4.0; promoting it fixes
the fields it has, not ones it may still grow.

A promised metric key cannot be renamed for convenience, and the guard checks golden
cases only: a key absent on an input no golden case covers is not caught. The default
promise is held by review and the changelog, not by a snapshot.
