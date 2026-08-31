# denckring — French

**Date:** 2026-08-31
**Status:** designed, not started
**Scope:** the prosodic and lexical capabilities `FrenchPack` has never had, the distribution that supplies them, and the line-level syllable seam French needs and the other two languages do not
**Branch point:** `eff4a06` (155 catalogued · 130 implementable · 121 implemented · 121 validated · 25 not mechanically checkable)

This is **chapter 6**. Like chapter 4 it answers the project's own coverage metric rather
than an external report, and it is the last language in `Lang` to be answered.

## Purpose

| pack | rows that run | of 121 |
|---|---|---|
| `en` | 121 | 100% |
| `de` | 121 | 100% |
| `fr` | **70** | 58% |

French ships in core with `tokens`, `alphabet`, `fold_diacritics` and `letter_shapes` and
no data at all (ADR 0029). Seventy rows run on that; fifty-one do not. They divide
cleanly, with **no overlap**:

| blocked on | rows |
|---|---|
| syllables and/or phonemes, no stress | **23** |
| a lexicon only | **10** |
| `stress` | **18** |

The 23: `alexandrine`, `arca_musarithmica`, `assonance_constraint`, `cinquain`,
`clerihew`, `englyn`, `ghazal`, `haibun`, `haiku`, `hemeling`, `hendecasyllable`,
`limerick`, `monosyllabic_prose`, `renga`, `rhyme_scheme`, `rondeau`, `senryu`,
`spoonerism`, `syllable_count`, `tanka`, `terza_rima`, `triolet`, `villanelle`.

The 10: `charade`, `definitional_expansion`, `definitional_literature`, `kangaroo_word`,
`n_plus_7`, `s_plus_7`, `semordnilap`, `tmesis`, `word_ladder`, `word_square`.

**The target is 103, not 121, and that is the honest ceiling** — see D2.

## The measurements that chose the source

Taken before the design, because ADR 0018's provenance rules mean a data source is
recorded rather than assumed, and because chapter 4 established the order: measure, then
the ADR, then the plan.

**Wikidata Lexemes cannot carry French.** It is the obvious candidate — ADR 0023 settled
that source and its CC0 licence for German, so the build script, the licence file and the
quarantine argument would all have been reused. Queried on 2026-08-31:

| | French (Q150) | German (Q188) |
|---|---|---|
| lexemes | **31,474** | 241,979 |
| noun lexemes | **12,768** | 188,948 |

French is 13% of German's lexeme count and **6.8% of its nouns**. German's shipped noun
list is 184,040 entries; the French equivalent would be roughly 12,768. `n_plus_7`
indexes positionally into that list and `lexicon.words` answers membership from it, so at
that depth both would be wrong about ordinary French. The cheap answer was tried first
and it failed — the same finding chapter 4 recorded for German IPA at 0.5%.

**Lexique 3.82 can.** Downloaded and measured on 2026-08-31:

| | |
|---|---|
| rows | 142,694 |
| distinct orthographic forms | 125,653 |
| lemmas | 46,947 |
| distinct noun forms (`cgram=NOM`) | **48,234** |
| rows with a phonemic form and a syllable count | **100%** |
| licence | **CC BY-SA 4.0** (stated in the shipped README) |
| archive | 26 MB zip, one TSV of 35 columns |

48,234 noun forms is **3.8× Wikidata's French nouns**, and curated rather than
crowd-sourced. It is a genuine inflectional lexicon, not a lemma list: *aimer* is present
in 36 forms.

Four columns carry the chapter:

| column | example | supplies |
|---|---|---|
| `phon` | `maison` → `mEz§` | `phonemes`, after a SAMPA→IPA table |
| `syll` | `mE-z§` | phonemic syllabation |
| `orthosyll` | `car-ros-se`, `ex-traor-di-nai-re` | **`syllables`** |
| `cgram`, `freqfilms2`, `freqlivres` | `NOM`, 570.30, 461.55 | `lexicon.nouns`, `lexicon.graded_words` |

**One thing Lexique cannot do**, and it is load-bearing for D3: it does not distinguish
aspirated *h* from mute *h*. `haricot` → `aRiko` and `hôtel` → `otEl` both simply drop
the letter. This is why plint carries a separate `haspirater`, and it is why French
Wiktionary earns a place here for more than glosses.

## Prior art

**plint** (plint.a3nm.net, gitlab.com/a3nm/plint) is the direct precedent: a French
poetry validator built on `frhyme`, itself built on Lexique, plus `haspirater`. Its
independent convergence on Lexique is corroboration for the choice above.

**It is GPLv3, and this project is Apache-2.0, so no code may come from it.** Its
*documented rules* are facts about French prosody and are free to learn from; its
implementation is not. Nothing in this chapter is to be derived from reading its source.

Its stated limits are the honest ceiling for anyone: syllable count is "a liberal
estimate which may allow some invalid diérèses and synérèses", hemistich placement at a
sensible grammatical position is unchecked, and rhymes between words derived from one
another are unchecked for lack of data. `phonemizer`/espeak and `prosodic` exist but are
TTS- and English/Finnish-oriented; a vendored table beats a runtime G2P dependency.

## Decisions

**D1. One distribution, two sources, one licence.** `denckring-fr-data` vendors Lexique
for prosody, nouns and frequency, and a slice of the `frwiktionary` dump
(875,956,556 bytes) for `lexicon.glosses` and the aspirated-*h* list. Both are CC BY-SA
4.0.

Unlike German there is nothing to quarantine *from*: no CC0 French distribution exists or
precedes it, so ADR 0013's per-distribution rule is satisfied by one package rather than
two. French therefore registers its own `fr` entry point directly, with **no `pack()`
factory** — the simple shape German could not have. ADR 0030's factory stays German-only,
and that asymmetry is deliberate and recorded rather than smoothed away.

**D2. No `stress`, and 103 is the ceiling.** French has no lexical stress. Lexique marks
none and the Wiktionary dump shows none. The 18 rows blocked on `stress` are all
accentual metres — iambic pentameter, dactylic hexameter, sapphic, alcaic, the sonnet
family, ottava rima, rhyme royal, spenserian, heroic couplet, trochaic tetrameter, double
dactyl, elegiac couplet, curtal sonnet, ballade, blank verse, proteus verse — and they are
not French forms. Declaring `stress` to reach 121 would be exactly the false-capability
defect ADR 0030 fixed twice in one day, in `denckring-en-data`'s `syllables` and in
`assonance_constraint`'s vowel test.

`alexandrine`, the French metre, needs only syllables and is in the reachable 23.

**D3. A line-level syllable seam, because French cannot be counted word by word.**
`denckring.procedures.syllable_count.line_syllables` sums `pack.syllable_count(word)`
across a line. That is right for English and German and wrong for French, where a final
mute *e* counts as a syllable before a consonant, elides before a vowel or mute *h*, and
never counts at the end of a line. Lexique gives `femme`, `une`, `belle` and `porte` all
`nbsyll=1` in citation form; in verse each is frequently 2. Summing them undercounts
systematically, and French verse is *entirely* syllable-counting, so `alexandrine` would
be wrong about most real French even with a perfect dictionary.

The seam: a pack may answer how many syllables are in a **line**, returning the same
`(total, estimated)` pair `line_syllables` already builds per line, and defaulting to
today's per-word sum. English and German inherit the default and are unchanged by
construction. French overrides it with the elision rules, reading the aspirated-*h* list
from D1.

The default lives on the pack rather than in `syllable_count`, so that the question "how
long is this line" is asked of the thing that knows the language — the same move ADR 0030
made for `is_vowel_phoneme` after `assonance_constraint` answered it with CMUdict's
convention and was wrong in German.

The 23 syllabic rows then work in French without any of them being edited, which is the
test of whether the seam is in the right place.

**D4. The French line count is estimated, never exact.** Diérèse and synérèse are not
decidable without editorial intent — `extraordinaire` is four syllables or five depending
on the poet — and plint, the mature tool, calls its own handling a liberal estimate.
ADR 0012's `exact` flag is what already exists to say so, and every syllabic report
carries `estimated_words`.

**D5. French declares `syllables`, and is the first pack that honestly can.** `orthosyll`
is an orthographic syllabation: `car-ros-se`, `ex-traor-di-nai-re`. ADR 0030 removed that
capability from `denckring-en-data`, which declared it and never implemented it, and
declined it for German, whose transcriptions carry no division of the spelling. French has
the data, so it declares it and implements it.

**D6. French gets `lexicon.graded_words`, and becomes the second pack that can.**
Lexique's `freqfilms2` and `freqlivres` are corpus frequencies. `anagram` needs a lexicon
graded by commonness in order to *generate* (ADR 0028); with this, `apply anagram` runs in
French. **Larger means more common here, where SCOWL bands mean the opposite** — the
build inverts to the project's convention rather than leaking a source's, and a test pins
the direction.

## Two tranches

The measured split is already the boundary, and chapter 4 proved the shape works:

- **Tranche A — the lexicon.** F1, F2 minus the prosodic capabilities, and the 10
  lexicon-only rows. Needs no line seam and no elision. French goes **70 → 80**, and it
  is independently shippable: if tranche B never happens, the ADR records why it stopped.
- **Tranche B — prosody.** F3, F4, the prosodic capabilities and the 23 syllabic rows.
  French goes **80 → 103**. This is where the risk is, and D3's alexandrine measurement
  is its go/no-go.

A's value does not depend on B, and B's design does not depend on A having shipped — but
doing A first means the distribution, the build script and the licence files all exist
before the hard part starts.

## Components

### F0. The test net, first

The SAMPA→IPA table is the one place French can go silently wrong, so it is tested
against hand-checked words before anything reads it. Golden cases follow each component
rather than the whole chapter.

### F1. `denckring-fr-data`

Package, `LICENSE-LEXIQUE` and `LICENSE-WIKTIONARY`, and `scripts/build_lexicon.py`
taking Lexique's zip and the Wiktionary dump, in the committed-and-diffable convention
`denckring-de-data` and `denckring-de-wiktionary` both follow. Version-locked to the other
four, making it a five-way lockstep — a cost ADR 0013 already admits and this compounds.

### F2. `FrenchDataPack`

`phonemes`, `syllables`, `syllables.dictionary`, `syllables.heuristic`, `lexicon.words`,
`lexicon.nouns`, `lexicon.glosses`, `lexicon.graded_words`. A fixed `ClassVar`, as on every
pack except German's.

### F3. The line seam

The default on `BasePack`, and the French override. This is the only change to `src/`
outside the French pack, and it must leave English and German byte-identical in behaviour
— a test asserts their line counts are unchanged across the existing fixtures.

### F4. The aspirated-*h* list

Extracted from `frwiktionary` in the same build pass as the glosses. Small, closed enough
to inspect, and vendored as data rather than as a rule in code, because it is a list of
words and not a generalisation.

### F5. Golden cases

French cases for the 33 rows that unblock (23 + 10), built the way chapter 4 built the German ones:
a verified line kit first — French verse lines checked against their own checkers before
any of them is written into a fixture — then the cases assembled from it.

## Testing

The gate is unchanged and must stay green, including `mypy --strict` over the five
package source trees and `denckring eval --all`.

Specific to this chapter:

- **Two measurements**, both for the ADR. Lexique's token coverage over public-domain
  French prose and verse, the way chapter 4 measured 94.0% over 340,958 tokens of
  Wieland, Goethe, Kafka and Mann. And — the one that actually tests D3 — the share of
  alexandrines from Racine and Hugo that the line counter scores at exactly twelve.
  That second figure is pass/fail per line rather than a coverage percentage, so it is
  the honest measure of whether the elision rules work, and it is the number the ADR
  stands on. If it is poor, D3 is wrong and the chapter stops rather than shipping it.
- **A `french-without-data` CI job**, mirroring `german-without-pronunciations`: with
  `denckring` alone, a French syllabic row must raise `MissingCapability` naming what is
  missing rather than guessing.
- **English and German line counts unchanged**, asserted rather than assumed, because D3
  touches a function both use.
- **The SAMPA→IPA table**, against hand-checked words.
- **The frequency direction**, pinned, because D6 inverts a source's convention.

## Out of scope

**As of 2026-08-31 — this section describes the state before this chapter, and dates
badly.** Chapter 4's spec was misread this way once; date it against `git log` before
trusting it.

- **`stress` for French.** D2. Not deferred — refused.
- **The caesura.** `alexandrine` checks twelve syllables and not the hemistich, and this
  chapter does not change that. plint does not check it either, for the reason it gives:
  the hemistich must fall at a sensible grammatical position, which is not decidable here.
- **Feminine/masculine rhyme alternation**, which French classical prosody requires and
  this project's `rhyme_scheme` does not model in any language. A real gap, and a
  different one.
- **Diérèse as a parameter.** D4 makes the count estimated; letting a caller declare a
  diérèse is a reasonable future request and is not designed here.
- **The layer split** (ADR, decided 2026-08-31), which is being written in parallel and
  shares nothing with this chapter but the release it precedes.
- **Widening `Lang` beyond `en`, `de`, `fr`.** The structural cap on a non-Eurocentric
  catalogue, and its own decision.
