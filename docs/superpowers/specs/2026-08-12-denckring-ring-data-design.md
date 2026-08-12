# denckring — the ring data, and the combinatorial devices

**Date:** 2026-08-12
**Status:** approved
**Scope:** sub-project 10

## Purpose

Make the namesake procedure run. Harsdörffer's *Fünffacher Denckring der Teutschen
Sprache* (1651) is what the package is named after, and it has sat in the catalogue as
an unimplemented row filed — wrongly — as something no program could ever judge.

## The misclassification being fixed

Chapter 4 introduced `checkability` and swept the whole permutation family into `none`,
on the argument that they assert every rearrangement reads acceptably, which no program
decides. That argument is sound for some of them and wrong for others.

*Is this word producible by these five rings?* is a segmentation problem. *Is this poem
one of Queneau's 10¹⁴?* is a selection check against the ten sonnets. Both are
decidable, and `denckring`, `cent_mille_milliards` and `wechselsatz` were mis-filed.

`line_permutation`, `stanza_permutation` and `word_permutation` stay `none`. "Is this a
permutation of the source" is decidable, but their definitions claim every ordering
reads as a finished text, and narrowing a definition to fit a convenient checker is the
failure this project exists to avoid.

## What the sources actually say

Three numbers, none agreeing:

| Source | Ring sizes | Product |
|---|---|---|
| Harsdörffer's own text | 48 · 50 · 12 · 120 · 24 | 82,944,000 |
| Florian Cramer's transcription | 49 · 60 · 12 · 120 · 23 | 97,372,800 |
| Repeated throughout the literature | — | 97,209,600 |

The third is arithmetically impossible: 97,209,600 is not divisible by 144, so it cannot
be a product involving rings of 12 and 120. The catalogue row records all three and says
so. Reconciling them quietly would be worse than leaving the discrepancy visible.

## Decisions

| Decision | Rationale |
|---|---|
| The rings ship in core, beside the catalogue | They are not a lexicon; they are the procedure's definition. A Denckring with different rings is a different device |
| Data sourced to Harsdörffer 1651, Cramer credited for the digitisation | A faithful transcription of a public-domain text carries no new copyright; the courtesy of credit is owed regardless |
| One slot mechanism, two shapes | Segmentation for the Denckring, selection for the sonnet machines — the same satisfiability question either way |
| `denckring` gains `apply` | Spinning the rings is what the device does, and it makes the round-trip property apply |
| The permutation rows that stay `none`, stay | Their definitions claim more than a permutation check verifies |

### Why the rings are not a data package

ADR 0013 sends linguistic data to separate distributions, with size and licence as the
stated trigger. Neither applies: the rings are 2 KB of public-domain morphology.

There is also a hard obstacle. Since ADR 0016, two packs claiming one language raise
`DuplicatePack`, and German already registers through the entry-point group from core. A
German data distribution would collide with it. Putting the rings in core is both the
lighter answer and the only one available without reopening pack composition.

## Design

### The device

```python
class Slot(BaseModel):
    name: str
    alternatives: list[str]
    optional: bool = False

class Device(BaseModel):
    id: str
    name: str
    source: str
    slots: list[Slot]
```

`denckring/data/devices/harsdoerffer_1651.yaml` holds Harsdörffer's five rings. The
catalogue row names the file; the procedure loads it by default and accepts another
device by parameter, so the mechanism is not welded to one historical object.

### Two questions over one structure

- **Segmentation** — can the text be cut into pieces, in slot order, each piece an
  alternative on its slot, skippable slots contributing nothing? This is the Denckring:
  the parts concatenate with no separators.
- **Selection** — is each token of the text an alternative on the corresponding slot?
  This is Queneau's ten sonnets and Kuhlmann's Wechselsatz, where the parts are
  separated and the count is fixed.

Both are searches for *some* consistent reading, which is the shape metre, N+7 and the
free monosyllable already take.

### Procedures

- `denckring` — `check` asks whether a word could have come off the rings; `apply` spins
  them from a seed. `kind` becomes `both`.
- `cent_mille_milliards` — source-relative: the source is the ten sonnets, one stanza of
  alternatives per line.
- `wechselsatz` — source-relative: the source is Kuhlmann's template.

### New catalogue rows

Ramon Llull's *Ars Magna* and the rotating figures of the dignities, as the tradition
the Denckring descends from. Kircher and Jean Paul are left out: Kircher until it is
settled which work is meant, Jean Paul until a source can be verified rather than
recalled.

## Acceptance

- `uv run pytest`, `ruff check`, `ruff format --check`, `mypy --strict` green.
- `denckring check denckring <a word off the rings>` is satisfied; a word that cannot be
  segmented is not.
- `apply` produces a word its own `check` accepts, exercised by the round-trip suite.
- `uv run denckring status` shows implemented risen by three and unreachable fallen by
  three.
- The catalogue row records all three combination figures and the impossibility of the
  third.

## Out of scope

Kircher, Jean Paul, `proteus_verse` (its metre is Latin and quantitative), the
permutation rows that keep their `none`, and pack composition. No network at runtime or
test time.
