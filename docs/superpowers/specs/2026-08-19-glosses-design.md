# Dictionary Glosses — Design

**Status:** approved, awaiting implementation plan
**Date:** 2026-08-19
**Branch point:** `3739ca1` (152 catalogued · 126 implementable · 114 implemented · 114 validated)
**Amends:** ADR 0015, which named `lexicon.synonyms`, `lexicon.antonyms` and
`lexicon.glosses` with no pack behind them "until a procedure can answer them without
guessing". This builds one of the three and records why the other two should not be
built at all.

## Goal

Give the English data pack dictionary definitions, and correct the four catalogue rows
whose stated needs turn out to be wrong.

This began as a thesaurus — three capabilities, eight rows. Measuring what the data can
actually do dissolved most of it. What survives is one capability, two rows it genuinely
unblocks, one row that needed nothing all along, and four corrections. That reduction is
the main result, not a setback.

## What the measurements changed

Every figure below is measured against Open English WordNet 2024.

**`lexicon.synonyms` should not be built.** No row honestly needs it:

- **`kangaroo_word`** — *a word containing the letters of a synonym of itself*. WordNet
  synonymy is synset co-membership, which is far stricter than the form's tradition. Of
  eight canonical kangaroo words only three validate: `chocolate`/`cocoa`,
  `illuminated`/`lit` and `rapscallion`/`rascal` pass, while `encourage`/`urge`,
  `masculine`/`male`, `container`/`can`, `chicken`/`hen` and `instructor`/`tutor` fail.
  Meanwhile the 6,197 matches it *does* find are dominated by orthographic variants —
  `aalborg`/`alborg`, `abcs`/`abc`, `abridgement`/`abridgment`. A checker that rejects
  the form's best-known example while accepting spelling variants is worse than none.
- **`chimera`** — *nouns, verbs and adjectives stripped out and replaced by those of
  three different source texts*. This needs part-of-speech identification, not synonyms.
  Its `lexicon.synonyms` declaration is simply wrong.
- **`synonymic_substitution`** — *every substantive word replaced by a synonym*. Of
  twelve natural substitutions a writer would make, only five are synset co-members
  (`bird`/`fowl`, `big`/`large`, `small`/`little`, `begin`/`start`, `happy`/`glad`);
  `quiet`/`silent`, `river`/`stream`, `cold`/`chilly`, `garden`/`yard`, `evening`/`dusk`,
  `house`/`dwelling` and `road`/`street` are all rejected. Worse, only 4 of 11 content
  words in plain prose have any synonym at all, so the row is unsatisfiable regardless.

**`lexicon.antonyms` should not be built either**, for the same shape of reason. Only
6,633 lemmas have an antonym; plain prose yields 2 content words in 11. *Every
substantive word replaced by its opposite* cannot be satisfied by ordinary text.

**`lexicon.glosses` is worth building.** 78,866 lemmas carry 134,298 definitions, and the
gaps in ordinary prose are function words and inflected forms rather than vocabulary
holes.

## Scope

### In

- `LanguagePack.glosses(word)`, gated on `lexicon.glosses`.
- A committed, reproducible build script for `denckring-en-data`, which has none.
- Migration of the English lexicon to Open English WordNet 2024, including the vendored
  noun list.
- `definitional_expansion` and `definitional_literature`.
- `kangaroo_word`, which needs no new capability.
- Four catalogue corrections.

### Out

- `lexicon.synonyms` and `lexicon.antonyms`, per the measurements above.
- `chimera`, now correctly blocked on `pos` alongside `homosyntaxism` and
  `verbless_prose`.
- `definitional_translation`, which needs glosses **in the target language**; English
  ones do not serve it, and no shipped pack has non-English glosses.
- Generators. All three new rows ship `check` only; `kind` deferrals are recorded in
  docstrings per ADR 0002.

## The capability

```python
def glosses(self, word: str) -> Sequence[str]: ...
```

`BasePack` raises `MissingCapability`, exactly as `is_word` and `nouns` do, so core stays
free of data.

**Every sense, not the first.** A writer who replaces *bank* with the riverbank
definition is performing the procedure correctly, so a checker accepting only the first
sense would reject correct work. This is the same satisfiability reading `rhyme_keys` and
`stress_patterns` already take. It costs 1.03 MB over first-sense-only.

**Resolution, and what happens when it fails.** The pack's existing `_lemma` only
lowercases and strips non-letters, so `glosses("birds")` would miss. Resolution therefore
tries, in order: the word as given, `_lemma`, then a documented plain-inflection fallback
(trailing `s`, `es`, `ed`, `ing`). Irregulars — *went* for *go* — remain out of reach.

A word that resolves to nothing returns an empty sequence. It is **never guessed at**,
and the rows that consume it count it and disclose it in an `estimated_words` metric,
the contract the syllable, stress and rhyme paths already share. In the sampled prose 7
of 11 words are substantive and 2 of those need the fallback; without disclosure a report
would silently be drawn from partial knowledge.

## What ships

| File | Size (gzipped) | Contents |
|---|---|---|
| `glosses.txt.gz` | 2.91 MB | 134,298 glosses across 78,866 lemmas |
| `nouns.txt` | 0.51 MB | regenerated from OEWN 2024 |
| `cmudict.dict` | 3.5 MB | unchanged |

The distribution grows from roughly **4 MB to roughly 6.9 MB**. Restricting glosses to
nouns, verbs and adjectives saves 0.06 MB and is not worth the lost coverage.

Extracts are **vendored, not downloaded**: ADR 0013's rule that neither installation nor
use touches the network is unchanged. The network is touched only by a deliberate
rebuild.

## The build script

`packages/denckring-en-data/scripts/build_lexicon.py`, mirroring the German pack's, whose
docstring already states the principle this corrects:

> Committed so the data files are reproducible and diffable. CMUdict in the English
> package is not, and a second opaque blob is not worth adding.

`nouns.txt` **is** that second opaque blob — extracted by hand from Princeton WordNet
3.1's `index.noun` and committed with no script. That is why nobody could tell the
package advertises a `syllables` capability it never implements, which is the trap that
produced this branch's worst defect.

The script reads OEWN 2024 through the `wn` package, added as a **build-only dependency**
in a PEP 735 group: never imported at runtime, never installed by
`pip install denckring[en]`. It writes the extracts plus a metadata file recording the
OEWN version and extraction date, as the German script does.

## The migration, and its blast radius

`nouns.txt` is regenerated from OEWN 2024. Case-folded, the new list agrees with the
vendored Princeton one on **55,221 of 55,239** entries, **adds 1,247** and **drops 18** —
mostly typo corrections such as *fuschia* → *fuchsia*.

**This changes `n_plus_7` and `s_plus_7` output**, because both walk the *ordered* list
and any insertion shifts every later displacement. Their golden fixtures change, and the
change is deliberate: each is regenerated from the new list and verified, never adjusted
until it passes. The CHANGELOG records it as a behaviour change, in the style used for
`prisoners_constraint`'s folding correction.

## Licensing

`LICENSE-WORDNET` carries the Princeton WordNet 3.1 licence and states that it covers
`nouns.txt`. After the migration no Princeton data remains, so it is replaced by Open
English WordNet's CC BY 4.0 licence and attribution. `LICENSE-CMUDICT` is untouched.

The package README's Data section names only CMUdict although the package has shipped
WordNet-derived nouns since it was created; that is corrected here.

## The four catalogue corrections

| Row | Change |
|---|---|
| `kangaroo_word` | `requires` → `[tokens, fold_diacritics, lexicon.words]`. It needed no thesaurus. |
| `chimera` | `requires` → `[tokens, pos]`, joining the `pos`-blocked group, with a `notes` explaining that it substitutes by part of speech rather than by meaning. |
| `synonymic_substitution` | keeps `lexicon.synonyms`, gains a `notes` recording the coverage measurement — blocked for a stated reason rather than an unbuilt one, as the antonym rows are. |
| `definitional_translation` | `requires` → `[tokens, lexicon.glosses.bilingual]`, naming what it actually needs, alongside `homophonic_translation`'s `phonemes.bilingual`. |

## The three rows

**`kangaroo_word`** takes the claimed synonym as a parameter. `check` verifies that the
synonym is a real word via `lexicon.words`, and that its letters appear in the host word
in order. **Whether it is genuinely a synonym is the writer's claim**, and the docstring
says so plainly — the same treatment `univocalic_translation` gives its undecidable
translation half. This is what lets the row accept `encourage`/`urge`, which no
WordNet-driven version could.

**`definitional_expansion`** — each substantive word replaced *once* by its definition.
`check` takes the source and verifies that for each source word resolving to a gloss, one
of that word's glosses appears in the result. Unresolved words are counted, not failed.

**`definitional_literature`** — the same, repeated. `check` accepts a text reachable from
the source by one *or more* iterations, with an `iterations` metric reporting how many it
found. It shares `definitional_expansion`'s comparison, extracted once the second row
needs it rather than designed ahead.

## Testing

- **The capability is gated**: a pack without `lexicon.glosses` raises from `glosses`.
- **Every sense is returned**: *bank* yields more than one definition, and the rows accept
  any of them.
- **Resolution is honest**: `birds` resolves through the inflection fallback; `went` does
  not, returns empty, and is counted in `estimated_words` rather than failing.
- **`kangaroo_word` accepts `encourage`/`urge`** — the case that motivated the parameter —
  and rejects a synonym whose letters are out of order, naming it in the violation.
- **The migration is asserted, not absorbed**: N+7's and S+7's changed fixtures are
  derived from the new list, and a test pins that the shipped `nouns.txt` matches what the
  build script produces, so a hand-edit is caught.
- **`test_declared_capabilities_are_sufficient` covers `lexicon.glosses`**, so the new
  rows' fixtures must genuinely reach it — the guard that caught `limerick` applies from
  the start.

## Risks

**The migration is the risky half, not the glosses.** Adding a method breaks nothing;
regenerating a list a shipped procedure walks in order changes published behaviour.

**Gloss text is third-party prose.** It carries punctuation, parentheses and semicolons,
and will be compared against writer-supplied text. The extract stores it verbatim; the
comparison must decide how strictly to match, and a too-strict match makes the
definitional rows unsatisfiable in the way synonyms already proved possible. This is the
first thing the implementation should test with real text, not the last.

**OEWN 2024 will age.** Pinning the version in the metadata file makes the next migration
a diff rather than the archaeology this one required.
