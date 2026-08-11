# denckring — checkability, and the procedures that need no data

**Date:** 2026-08-11
**Status:** approved
**Scope:** sub-projects 4 and 5 of 6 (the decomposition has grown by one; see below)

## Purpose

Two chapters that share a schema change and ship as two merges:

- **Chapter 4** — model whether a procedure can be checked at all, fix the coverage
  metric accordingly, and implement the ~23 catalogued procedures that are decidable
  from the text alone.
- **Chapter 5** — give the protocol a shape for procedures decidable only against their
  source text, and implement the ~15 of those.

Together these take `implemented` from 12 to roughly 50 without touching the
data-licensing question.

## The finding that prompted this

85 catalogued rows need no capability the English pack lacks. But `requires` names
*capabilities*, not whether a check is possible at all, and those 85 fall into three
groups that behave completely differently:

- decidable from the text alone;
- decidable only against the source text the work was made from — a shape `check(text)`
  has no room for;
- **not decidable at all.** `canada_dry` is *defined* as having the manner of a
  constrained work with no constraint operating. `found_poem`, `chance_operation`,
  `calligram` and `concrete_poetry` have no computable acceptance criterion.

The third group means the coverage metric currently misleads. `145 catalogued · 12
implemented` reads as a gap that will one day close; roughly 25 of those rows can never
have a checker, and ADR 0002 says a procedure without one is never registered. A metric
that promises an unreachable target is worse than no metric.

## Decisions

| Decision | Rationale |
|---|---|
| `checkability: self \| source \| none`, required on every row | Distinguishes "not yet" from "never", which `requires` cannot express |
| Coverage is measured against the implementable subset | Otherwise the project metric describes a gap that cannot close |
| A registered procedure may not declare `checkability: none` | If a checker exists the row was mis-filed; the invariant catches it |
| `source` rides on a `SourceParams` base model | Same pattern as `DiacriticParams`: it reaches `params_schema()` and the CLI for free, and `check()` keeps its signature |
| CLI gains `--source FILE` | `--param source=<a whole novel>` is not usable |
| `sestina`, `quenina` and `pantoum` ship in the self-checkable batch | Their defining rule is end-word permutation, which needs no prosody |

## Chapter 4: checkability and the self-checkable batch

### Schema

```python
Checkability = Literal["self", "source", "none"]

checkability: Checkability
```

- `self` — decidable from the text and its parameters alone.
- `source` — decidable only against the source text, supplied as a parameter.
- `none` — no computable acceptance criterion exists. The row is catalogued because
  the form belongs in an honest survey of the field, not because it is a backlog item.

### The metric

`Coverage` gains `implementable` and `unreachable`:

```
145 catalogued · 120 implementable · 12 implemented · 12 validated · 25 not mechanically checkable
```

`implementable` counts rows whose `checkability` is not `none`. `unreachable` counts the
rest. `implemented` and `validated` keep their present meanings.

### Procedures

Twenty-three, all lexicon-free and decidable from the text alone: `abecedarian`,
`alphabetical_sentence`, `bivocalic`, `monoconsonantal`, `consonantal_lipogram`,
`pangrammatic_lipogram`, `supervocalic`, `homoteleuton`, `double_acrostic`, `chronogram`,
`liponym`, `snowball_sentence`, `sentence_length_constraint`, `anaphora`, `epistrophe`,
`single_sentence`, `letter_bank`, `tautonym`, `boustrophedon`, `sator_square`, `sestina`,
`pantoum`, `quenina`.

`sestina`, `quenina` and `pantoum` check **end-word permutation only**, not metre or
rhyme. Their catalogue definitions say so explicitly, so the row does not overclaim what
its checker verifies.

## Chapter 5: source-relative procedures

### Shape

```python
class SourceParams(BaseModel):
    source: str = Field(description="The text this one was made from.")
```

`check()` is unchanged. The CLI gains `--source FILE`, which reads the file into the
`source` parameter before dispatch.

### Procedures

Fifteen: `anagram`, `antigram`, `transposal`, `cut_up`, `every_nth_word`, `diastic`,
`mesostic`, `slenderizing`, `melting_text`, `larding`, `haikuization`, `column_reading`,
`recombination`, `lipogrammatic_translation`, `univocalic_translation`.

### The round-trip property, at last

`cut_up` and `every_nth_word` admit genuine `apply()` implementations: generating them
needs the source text and nothing else. That makes the seed's central property —
`check(apply(text))` is satisfied — testable for the first time, having been deferred in
the Batch 1 spec for want of any constructive procedure. A new registry-wide suite
exercises it for every procedure that defines `apply`.

## What this leaves

The remaining data-dependent rows are now a well-defined set rather than an amorphous
backlog: 9 on `lexicon.nouns`, 18 on `syllables`, 20 on `phonemes`. The data-licensing
ADR still gates them. Neither chapter here touches it.

## Acceptance

- `uv run pytest`, `ruff check`, `ruff format --check`, `mypy --strict src tests` green.
- `uv run denckring status` reports catalogued, implementable, implemented, validated and
  unreachable counts, with implementable strictly less than catalogued.
- Catalogue validation fails if a row omits `checkability`.
- The invariant suite fails if a registered procedure declares `checkability: none`.
- `uv run denckring eval --all` green across roughly 50 procedures.
- `uv run denckring check anagram --source original.txt candidate.txt` works.
- The round-trip suite runs for every procedure defining `apply`, and is non-empty.

## Out of scope

Any lexicon, syllabification or phoneme data; the French pack; CI and release rails; the
docs gallery. No network at runtime or test time.
