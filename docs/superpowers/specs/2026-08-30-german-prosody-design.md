# denckring — German prosody

**Date:** 2026-08-30
**Status:** tranche A implemented 2026-08-30; tranche B implemented 2026-08-31, with
D3 and the distribution's name amended — see ADR 0030
**Scope:** the syllable, stress and phoneme capabilities the German pack has never had, and the data distribution that can supply them
**Branch point:** `f0ffdcb` (154 catalogued · 128 implementable · 119 implemented · 119 validated · 26 not mechanically checkable)

This is **chapter 4**, and it does not answer the developer's MCP report that chapters 1–3
answered. It answers the project's own metric.

## Purpose

`denckring status` reports coverage against the implementable subset, and that figure is
this project's headline claim. It is a claim about English. Measured on this install:

| pack | rows that run | of 119 |
|---|---|---|
| `en` | 119 | 100% |
| `de` | **78** | 66% |
| `fr` | 70 | 59% |

Reproduce with:

```python
from denckring.core.registry import all_procedures
from denckring.lang import get_pack, installed_languages
for lang in installed_languages():
    caps = set(get_pack(lang).capabilities)
    runs = [p for p in all_procedures().values() if all(c in caps for c in p.meta.requires)]
    print(lang, len(runs), "of", len(all_procedures()))
```

Nothing here is dishonest — no row's editorial `languages` claims a language it cannot run
in, and ADR 0029 added `runs_in` so a caller can ask rather than assume. But 41 German rows
are blocked, and **39 of the 41 are blocked on prosody**: `syllables.heuristic` (29),
`phonemes` (21) and `stress` (17), overlapping across rows. The other two want
`lexicon.glosses`, a different source, out of scope below. Every metre, rhyme and verse form
in the catalogue is in the prosody set.

This is the only gap in the project with no decision record either way. ADR 0012 settles the
`syllables.heuristic`/`syllables.dictionary` split without mentioning German. ADR 0023 chose
Wikidata Lexemes for the German lexicon and is silent on prosody. The gap is not a decision
that was made; it is one that was never reached.

`stress` alone unblocks **nothing** — it never appears in a `requires` without syllables — so
this is one piece of work, not three:

| `de` gains | rows that run |
|---|---|
| — (today) | 78 |
| `syllables.heuristic` | 89 |
| `syllables` + `stress` | 96 |
| `syllables` + `stress` + `phonemes` | **117** |

## The measurement that chose the source

Written before the design, because the design depends on it and because ADR 0018's
provenance rules mean a data source is recorded, not assumed.

**Wikidata Lexemes cannot carry this.** It is the obvious candidate — ADR 0023 already
settled that source and its CC0 licence for `denckring-de-data`, so the build script, the
licence file and the quarantine argument would all have been reused. Queried against the
same SPARQL endpoint `packages/denckring-de-data/scripts/build_lexicon.py` uses, on
2026-08-30:

| | count |
|---|---|
| German forms carrying IPA (P898) | 6,904 |
| distinct written representations among them | **3,342** |
| representations the pack already knows (ADR 0023) | 668,580 |

**0.5%.** For scale, CMUdict — which gives English `phonemes`, `stress` and
`syllables.dictionary` — carries 135,166 entries; this is 2.5% of that. The transcriptions
are also not uniform: `[ˈniːɡɐ]` appears bracketed beside a bare `ˈkatsə`, so even the 3,342
would need normalising. The cheap answer was tried first and it failed; that is the finding,
not a preamble to one.

**German Wiktionary can.** Sampled with the MediaWiki API against the pack's own word lists
(seed `20260830`, n=300 each) and against real text:

| measure | coverage |
|---|---|
| noun lemmas, sampled from the 184,040-entry list | 41.7% |
| all forms, sampled from the 668,580-entry list | 17.0% |
| **tokens of the project's own German golden fixtures** | **90.8%** |

The spread between 17% and 91% is the whole argument, and it is not a contradiction: **a
pronouncing dictionary does not need to cover the lexicon, it needs to cover text.** The
lexicon is dominated by rare compounds — German makes them freely, and Wiktionary has no
entry for most — while text is dominated by common words, which Wiktionary documents well.
The 17% figure describes a corpus nobody reads.

Two cautions the numbers carry, recorded rather than smoothed over:

- **The 90.8% comes from 639 tokens of this project's own fixtures**, which are short and
  deliberately plain. Real literary German will be worse. The build must re-measure against
  the dump, and that figure — not this one — belongs in the ADR.
- **The residue is mostly not German.** Of 29 unmatched types, `dnuh`, `llenhcs` and `won`
  are reversed strings from palindrome fixtures, `fuenf`/`zwoelf` are ASCII transliterations
  from `fold_diacritics` fixtures, and `katze`/`hund`/`strand` are deliberately lowercased
  nouns. Genuine misses are proper nouns (`Sylter`, `Victor`), free compounds (`Tischbürste`,
  `Boxkämpfer`) and poetic elisions (`vergehn`, `ohn`, `läßt`).

## The constraint that shapes everything

`denckring/lang/__init__.py:47` refuses to choose between two packs claiming one language:

```python
def _install(packs, lang, pack, *, source):
    if lang in packs:
        raise DuplicatePack(lang, _SOURCES.get(lang, "an installed pack"), source)
```

So the obvious shape for a share-alike source — a fourth distribution registering its own
`de` entry point — **cannot work**. Installing it beside `denckring-de-data` raises
`DuplicatePack` at import, before any procedure runs.

That collides with ADR 0013, which quarantines data licences per distribution precisely so
that "a future copyleft lexicon has an established place to go". Two rules of the
architecture, both right, pointing opposite ways. Resolving it is the real work here; the
syllable heuristic is a morning's coding by comparison.

## Decisions

**D1. The heuristic ships in core, the dictionary ships in a distribution.** This is the
shape English already has and it is not reinvented: `denckring.lang.en` declares
`syllables.heuristic` with no data files, and `denckring-en-data` overrides it with CMUdict
lookups and falls back to core for unknown words. German gets the same two layers. The
consequence is that tranche A lands with no licence question, no ADR and no new package —
and that it is worth doing even if tranche B is never built.

**D2. The German heuristic is not a port of the English one.** Two of English's three rules
are wrong for German. Final `-e` is not silent — `Katze` is `ˈkat.sə`, two syllables — so
the silent-`e` subtraction and its compensating `-le` rule are both dropped rather than
carried over. German's diphthongs are a closed set (`au ei ai eu äu oi`) counted as one
nucleus, and `ie` is a long monophthong, not two. The admitted cost: vowel sequences across
a morpheme boundary undercount, so `Museum` reads `eu` as a diphthong and `Familie` reads
`ie` as one. `exact=False` is what keeps that honest, and it is the same class of error
English's heuristic already ships.

**D3. One pack per language; data quarantined per distribution.** `denckring-de-data` keeps
the sole `de` entry point and detects whether the phonetic distribution is importable,
declaring `phonemes`, `stress` and `syllables.dictionary` only when it is. Both invariants
survive: `DuplicatePack` stays meaningful, and CC BY-SA data never enters the CC0 package.

The cost is real and is not softened: **`capabilities` stops being a fixed
`ClassVar[frozenset]` for this pack and becomes computed from the install.** A reader of
`GermanDataPack` can no longer see what it can do without knowing what else is installed.
This extends an idea ADR 0029 already established rather than introducing one — `runs_in`
exists because what an install can do is a question a caller must ask — but it moves that
uncertainty one layer deeper, into the pack itself.

**D4. Stress comes from the transcription, not from a second source.** German Wiktionary's
IPA marks primary stress `ˈ` and secondary `ˌ`, so `stress_pattern` is derived from the
string exactly as English derives it from CMUdict's digits. No stress data is sourced, and
`stress` is therefore not a capability that can be present while `phonemes` is absent.

**D5. Lookup tries the token as written, then case-flipped.** German capitalises nouns *and*
sentence openers, and Wiktionary titles are case-sensitive. Measured: this alone moved token
coverage from 89.5% to 90.8%, recovering `Und`, `Was`, `Nicht`, `Ein` — function words whose
entries live at lowercase titles. The reverse direction matters too, for a lowercased noun.

## Components

### G0. The test net, first

German golden fixtures for the syllable heuristic before it exists, including the cases D2
names as wrong (`Museum`, `Familie`) so the undercount is pinned as known behaviour rather
than discovered later as a bug. `tests/test_round_trip.py` already covers every generator;
no new property is needed for A.

### G1. `syllables.heuristic` on `GermanPack`

`syllable_count` in `src/denckring/lang/de.py`, returning `(count, False)` always and never
less than 1. `SYLLABLES_HEURISTIC` joins the capability set. Eleven rows unblock; `status`
is unchanged, because `status` counts implemented rows and these were always implemented.

**This is the whole of tranche A and it is independently shippable.** If tranche B never
happens, German goes from 78 to 89 and the ADR records why it stopped there.

### G2. The capability, computed

`GermanDataPack.capabilities` becomes a computed property over an importable-check for the
phonetic distribution. Needs care: `capabilities` is read by `require_capability` on every
`check` call, so it must be cached rather than re-probed per call, and the probe must not
raise when the package is absent.

### G3. `denckring-de-phon`, the fourth distribution

Build script over the `dewiktionary` dump extracting `{{Lautschrift|…}}` from German
sections only, mirroring `build_lexicon.py`'s committed-and-diffable convention.
`LICENSE-WIKTIONARY` (CC BY-SA 4.0) beside it, and an ADR recording the source, the measured
coverage against the dump, and the licence quarantine. Version-locked to the other three, per
the lockstep ADR 0013 already admits as a cost — now a four-way lockstep.

### G4. `phonemes`, `stress`, `syllables.dictionary`

Implemented on `GermanDataPack` against the phonetic data, falling back to G1's heuristic for
unknown words exactly as `denckring-en-data` falls back to English core's. `rhyme_key` and
`rhyme_keys` derive from phonemes as they do for English.

## Testing

The gate is unchanged and must stay green: `pytest`, `mypy --strict src tests`, `ruff check`,
`ruff format --check`, plus `denckring eval --all` and `denckring status` for anything
touching a procedure.

Specific to this chapter:

- **Golden fixtures in German** for every row that unblocks, which is the project's normal
  bar for a procedure gaining a language.
- **A capability test that fails loudly if `de` silently loses one**, since D3 makes the set
  computed and a computed set can go empty without anyone noticing.
- **The `core-only` CI job's German equivalent**: `denckring[de]` without the phonetic
  package must raise `MissingCapability` naming `phonemes`, not guess.
- **`test_round_trip.py` is unaffected by tranche A**, which is worth stating because the
  draft of this spec assumed otherwise. It selects `procedure.meta.languages[0]` — the
  row's editorial language — rather than sweeping installed packs, so a pack gaining a
  capability adds no reachable row and cannot move the measured floor of 600.

## Out of scope

**As of 2026-08-30 — this section describes the state before this chapter, and dates badly.**

- **`lexicon.glosses` for German**, which the last two blocked rows want. A different source
  and a different licence question.
- **French prosody.** `FrenchPack` ships no data at all; 49 of its rows are blocked, and 39
  of those on exactly the capabilities this chapter builds for German (the other ten want
  `lexicon.words`, `lexicon.nouns` or `lexicon.glosses`). Nothing here is
  French-specific in principle, but a French lexicon is its own data and licence decision
  (ADR 0029 says so already).
- **Making `capabilities` computed for every pack.** D3 does it for one, where the need is
  demonstrated. Generalising it is a change to all three.
- **A frequency-weighted lexicon.** ADR 0028 wanted one for `anagram` ranking and settled for
  SCOWL's editorial bands. German Wiktionary would not supply one either.
- **The four decisions ADRs 0028 and 0029 leave open.** Untouched here.
