# denckring — the lexicon

**Date:** 2026-08-12
**Status:** approved
**Scope:** sub-project 9

## Purpose

Unblock the procedures that need to know what a word is, and correct a capability name
that turned out to be doing five jobs.

## Two problems this chapter found

### `lexicon.nouns` was five capabilities wearing one name

Thirteen catalogued rows declared it. They want quite different things:

| What they need | Rows |
|---|---|
| Word membership — is this a word? | `charade`, `semordnilap`, `word_square` |
| An ordered noun list | `n_plus_7`, `s_plus_7` |
| Synonyms | `kangaroo_word`, `synonymic_substitution`, `chimera` |
| Antonyms | `antonymic_substitution`, `antonymic_translation` |
| Glosses | `definitional_literature`, `definitional_expansion`, `definitional_translation` |

A row declaring `lexicon.nouns` when it means "give me a thesaurus" is the same class of
error as a definition promising more than its checker verifies.

### Two data packages cannot both serve one language

Entry-point discovery is keyed by language name and skips a name already present, so a
second package registering `en` would be silently ignored. That is a silent failure of
the kind ADR 0004 exists to prevent, and it is a bug in what has already shipped.

## Decisions

| Decision | Rationale |
|---|---|
| Duplicate registration for a language raises, naming both packs | Silently taking one is the failure mode the project forbids everywhere else |
| Split into `lexicon.words` and `lexicon.nouns` only | Naming a synonym or gloss capability before an honest checker exists repeats the mistake being fixed |
| WordNet goes into the existing `denckring-en-data` | Because of the collision above; the two licences get separate files |
| N+7 reports `ambiguous_words` | A word list cannot tell you *run* is a verb here; the count is what keeps the check honest, as `estimated_words` does for syllables |
| The other eight rows stay catalogued, with corrected `requires` | Their capabilities do not exist yet, and saying so is more useful than a name that misdescribes them |

## Design

### Capabilities

- `lexicon.words` — membership. Backed by the union of the noun list and the
  pronouncing dictionary's headwords, which between them cover ordinary English.
- `lexicon.nouns` — the ordered noun list, which is what N+7 walks.

Pack API:

```python
def is_word(self, word: str) -> bool: ...
def nouns(self) -> Sequence[str]: ...        # already on the protocol, now ordered
def noun_index(self, word: str) -> int | None: ...
```

`nouns()` returns a sequence rather than an iterable, because N+7 needs to index into it.

### Data

WordNet 3.1's `index.noun`, reduced to its 57,616 single-word lemmas in alphabetical
order — 544 KB plain, 192 KB compressed. Multi-word lemmas are dropped: N+7 walks a
dictionary of words, and *antonine_wall* is not an entry a writer would count past.

Princeton's WordNet licence is permissive and attribution-only, with no share-alike, so
it sits alongside CMUdict's BSD-2-Clause without affecting the permissive core. Each
gets its own licence file.

### N+7 and ambiguity

Given a source and a candidate of equal word count, each position is one of:

- **unchanged** — consistent if the source word is not a noun, *or* if it is a noun that
  could be another part of speech here. The second case is counted as ambiguous.
- **changed** — consistent if the source word is a noun and the candidate is the word
  `n` positions later in the noun list.

`satisfied` requires every position consistent. `metrics["ambiguous_words"]` reports how
many rested on the second reading, so a caller who needs certainty can check it is zero.

`s_plus_7` is N+7 with a configurable offset, delegating to the same walk.

### The remaining eight

Their `requires` becomes `lexicon.synonyms`, `lexicon.antonyms` or `lexicon.glosses` —
names with no pack behind them, which is the honest state. They stay catalogued.

## Acceptance

- `uv run pytest`, `ruff check`, `ruff format --check`, `mypy --strict` green.
- Two packs claiming one language raises, and a test proves it.
- `uv run denckring status` shows implemented risen by five.
- A core-only install raises `MissingCapability` for `n_plus_7`.
- An N+7 built by walking the list validates, and reports its ambiguous count.

## Out of scope

Synonyms, antonyms and glosses; pack composition, so that several data packages can
serve one language; the French pack. No network at runtime or test time.
