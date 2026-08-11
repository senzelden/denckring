# 11. Checkability is a property of the procedure, not of its capabilities

## Context

`requires` records what a procedure needs from a language pack. It says nothing
about whether the procedure can be checked at all, and the difference turned out to
matter: sorting the catalogue by what the English pack already supplies produced 85
rows, of which roughly a quarter can never have a checker.

`canada_dry` is *defined* as having the manner of a constrained work with no
constraint operating. `found_poem`, `chance_operation` and `calligram` have no
computable acceptance criterion at all. A third group — `anagram`, `cut_up`,
`every_nth_word` — is perfectly decidable, but only against the source text the work
was made from, which `check(text)` had no room for.

Left alone, the coverage metric promised a gap that could never close.

## Decision

Every catalogue row declares `checkability`: `self` when decidable from the text and
its parameters, `source` when it needs the text it was made from, `none` when no
computable acceptance criterion exists. Coverage is measured against the rows that
are not `none`, and `denckring status` reports the unreachable count separately.

Source-relative procedures carry the source on a `SourceParams` base model, so
`check` keeps its one-text signature and the requirement appears in
`params_schema()` for callers that never touch Python.

An invariant fails the build if a registered procedure declares `checkability:
none` — if a checker exists, the row was mis-filed.

## Consequences

The project metric describes reachable work. A `none` row becomes an honest
statement about a form rather than a backlog item, so the catalogue can survey the
field without pretending every entry is pending implementation.

The invariant only catches one direction of error: a row wrongly filed `none`
quietly shrinks the denominator and nothing complains. That list is about two dozen
rows and should be read directly rather than trusted.

Classifying the catalogue this way immediately caught four rows whose `requires` had
been wrong — `boustrophedon` is source-relative, and `semordnilap`, `kangaroo_word`,
`word_square` and `charade` cannot be decided without knowing what counts as a word.
