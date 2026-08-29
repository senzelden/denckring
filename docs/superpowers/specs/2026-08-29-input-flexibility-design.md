# denckring — input flexibility

**Date:** 2026-08-29
**Status:** draft
**Scope:** the choices a caller could not make — which dictionary, which language, which reading of an undecidable verdict, and how much of the source an anagram must use
**Branch point:** `0195c56` (154 catalogued · 128 implementable · 119 implemented · 119 validated · 26 not mechanically checkable)

This is **Spec B of chapter 3**. Spec A — the anagram spine — merged earlier the same day as
ADRs 0027 and 0028. Everything here was named in that spec's Out-of-scope section.

## Purpose

Chapter 3's first half made `anagram` work. This half is about the things a caller is told
they can choose and cannot.

`n_plus_7`'s own catalogue definition says the displacement happens "in a chosen
dictionary". No such choice exists: the procedure walks `pack.nouns()` and there is no
parameter to point it elsewhere. That is a definition promising more than the
implementation delivers, which is the defect class ADR 0015 exists to prevent, sitting in
the catalogue since the row was written.

`lang: "fr"` fails with `UnknownLanguage` on a check that needs no language data. The
catalogue ships French names and definitions for `anagram`; a French anagram pair validates
perfectly under the tokeniser and the letter multiset, neither of which is French-specific.
The failure is real but it blames the wrong thing.

N+7's checker accepts an unchanged noun because no word list can rule out its being a verb
in that position, and reports `ambiguous_words` in its metrics. The behaviour is right. The
verdict is more confident than the evidence: `satisfied` is `True` with no way for a caller
to ask for the stricter reading.

`anagram` requires an exact letter multiset. The transposal tradition — a candidate built
from *some* of the source's letters — is not expressible, and `check` reports every unused
letter as `missing_letter`.

## Decisions

**A French core pack, not a generic fallback.** `Lang` is already
`Literal["en", "de", "fr"]`, and ADR 0022 established the shape when German moved from an
entry point to a built-in default: a pack with no data files, declaring
`{TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES}`. French gets the same. A generic
"fall back to something minimal for any unknown language" was rejected: it would let a row
run under a pack weaker than its author assumed, silently, and `Lang`'s three members mean
there is no open-ended case to serve.

The consequence is that failures move to the right layer. `check n_plus_7 lang=fr` still
fails — but with `MissingCapability` naming `lexicon.nouns`, which is what is actually
absent, rather than `UnknownLanguage` naming a language that is merely undersupplied.

**`describe` computes which languages a row runs in.** Once French works for core-only
rows, a row whose `meta.languages` reads `[en]` while it demonstrably validates French is
making a false claim, and this project treats those as defects. `meta.languages` stays as
authored *editorial* scope — `wechselsatz` is German by nature and not merely by
capability — and a computed field reports what the installed packs can actually satisfy.
Two fields because they answer two questions; one derived so it cannot drift.

**The dictionary is a `check` parameter, and that is forced rather than chosen.** `check`
verifies a displacement by walking the same list the writer walked. Given a different list
it computes different displacements and rejects correct work. So `dictionary` goes on
`NPlus7Params`, not on the apply-only model — the first parameter in this catalogue whose
placement is decided by the checker's needs rather than the generator's.

**Its shape is an inline list, with the pack's nouns as the default.** A named-dictionary
enum was rejected: SCOWL is not part-of-speech tagged and cannot serve a noun walk, so
today an enum would have exactly one valid member — a choice in name only, which is the
defect being fixed wearing a new hat. An inline `list[str]` is honest about the real use,
which is small and editorial: N+7 in a gardening dictionary, in a single author's
vocabulary, in the hundred words of a manifesto.

**`ambiguous_nouns` copies `unknown_rhyme` exactly.** `RhymeParams` already solved this
shape for a different undecidable: three readings — leave it unscored, let it pass, fail
it — carried as a parameter under ADR 0009 rather than settled as a library constant. The
same three readings apply unchanged to a noun that may not be a noun here. Reusing the
vocabulary matters more than inventing a better one: a caller who has met one has met both.

The default is `free`, which is what ships today. `undecidable` is arguably the more honest
default and was rejected for this chapter on a narrower ground: changing it silently
changes the score of every existing N+7 text containing an unchanged noun, and a verdict
change is worth its own decision rather than arriving as a side effect of adding the knob.

**`satisfied` stays `score == 1.0`.** The obvious reading of "the verdict is too confident"
is a third verdict state, and it is refused. `Report.satisfied` is documented as exactly
`score == 1.0`, and ADR 0005 made the score continuous so that partial credit had one
representation. A third state would give it two.

**Subset covers are a parameter on `anagram`, not a new row.** `allow_subset` matches
`allow_identity`'s shape — the same procedure under a stated convention, not a different
procedure. Under it, `missing_letter` stops being a violation while `surplus_letter`
remains one: a transposal may use fewer of the source's letters and never a letter the
source does not have.

**The generator learns it too, not only the checker.** ADR 0002 makes `apply` the optional
half, so a checker-only parameter would be defensible — but it would mean `check` accepts a
class of text `apply` can never produce, and this project has kept that asymmetry narrow.

**Ranking gains `letters_used` as its primary key.** Under `allow_subset` every single word
that fits the source is a valid transposal: 373 of them for `astronomer` before any
multi-word cover is considered. Ranked by the existing keys, turning the flag on would bury
every good answer under one-word fragments. Sorting by letters used, descending, before
word count keeps full covers at the head of the list, so today's output remains the first
thing a caller sees.

## Components

### V0. A paragraph-shaped strategy

`tests/test_round_trip.py` runs at `max_examples=1000` because `fold_in` and
`mathews_algorithm` need two blank-line-separated paragraphs, which text drawn uniformly
from the test alphabet offers about once in three hundred examples. The chapter-2 spec
recorded the durable fix: reach those rows by construction rather than by drawing enough
examples to get lucky.

A Hypothesis strategy that builds paragraph-shaped text, composed with the existing `TEXT`
rather than replacing it — the alphabet's `\n`, `|` and `.` are each load-bearing for other
rows and that reasoning is written down in the module docstring.

Once the rows are reached by construction, `max_examples` comes back down. **The number it
returns to is measured, not chosen**: the floor is what the rarest reachable row actually
costs, and `test_the_named_coverage_gap_is_the_whole_coverage_gap` is what proves the floor
holds. If lowering it makes that test fail, the strategy has not done its job and the
number is not the problem.

This is first for the reason W0 was first in Spec A: it is the net the rest lands on.

### V1. French, and failures at the right layer

`FrenchPack` in `src/denckring/lang/`, added to `_DEFAULTS` beside `GermanPack`, mirroring
it in shape and in size.

The alphabet needs a decision the German pack already faced. French carries
`é è ê ë à â ä î ï ô ö ù û ü ÿ ç` plus the ligatures `œ` and `æ`. German's
`fold_diacritics` maps `ß` to `ss` because no single letter is right; `œ` and `æ` are the
same case and fold to `oe` and `ae`. Record the choice where `de.py` records its own, and
note that ADR 0009 makes folding a procedure parameter rather than a property of the data,
so a caller who wants `œ` to stay a letter can have that.

`describe` gains a computed report of the languages whose installed pack satisfies the
row's `requires`. `meta.languages` is untouched.

### V2. A chosen dictionary

`dictionary: list[str] | None = None` on `NPlus7Params`, defaulting to `pack.nouns()`.
`s_plus_7` inherits it, since it already delegates to `NPlus7Params` and
`displacement_report`.

Validated the way ADR 0015 already restricts `nouns()`, and for the same reason: entries
must be single alphabetic tokens the tokeniser returns whole, because a displacement has to
be a word that survives being read back. A `cat's-paw` in a supplied dictionary would break
the correspondence between source and result exactly as it would in the shipped list.

Order is the contract. N+7 walks *the seventh noun after* a given one, so a supplied list is
an ordered sequence and its order is the caller's editorial choice, not something to
normalise. Displacement wraps modulo its length, as it does today.

A word absent from the supplied dictionary is left alone, which is already the behaviour
for a word the pack does not call a noun.

**A limitation to state rather than hide.** `require_capability` runs before parameters are
parsed, so `lexicon.nouns` is checked whether or not a dictionary was supplied. A custom
dictionary therefore works wherever the pack already has a noun list; it does not unlock
N+7 for a language whose pack has none. Making the capability conditional on a parameter is
a spine change — it inverts the order of two steps every procedure inherits — and it is out
of scope here.

### V3. The reading of an undecidable noun

`ambiguous_nouns: Literal["undecidable", "free", "strict"] = "free"` on `NPlus7Params`,
threaded through `displacement_report`.

- `free` — an unchanged listed noun counts toward `good`. Today's behaviour.
- `strict` — it counts as a violation, with a rule name saying what was undecidable.
- `undecidable` — it is removed from both `good` and `total`, so it neither helps nor
  harms.

`undecidable` is the one reading that can drive `total` to zero, on a text whose every word
was an unchanged listed noun. `displacement_report` already removed an earlier floor on
`total`, recording in a comment that the length-mismatch check above it covers the case the
floor was guarding — that reasoning was about an empty candidate and does not extend to
this one. Decide what a wholly undecidable text scores and say so in the code: a report
that is `satisfied` because nothing could be judged is the same overconfident verdict this
workstream exists to fix, one level down.

`metrics["ambiguous_words"]` already exists and keeps its meaning under all three, which is
what lets a caller see how much of the verdict rested on the reading they chose.

### V4. Subset covers

`allow_subset: bool = False` on `AnagramParams` — the check model, so `check` and `apply`
both see it.

`_check`: `multiset_violations` stops reporting `missing_letter` under the flag.
`surplus_letter` is unchanged and unconditional. Scoring changes with it: `total` becomes
the candidate's letter count rather than `max(candidate, source)`, so a short valid
transposal scores 1.0 instead of being marked down for brevity — under exact cover the two
are identical, so nothing changes when the flag is off.

`_produce`: the recursion records a cover when the remaining multiset is empty *or*, under
the flag, at every node where the chosen words are non-empty. `Candidate.metrics` gains
`letters_used`.

Ranking becomes `(-letters_used, word_count, max_band, text)`. With the flag off,
`letters_used` is constant across all covers and the key is exactly today's.

The catalogue row's provenance is untouched: this is a parameter on an existing procedure,
not a new row, so no new attestation claim is made. The parameter's documentation describes
the transposal convention without citing a page — `Attestation` offers no value meaning
"unverified", and `author-stated` is the only one that demands a citation, so silence is the
honest form here rather than a weakened claim.

## Testing

The gate is the four commands plus `eval --all` and `status`.

- V0's success condition is measurable and must be measured: the rows currently reached by
  luck are reached at a materially lower `max_examples`, and the coverage-gap test still
  passes. A strategy that changes nothing measurable has not earned its place.
- V1: a French anagram pair validates; `n_plus_7` under `lang="fr"` raises
  `MissingCapability` naming `lexicon.nouns` and **not** `UnknownLanguage`. The distinction
  is the whole point of the workstream, so it is asserted on the error type, not on a
  message.
- V2: a text displaced under a supplied dictionary satisfies its own check under the same
  dictionary, and fails under a different one. Both directions, or the test proves only
  that the parameter is accepted.
- V3: the same text scores differently under all three readings, and `ambiguous_words`
  reports the same count under each.
- V4: with the flag off, output is byte-identical to today's for `dormitory`, `astronomer`
  and `listen` — the regression that keeps this from being a behaviour change in disguise.
  With it on, a strict subset of a source's letters satisfies `check`, and the first result
  is still a full cover.

## Out of scope

- **Conditional capabilities.** Named in V2. `require_capability` running before parameter
  parsing is why a supplied dictionary cannot substitute for `lexicon.nouns`. Inverting
  those two steps changes the template method every procedure inherits and deserves its own
  spec.
- **`anagram`'s dictionary.** The research note grouped `anagram` with `n_plus_7` and
  `s_plus_7` as wanting the same mechanism. After ADR 0028 it does not: its lexicon choice
  *is* `max_size` over SCOWL's bands, which is selectable, sourced and already shipped. The
  item closed itself and building a second mechanism would be inventing a need.
- **Changing `ambiguous_nouns`'s default to `undecidable`.** Argued above; a verdict change
  deserves its own decision rather than arriving with the knob that makes it possible.
- **A third verdict state.** Refused above. `satisfied` is `score == 1.0` and ADR 0005 made
  the score continuous so partial credit had one representation.
- **German and French lexicons.** `FrenchPack` ships no data, exactly as `GermanPack` did
  before `denckring-de-data`. What it takes to give French a noun list is the same question
  ADR 0023 answered for German, and it is not this chapter's.
- **Spelling variants and the `i` exclusion**, both from ADR 0028, are unchanged here and
  remain open for their own reasons.
