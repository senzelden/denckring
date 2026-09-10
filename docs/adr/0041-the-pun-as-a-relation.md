# 41. A pun is a relation between two texts, and only part of it is checkable

## Context

`paronomasia` is the first row whose popular form — the punning shop window,
*Curl Up & Dye*, *Diminu'tif*, *Haarmonie* — is better attested than its
scholarly one, and the first where the obvious reading of the procedure is a
judgement no program makes. "Is this a good pun" is not decidable here, and
neither is "is this a pun". A row that promised either would be the catalogue
definition promising more than its checker verifies, which ADR 0015 names as the
error it exists to prevent.

Two further things were true before any code was written, and both narrow the
row rather than the ambition behind it.

**The phonetic half was already built.** The research this row came from
proposes ingesting CMUdict, Lexique and WikiPron and adding PanPhon for a
feature-weighted distance. `pack.phonemes()` has answered in all three languages
since ADR 0030 and ADR 0032, and twenty-three rows already read it. Nothing new
had to be acquired.

**The orthographic half cannot be built from what is here.** A pun's surface is
usually a coined word, and no pack can pronounce a word it has never seen.
Measured: `hairways`, `hairitage`, `barberella`, `Haarmonie`, `Chaarisma` and
`atmosphair` all raise `MissingCapability`, while `bread`, `Kamm`, `tif` and
`diminutif` resolve. That is not a gap in one language's data — it is the
difference between a dictionary and a grapheme-to-phoneme model, and this
project has the first and not the second.

## Decision

**D1. The row checks a declared relation, not a quality.** `checkability: source`.
The caller declares the phrase (`source`), and the check decides three things
about the text against it: that at least one word has been displaced, that no
more than `max_displacements` have been, and that each displacement lands inside
a requested band of phonetic distance. Whether the result is funny, or is a pun
at all, is the writer's claim — the position `kangaroo_word` takes on synonymy
and `antigram` on oppositeness.

**D2. The knob is a band with two edges, not a ceiling.** `min_distance` and
`max_distance` both bind, so `0.0`–`0.0` asks for a homophone and refuses
anything else, and `0.4`–`0.7` asks for a pun that has to work for it and
refuses a homophone as too easy. A ceiling alone would make "make it worse" —
the thing the whole idea is about — inexpressible, and would turn the row from a
constraint into a scorer.

**D3. Distance is unweighted Levenshtein over the pack's own phoneme symbols,
normalised by the longer sequence.** Not PanPhon's feature-weighted PFER, which
is the more perceptually faithful measure. Two reasons, in order of weight: it
would put numpy and pandas behind a package whose dependencies are pydantic,
pyyaml and typer and which claims free-threading support; and it needs a feature
table per notation, where this needs none. Because a pun is made inside one
language, both sides of any comparison come from the same pack and are already
commensurable — the three notations (ARPABET, IPA, IPA-from-SAMPA) never meet.

**D4. ARPABET stress digits are stripped before comparing.** CMUdict marks stress
on the vowel, so `DH AH0` and `DH AH1` are one word spelled two ways; left in,
`the` would read as a pun on `the`. The rule strips a *trailing digit*, so it is
a no-op for German and French, which mark stress with separate IPA symbols.

**D5. A word the dictionary lacks is reported, never guessed at.**
`unknown_word` carries the same three readings as `n_plus_7.ambiguous_nouns` and
`RhymeParams.unknown_rhyme`, defaulting to `undecidable`. It is scored as a
violation rather than dropped, on `spoonerism`'s ruling R14: a displaced pair has
nothing to fall back on, so dropping it would let a text of nothing but coinages
score 1.0 vacuously.

**D6. The blend family is out of scope and is named, not implied.** Displacements
onto coined words need a `phonemes.g2p` capability, named in the row's `notes`
with no pack behind it — the state ADR 0015 calls honest, and the one
`homophonic_translation` is in for `phonemes.bilingual` and `perverb` for
`corpus.proverbs`. The found pun, which displaces nothing, states no relation
between two texts and is not this row at all.

**D7. No golden case claims external provenance in this pass.** The row's sources
are the rhetoricians the catalogue already cites elsewhere, but no example has
been read off the page here, and an example nobody has read is the invented
citation the house style refuses. The attested modern corpus is entirely
post-1929, and whether this package may quote it is a maintainer decision already
pending for research batch 3.

**D8. The trade is a parameter, and it ranks before sound.** `domain` names a
shipped vocabulary; `domain_words` supplies one. A candidate belonging to the
trade is offered before one that does not, and only then does distance decide.
Without a trade every candidate ranks equal there and the key falls through to
sound alone, which is the general behaviour.

The first ordering shipped in this ADR was wrong and is recorded rather than
quietly replaced: it ranked by SCOWL band first, so `bread` (band 20) came 74th
behind `brand`, `bad`, `it` and `put` (all band 10) *whatever* their distance,
and the canonical example of the figure could not be generated by the row that
catalogues it. Band 10 and band 20 are both words every reader knows, so
commonness was not buying what its comment claimed. It now breaks ties only.

**D9. The trade files are authored, and they carry the phrases too.** Each ships
per language a vocabulary *and* a set of target phrases, because two things that
no rule in the checker can express turned out to decide whether output is any
good, both measured: displacing a function word produces nonsense (French `la`
is 0.333 from `laque`, which offers `laque vie en rose` for half the language),
and a phrase that already contains its own trade word has nothing left to
displace (`Curl up and die`, `Das Brot`). Every word and phrase was written for
this project, so there is no third-party licence and nothing to quarantine under
ADR 0013 — the Poesieautomat's 360 authored fillers are the precedent.

## Consequences

**The knob's meaning depends on word length, and the ADR would rather say so than
hide it.** Distance is normalised by the longer sequence, so a fixed band is
proportionally stricter on long words. Measured over the pronounceable graded
lexicon, inside the default band `0.0`–`0.5`: English `air` (2 phonemes) has 49
displacements available, `brad` (4) has 240, `heritage` (7) has 35. A caller who
tunes a band on short words and applies it to long ones will find it tighter than
they left it.

**The measure cannot tell a near-miss consonant from a distant one.** That is the
admitted cost of D3: `/t/`→`/d/` and `/t/`→`/m/` both cost one edit, where a
feature-weighted measure would charge much less for the first. A band tuned on
vowel swaps will not behave the same way on consonants.

**Homophone density differs sharply by language, and this is the orthography
showing through.** At distance exactly 0.0, French `air` has 13 displacements and
`temps` has 7, English `air` has 3, and German `Komm` and `Haar` have none.
French spelling is many-to-one on sound and German is close to phonemic, so the
same band buys a French writer a family the German writer does not have. It is
not a defect in the German data: 72,734 of German's 101,296 graded words carry a
pronunciation, against 45,884 of English's 77,078.

**Coverage moves and the externally-sourced share falls.** 122 implemented rows
become 123 and the catalogue 156 becomes 157; twelve constructed cases take the
corpus from 560 to 572 and the external share from 11.8% to 11.5%. The fall is
arithmetic, not a regression — D7 is why, and reversing it is a one-file change
once the ruling lands.

**The row reads as `heuristic`, not `exact`, and that is correct rather than a
misfiling.** `Reading.determinacy` is derived from whether a row's `requires`
names a soft capability, and `phonemes` is one: a pronouncing dictionary records
one committed reading of a word, several words carry more than one, and the
distance between two of them inherits that. A caller who reads `exact` off
`spoonerism` and expects the same here would be reading the wrong thing into
both.

**A trade is not padded into a language it has nothing for, and one trade ships
weak on purpose.** `optician` has English only; `bakery` dropped German after
all four of its first-draft phrases displaced outside the trade. And the
optician's vocabulary is the weakest of the three measured: its near neighbours
are mostly inflections of a word already in the phrase — `frame`/`frames`,
`lens`/`lenses` — which is morphology wearing a pun's clothes, and the checker
cannot tell the difference because a plural genuinely is a different word at a
small distance. It ships anyway, saying so in its own file, because three trades
that all flatter the procedure would be evidence about the choosing rather than
about the procedure.

**No search budget was needed, which is unusual for a generative row.**
Prefiltering candidates on phoneme length and on sharing a first or last phoneme
takes English's 45,884 pronounceable words down to between 143 and 2,424 per
position, and the scan then runs in under a hundredth of a second — so unlike
`anagram` and `word_ladder` this row has no node ceiling to tune. The built
lexicon is cached per pack because building it is the expensive part: 0.3s for
English, 1.2s for German.
