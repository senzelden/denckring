# denckring — the catalogue as open data

**Date:** 2026-08-11
**Status:** approved
**Scope:** sub-project 3 of 5 (see the Batch 1 spec for the decomposition)

## Purpose

Grow `data/catalogue.yaml` from 31 rows to roughly 150 and make it publishable as a
CC BY 4.0 dataset in its own right — useful to someone who will never install the
package.

## The constraint that shapes this sub-project

The seed asks for 500+ entries. That number is not achievable at the quality the dataset
claims. Names and definitions of these forms are well established; **attributions are
not**, and there is no machine-readable catalogue of them online — the authoritative
list is the *Oulipo Compendium*, a print book. Writing 500 rows from memory would
produce a dataset whose defining feature, being sourced, is partly fabricated. In a
citable dataset a wrong attribution propagates.

So: roughly 150 rows, every one carrying an attribution that is either confident or
honestly labelled as second-hand. The catalogue grows later; a wrong row is harder to
undo than a missing one.

## Decisions

| Decision | Rationale |
|---|---|
| ~150 rows, not 500 | A clean 150 is worth more to a researcher than a shaky 500 |
| `attribution` records how the source was established | Lets a reader distinguish "Perec invented this in 1969" from "this is catalogued in the Compendium" |
| `family` is a closed vocabulary of eight | An invalid family becomes a validation error, not a silent ninth group |
| `aliases`, not free-form tags | Aliases make the dataset findable; tags duplicate `family` and `requires` and drift without a vocabulary |
| Aliases are unique catalogue-wide and never collide with an id | Otherwise `search` is ambiguous the moment two forms claim `mesostich` |
| Data licence gets its own file | `LICENSE` is MIT and covers code; a sentence in the README is not a licence statement |

## Schema additions

Three fields on `Meta`:

```python
Family = Literal[
    "letter", "word", "syntax", "form",
    "permutation", "procedural", "translation", "visual",
]
Attribution = Literal["primary", "reference", "traditional"]

family: Family
aliases: list[str] = []
attribution: Attribution
```

- `primary` — a named author, work and year the entry stands behind.
- `reference` — attested in a standard reference rather than traced to an origin.
- `traditional` — classical or folk; no single origin exists to name.

`family` and `attribution` are required, so every existing row is backfilled in the same
task that adds the fields.

### Family definitions

Recorded here because the boundaries are the part most likely to drift:

| Family | Operates on | Examples |
|---|---|---|
| `letter` | individual characters | lipogram, pangram, palindrome, acrostic |
| `word` | whole words, usually via a lexicon | N+7, anagram, perverb |
| `syntax` | sentence and clause structure | homosyntaxism, larding |
| `form` | metre, rhyme, stanza | sonnet, haiku, alexandrine |
| `permutation` | reordering a fixed set of parts | quenina, Denckring, Cent mille milliards |
| `procedural` | a process applied to source text | cut-up, mesostic, erasure |
| `translation` | mapping one text onto another | homophonic translation, antonymic translation |
| `visual` | the shape of the text on the page | calligram, pattern poem, word square |

`syntax` and `procedural` are the least crisp pair: the test is whether the procedure
rewrites *structure* (syntax) or applies a *process* to source material (procedural).

## Validation

A test, not a review. Every row must have: a non-empty `source`; `names.en`,
`definitions.en` and `prompt_hints.en`; a `family` in the vocabulary; an `attribution`.
Aliases must be unique across the catalogue and must not collide with any procedure id.
Ids must be unique — already enforced by the loader.

## Discoverability

- `denckring search <term>` — matches ids, names and aliases, case-insensitively.
- `denckring list --family form` — filters by family.

Without these a 150-row catalogue is a file to grep.

## Release artifact

- `denckring catalogue export --format json|csv` writes the dataset as a standalone
  file, with `--output` for the destination and stdout by default.
- `LICENSE-DATA` carries the CC BY 4.0 notice and the attribution requirement.

## Build sequence

1. Schema fields, catalogue validation tests, and backfill of the 31 existing rows.
2. `search` and `list --family`.
3. Expansion, one task per family: letter, word, syntax and form, permutation and
   procedural, translation and visual.
4. Export command, `LICENSE-DATA`, README and changelog.

## Acceptance

- `uv run pytest`, `ruff check`, `ruff format --check`, `mypy --strict src tests` green.
- `uv run denckring status` reports roughly 150 catalogued, 12 implemented, 12 validated.
- `uv run denckring search snowball` finds the entry by its `rhopalic` alias.
- `uv run denckring catalogue export --format json` emits valid JSON for every row.
- Catalogue validation fails if a row is added without a `family` or `attribution`.
- No entry claims a `primary` attribution the author would not stand behind; where the
  origin is uncertain the row says `reference`.

## Out of scope

Implementing any newly catalogued procedure; the French pack; `apply()`; Zenodo and the
DOI; the docs gallery; CI. No network access at runtime or test time.
