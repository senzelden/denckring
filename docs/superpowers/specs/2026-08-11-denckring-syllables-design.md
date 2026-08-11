# denckring — syllables, and the first data package

**Date:** 2026-08-11
**Status:** approved
**Scope:** sub-project 6 of 7

## Purpose

Give the library syllable counting, and in doing so establish where linguistic data
lives. Eighteen catalogued rows are blocked on `syllables`; this chapter unblocks the
eight that need nothing but a count, and builds the packaging that the rhyme and
lexicon chapters will reuse.

## The data

CMU Pronouncing Dictionary, 135,166 entries, BSD-2-Clause — permissive, attribution
only, no share-alike, so it is compatible with an MIT core. 3.6 MB raw, 915 KB
compressed.

Its stress digits give exact syllable counts (`HH AY1 K UW0` → two), and the phoneme
string from the last stressed vowel gives rhyme. One source therefore unblocks both
`syllables` and `phonemes`; this chapter takes the first and leaves rhyme to the next.
CMUdict carries no part-of-speech tags, so `lexicon.nouns` and its nine rows stay
blocked.

## Decisions

| Decision | Rationale |
|---|---|
| Two capabilities: `syllables.heuristic` and `syllables.dictionary` | The user's call over the alternative of dictionary-only; the design below gives the weaker one a real consumer rather than a second unused code path |
| Procedures require `syllables.heuristic`, the weaker capability | So a core-only install can still check a haiku, and installing the data improves the same procedure rather than enabling a different one |
| Every syllabic report carries `metrics["estimated_words"]` | The caller always knows how much was guessed; installing the data drives it to zero. This is what keeps the heuristic honest rather than a silent fallback |
| Data ships as a separate `denckring-en-data` distribution | ADR 0010 named "the first lexicon" as the trigger for splitting data out, and this is it |
| The data package registers through the existing entry-point group | The same mechanism the German pack proved |

### Why the two-capability split needs care

A capability that nothing requires is decoration. The resolution is to treat the
capability as a **floor rather than a switch**: procedures declare
`syllables.heuristic`, which every English pack satisfies, and a pack that also
declares `syllables.dictionary` transparently answers the same calls more accurately.
Nothing branches on which pack is installed; the answers simply get better.

That only stays honest because the count of estimated words is reported on every
result. A caller who needs certainty checks that it is zero — and a future procedure
that cannot tolerate estimates may require `syllables.dictionary` outright, at which
point a core-only install correctly raises `MissingCapability`.

## Design

### Pack API

```python
def syllable_count(self, word: str) -> tuple[int, bool]:
    """The word's syllable count, and whether it was looked up or estimated."""
```

`syllables(word) -> list[str]`, already on the protocol, stays as the segmentation
method and continues to raise for packs that cannot segment.

The English core pack implements `syllable_count` by vowel-group heuristic, returning
`exact=False` always, and declares `syllables.heuristic`.

### The heuristic

Count vowel groups, subtract a silent terminal `e`, add back a syllabic `-le`, and
never return less than one. It is a standard approximation and the docstring says so.
Its accuracy against CMUdict is measured by a test rather than asserted in prose, with
a floor the test enforces — if a change makes the heuristic worse, the build fails.

### The data package

```
packages/denckring-en-data/
  pyproject.toml            name = "denckring-en-data"
  src/denckring_en_data/
    __init__.py             EnglishDataPack
    data/cmudict.dict       vendored, with LICENSE-CMUDICT alongside
```

A uv workspace member, installed by `pip install denckring[en]`, registering
`en` through the `denckring.lang` entry-point group at a higher precedence than the
core pack. It subclasses `EnglishPack`, adds `syllables.dictionary`, and overrides
`syllable_count` to consult CMUdict first and fall back to the inherited heuristic —
reporting `exact=False` when it does.

### Procedures

Eight, all needing nothing but a count: `haiku`, `tanka`, `senryu`, `cinquain`,
`syllable_count`, `monosyllabic_prose`, `hendecasyllable`, `alexandrine`.

Metre — `iambic_pentameter`, `dactylic_hexameter`, and the rest — needs stress
patterns, which CMUdict also carries but which are a chapter of their own. Rhyme needs
the phoneme tail. Both are left catalogued.

## Acceptance

- `uv run pytest`, `ruff check`, `ruff format --check`, `mypy --strict` green across
  both packages.
- `uv run denckring status` shows implemented risen by eight.
- With core only: `denckring check haiku` works and reports a non-zero
  `estimated_words`.
- With the data package installed: the same command reports `estimated_words` of zero
  for ordinary English, and `syllables.dictionary` appears in the pack's capabilities.
- The heuristic's measured agreement with CMUdict is asserted by a test.
- `LICENSE-CMUDICT` is present in the data package and its attribution requirement is
  stated.

## Out of scope

Rhyme and metre; `lexicon.nouns` and its nine rows; the French pack; CI and release
rails; publishing either distribution. No network at runtime or test time — the
dictionary is vendored, not downloaded.
