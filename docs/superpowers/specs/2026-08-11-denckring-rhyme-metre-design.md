# denckring — rhyme and metre

**Date:** 2026-08-11
**Status:** approved
**Scope:** sub-project 7 of 8

## Purpose

Unblock the twenty catalogued rows that need pronunciation beyond a syllable count. The
data is already vendored in `denckring-en-data`; what is missing is a rhyme key, a
stress pattern, and a formulation of metre that does not lie.

## The problem metre poses

CMUdict records lexical stress, not metrical stress. On "Shall I compare thee to a
summer's day" it marks *to* as stressed and *shall* as stressed, because those are the
citation forms. A checker that compared dictionary stress against an iambic pattern
would reject Shakespeare's most famous line.

The distinction that resolves it: **polysyllabic words have fixed internal stress;
monosyllables do not.** *Compare* is 01 wherever it appears, *summer's* is 10. A
monosyllable takes whatever stress the line gives it.

## Decisions

| Decision | Rationale |
|---|---|
| Metre is a satisfiability question, not a comparison | Asking whether *some* assignment fits makes the check exact rather than approximate, and it validates real verse |
| Polysyllabic stress is fixed; monosyllabic stress is free | This is the actual linguistic fact, and it is what makes the satisfiability formulation sound |
| Secondary stress counts as free | CMUdict's `2` is genuinely either, and forcing it would reintroduce false negatives |
| Rhyme runs from the last primary-stressed vowel | The standard definition of perfect rhyme |
| A word does not rhyme with itself by default | English practice; `allow_identical` exists because French *rime riche* wants the opposite |
| `phonemes` and `stress` are dictionary-only | There is no honest spelling heuristic for either, unlike syllables — so no floor capability, and core-only installs correctly cannot check a sonnet |
| Quantitative classical metres stay catalogued | They measure syllable length, not stress; English only imitates them |

## Design

### Pack API

```python
def rhyme_key(self, word: str) -> str:
    """Phonemes from the last primary-stressed vowel to the end."""

def stress_pattern(self, word: str) -> str:
    """One character per syllable: '0', '1', or '?' where either will do."""
```

Both raise `MissingCapability` on a pack without the dictionary. `stress_pattern`
returns `?` for every syllable of a monosyllable and for any syllable CMUdict marks
with secondary stress.

### Metre checking

A line satisfies a pattern when its concatenated stress string, with `?` free, can be
matched against the pattern character by character. Because each `?` is independent,
this is a linear scan rather than a search: a mismatch is only a violation where the
word's stress is fixed.

The violation names the word, not the syllable index, because that is what a writer can
act on.

### Rhyme checking

`rhyme_scheme` takes a pattern such as `ABAB`. Lines sharing a letter must share a
rhyme key; lines with different letters must not. Both directions are checked — a poem
where every line rhymes does not satisfy `ABAB`.

Words absent from the dictionary raise `MissingCapability` naming the word, since
guessing a rhyme is exactly the silent wrongness ADR 0004 forbids.

### Procedures

Twelve: `rhyme_scheme`, `iambic_pentameter`, `trochaic_tetrameter`, `blank_verse`,
`heroic_couplet`, `terza_rima`, `villanelle`, `triolet`, `limerick`,
`shakespearean_sonnet`, `petrarchan_sonnet`, `rhyme_royal`.

The composite forms delegate: a Shakespearean sonnet is `rhyme_scheme` at
`ABABCDCDEFEFGG` plus `iambic_pentameter`, and says so rather than reimplementing
either.

## Acceptance

- `uv run pytest`, `ruff check`, `ruff format --check`, `mypy --strict` green.
- Shakespeare's Sonnet 18 opening satisfies `iambic_pentameter` and its rhyme scheme.
- A core-only pack raises `MissingCapability` naming `denckring[en]` for any of the
  twelve.
- `uv run denckring status` shows implemented risen by twelve.

## Out of scope

`lexicon.nouns` and its nine rows; the quantitative classical metres; the French pack;
CI and release rails. No network at runtime or test time.
