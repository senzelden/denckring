# 32. The French lexicon comes from Lexique and Wiktionary, in a fifth distribution

## Context

`denckring status` reports coverage against the implementable subset, and chapter 4
turned that from a claim about English into a measured claim about each language.
German finished at 121 of 121. French did not move: it ships in core with `tokens`,
`alphabet`, `fold_diacritics` and `letter_shapes` and no data at all (ADR 0029), and
**70 of the 121 implemented rows run on that**. The 51 that do not divide cleanly, with
no overlap: 23 want syllables and/or phonemes, 18 want `stress`, and **10 want nothing
but a lexicon**.

Those 10 — `charade`, `definitional_expansion`, `definitional_literature`,
`kangaroo_word`, `n_plus_7`, `s_plus_7`, `semordnilap`, `tmesis`, `word_ladder`,
`word_square` — are this record's subject. The other 41 are not, and one reason for that
is permanent; see D5.

**Wikidata Lexemes cannot carry French.** It was the obvious candidate and it was
measured first, because ADR 0023 already settled that source and its CC0 licence for
German, so the build script, the licence file and ADR 0013's quarantine argument would
all have been reused as they stand. Queried on 2026-08-31:

| | French (Q150) | German (Q188) |
|---|---|---|
| lexemes | **31,474** | 241,979 |
| noun lexemes | **12,768** | 188,948 |

French is 13% of German's lexeme count and **6.8% of its nouns**. `denckring-de-data`
ships 184,040 nouns; the French equivalent would be roughly 12,768. `n_plus_7` indexes
positionally into that list and `lexicon.words` answers membership from it, so at that
depth both would be confidently wrong about ordinary French rather than absent. The
cheap answer was tried first and it failed — the same finding, and the same order of
work, that ADR 0030 recorded for German IPA at 0.5%.

**Lexique 3.82 can.** Downloaded and measured on 2026-08-31:

| | |
|---|---|
| rows | 142,694 |
| distinct orthographic forms | 125,653 |
| lemmas | 46,947 |
| distinct noun forms (`cgram=NOM`) | **48,234** |
| rows with a phonemic form and a syllable count | **100%** |
| licence | **CC BY-SA 4.0** |
| archive | 26 MB zip, one TSV of 35 columns |

48,234 noun forms is **3.8× Wikidata's French nouns**, and it is an inflectional lexicon
rather than a lemma list — *aimer* is present in 36 forms, which is what a checker
reading running text needs. `freqfilms2` and `freqlivres` are corpus frequencies, so the
same file also answers commonness.

Lexique carries no definitions. The `frwiktionary` dump (875,956,556 bytes) does, and it
is CC BY-SA 4.0 as well, so `lexicon.glosses` costs a second source but not a second
licence decision.

**plint** (plint.a3nm.net) is the direct precedent and converged independently on
Lexique, which is corroboration for the choice. It is GPLv3 against this project's
Apache-2.0, so no code comes from it and none was read; its published *rules* are facts
about French and are not its code.

## Decision

**D1. One distribution, `denckring-fr-data`, two sources, one licence.** Under
`pip install denckring[fr]`. Lexique supplies `lexicon.words`, `lexicon.nouns` and
`lexicon.graded_words`; `frwiktionary` supplies `lexicon.glosses`. `LICENSE-LEXIQUE` and
`LICENSE-WIKTIONARY` sit beside the data, and `scripts/build_lexicon.py` regenerates
every table from the two archives, in the committed-and-diffable convention
`build_lexicon.py` and `build_pronunciations.py` already follow.

Both sources are CC BY-SA 4.0, so ADR 0013's per-distribution quarantine is satisfied by
one package. That is the whole reason French is simpler than German here: German had a
CC0 distribution already shipping and a CC BY-SA one arriving after it, and the two could
not merge.

**D2. French registers its own `fr` entry point, resolving to a class, not a factory.**
ADR 0030's `pack()` factory exists because two German distributions both had to answer
to one entry point without raising `DuplicatePack`. There is nothing to choose between
here: no CC0 French distribution exists or precedes this one, so the entry point names
`FrenchDataPack` directly and its `capabilities` is a fixed `ClassVar[frozenset]`, as on
every pack but German's. The asymmetry between the two languages is deliberate and
recorded rather than smoothed away by giving French a factory it has no use for.

**D3. The frequency bands are inverted at build time.** `LanguagePack.graded_words`
documents SCOWL's direction — larger means *less* common — and `anagram` sorts ascending
by it (ADR 0028). Lexique's frequencies run the other way. The build inverts, rather than
leaking a source's convention into a capability's contract, and a test pins the
direction, because this is exactly the class of defect ADR 0030 fixed twice in one day:
a row answering a shared question with one source's conventions.

**D4. The noun list is restricted to purely alphabetic forms, and the word list is
not.** `n_plus_7` walks the noun list and substitutes into running text, so a
displacement must be a word the tokeniser gives back whole — the rule
`denckring-en-data`'s `noun_list` docstring already states about `cat's-paw`. 3,324 of
48,070 French nouns break it, `abat-jour` and its hyphenated kin being most of them, and
they are dropped. Membership and ranking are asked about tokens, so `words.txt` and
`graded_words` keep those forms; only the positional list is filtered. A separate filter
drops multi-word entries (`a priori`, `acid jazz`) from both — 310 of 125,653 forms, 164
of 48,234 nouns — for the same reason: the tokeniser can never yield one.

**D5. French declares no prosody, and the ceiling for this record is 80.** French has no
lexical stress; Lexique marks none and the dump shows none. The 18 rows blocked on
`stress` are accentual metres — the sonnet family, iambic pentameter, dactylic hexameter,
sapphic, alcaic, ottava rima, rhyme royal, spenserian, heroic couplet, trochaic
tetrameter, double dactyl, elegiac couplet, curtal sonnet, ballade, blank verse, proteus
verse — and they are not French forms. Declaring `stress` to reach a bigger number would
be the false-capability defect ADR 0030 fixed in `denckring-en-data`'s `syllables`.

Lexique's `orthosyll`, `phon` and `syll` columns are present and are deliberately unused
here. The 23 syllabic rows need a **line-level** syllable seam, not a per-word count: a
French final mute *e* counts as a syllable before a consonant, elides before a vowel or
mute *h*, and never counts at the end of a line, so summing citation-form counts
undercounts systematically and `alexandrine` would be wrong about most real French even
with perfect data. That is a separate decision, gated on a separate measurement, and it
is not made here.

## Consequences

**French runs 80 of 121, up from 70**, and `denckring eval --all` goes from 417 to 439
passing cases, the 22 new ones French across eleven rows.

**The version lockstep is now five ways.** ADR 0013 admitted version-locking as the cost
of quarantining data per distribution; ADR 0030 made it four. Five distributions are
pinned to one version, one release moves all of them, and `release.yml` publishes all
five or the install is incoherent. Each new language makes this worse, and nothing in the
design bounds it.

**Every French capability inherits share-alike, and there is no CC0 French tier.**
German's split is `[de]` CC0 and `[de-wiktionary]` CC BY-SA, so a user who cannot accept
share-alike can still have German membership and nouns. A French user has no such choice:
Lexique is CC BY-SA and it is the only source measured to be deep enough, so
`lexicon.words` — the mildest thing a pack can offer — carries share-alike too. Adding a
CC0 French tier is not a matter of a flag; it needs a second distribution built from a
second source that does not currently exist. Anyone redistributing the derived tables
inherits attribution and share-alike on all four capabilities.

**The six bands are an arbitrary bucketing of a continuous quantity.** Lexique gives a
frequency, not a band. Six was chosen because it is enough to rank and few enough to
eyeball, and the ceiling is 60 because `anagram`'s `max_size` is capped there. That puts
roughly 20,900 words in each band with **no ordering inside a band**, so `anagram`'s
French ranking is coarser than its English one, where SCOWL's bands are somebody's
editorial judgement rather than a division of a sorted list. A caller comparing two
French words of similar frequency gets a tie the data could have broken.

**41 rows stay blocked in French, and 18 of them permanently.** The remaining 23 are
reachable and are not reached by this record. The 18 are not deferred; they are refused,
and no future data source changes that, because the missing thing is a property of the
language and not of the lexicon. French will not reach 121, and the honest ceiling is
103.

**`denckring-fr-data`'s wheel is 16,155,488 bytes** — measured, against
`denckring-de-data`'s 2,660,738 and `denckring-en-data`'s 7.0 MB. It is the largest
distribution in the project by some distance, six times the German lexicon package, and
the glosses are 15.3 MB of the 16. (The chapter spec's estimate of about four times was
written before the tables were built; the measured figure is the one to trust.) It is
excluded from the root sdist as the others are, so the sdist bound is untouched.

**The round-trip gate cannot see a French-only generator bug, and this chapter found one
by not relying on it.** The build's first noun table was produced by a `_lemma` helper
copied from the German script, which strips non-alphabetic characters. That is safe for
German, whose lexeme data carries no hyphens, and wrong for French: it made 3,302 nouns
unreachable by lookup while leaving them in the positional list, so
`n_plus_7.apply("abalone", lang="fr")` returned `abat-jour` — which `n_plus_7`'s own
checker then scored 0.0, because the tokeniser yields two words where the correspondence
needs one. `tests/test_round_trip.py` drives every procedure through `meta.languages[0]`,
which for `n_plus_7` is `en`, so the safety net that exists for exactly this class of
defect was structurally incapable of seeing it. D4 is the fix; a named regression test in
`tests/test_lang_fr_data.py` is the French leg the shared gate cannot supply for itself.
The general lesson is uncomfortable and is not softened here: the round-trip suite's
coverage is one language deep, and every second-language generator path is untested by
construction until someone writes the leg by hand.

**The gloss extraction discards more than it keeps, by design.** French Wiktionary marks
an inflected-form section `{{S|verbe|fr|flexion}}`, whose text describes a grammatical
form rather than defining a word — `accédons` reads "Première personne du pluriel de
l'indicatif présent du verbe accéder". Feeding that to `definitional_expansion` replaces
a word with a description of its own inflection. Skipping those sections takes the
extraction from 2,026,448 entries to 510,973 headwords; a further 14,110 of 700,213
senses are dropped for containing no letter at all, which happens when a sense line is
entirely templates and strips to punctuation. A `"."` gloss is worse than no gloss,
because `LanguagePack.glosses` documents the empty sequence as "could not resolve" and a
punctuation-only sense looks resolvable.

**An install without the data is now a real French shape and the suite never runs it.**
`denckring` alone still gives French 70 rows, and the other 51 must refuse by naming the
missing capability rather than guessing. A `french-without-data` CI job covers it, the
way `german-without-pronunciations` covers German's lexical-only install.

## Alternatives considered

**Wikidata Lexemes, for consistency with German.** Measured and rejected; see Context.
It would have cost nothing new architecturally and would have shipped a noun list a
quarter the necessary depth, which `n_plus_7` indexes into positionally.

**Two French distributions, mirroring German's split.** There is no CC0 French source to
put in the first one. The split would have been a package boundary with a licence on
both sides that is the same licence, and a fifth entry point's worth of machinery for it.

**Vendoring a G2P engine (`phonemizer`/espeak) instead of a table.** A runtime
dependency, TTS-oriented, and it answers the prosodic question this record does not ask.
Nothing about it is decided here.

**Deriving anything from plint.** GPLv3 against Apache-2.0. Its documented rules are
facts about French and are free to learn from; its implementation is not, and none of it
was read.
