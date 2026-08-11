# 9. Diacritic folding is a parameter, not a policy

## Context

Whether `ä` counts as `a` has no single right answer. A German lipogrammatist writing
without "a" must decide whether *Mädchen* is permitted, and Perec's translators faced
exactly that question; the French edition had already settled that `é`, `è` and `ê`
count as `e`. The same question reaches English through borrowings like *café*.

Meanwhile two kinds of procedure must never fold. `snowball` counts the letters of a
word as written. `prisoners_constraint` asks whether a glyph rises above the x-height,
and folding is precisely what destroys the information it needs.

## Decision

`fold_diacritics` is a per-call parameter defaulting to true, carried on a shared
`DiacriticParams` base model and inherited by the nine procedures that compare letters.
`letter_spans` takes a matching `fold` argument. Procedures that count word length or
read glyph shapes do not inherit the model, so the parameter cannot be passed to them at
all.

## Consequences

The choice reaches `params_schema()` and therefore the JSON data contract, and works as
`--param fold_diacritics=false` from the command line, without any further plumbing.
Every letter-comparing procedure now has two code paths, and both need fixtures.

The exclusion is enforced by type rather than by convention: `prisoners_constraint` has
no `fold_diacritics` field, so no caller can ask it to fold, and a future procedure that
inherits the wrong base will be caught by the parameter appearing where it should not.
