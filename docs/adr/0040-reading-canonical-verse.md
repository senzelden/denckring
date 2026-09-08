# 40. Canonical verse is read strictly, and the strictness is a parameter

## Context

The corpus provenance split — added 2026-09-07 in *feat: the corpus says how much of
it is evidence about the reading*, and carried by no ADR of its own — reported **38 of 532 golden cases (7.1%) sourced outside this repository**. The rest
were written for the suite by its author, which is the failure the 0.1.0 review named:
an implementation and its own examples agree by construction, and a misreading of a
form is present in both or neither.

The attempt to raise that number found why it is low. The commit *test: canonical
verse, and what the checkers make of it* (2026-09-08) put seven canonical pentameter
lines through their rows, found three not read as ten syllables, and named synaeresis
as the sharp cause — *disobedience* is five syllables to CMUdict, exactly and with no
estimate, and four to Milton. It shipped as characterisation and deferred the editorial
question here, because widening the metre model touches all 41 heuristic rows.

Two research batches, both 2026-09-08, then supplied **23 verified public-domain texts
across 17 rows in three languages**, with per-item confidence notes and two deliberate
gaps (haibun, for want of any pre-1929 English translation rendering a prose-plus-haiku
unit). That is enough text to answer the deferred question on a measurement rather than
on a sample of seven. **This record rests on 111 canonical lines, and they do not say
what the seven said.**

### What 111 lines measure

| | exactly on metre | one over | other |
|---|---|---|---|
| English, 69 lines | 78.3% | 8.7% | 13.0% (all one under) |
| German, 42 lines | 45.2% | **52.4%** | 2.4% |

Nothing in English is off by more than one syllable. **Of the 15 English outliers, 12
contain a word the pronouncing dictionary had to guess** — `louely`, `heauen`,
`siluer`, `shielde`, `bloudy` and the rest of the 1590/1609 orthography, Chaucer's
Middle English, and the proper nouns `Sion`, `Aonian`, `Camöens`, `Thesiphone`. Only
**3 of 69 lines** are disagreements between the poet and the model with no guessing
involved. The seven-line sample pointed at prosody; 69 lines point at the lexicon.

German is a different story with a single cause: **52.4% of German canonical lines are
exactly one syllable over**, because the klingende Kadenz is the norm in German
blank verse and the alexandriner, not an exception.

## Decision

**D1. Feminine endings become expressible, and the bar was met — on line length.**
The bar, chosen before the work in the manner of ADR 0034's D5: *at least 95% of German
canonical lines must fall within their declared syllable count.* Measured **97.6%**,
against 45.2% today. The bar is stated on length because length is what was measured;
the stricter question is reported below rather than folded into it.

A feminine ending is **an additional acceptable pattern, not a different one**.
`line_metre` already scans a line against a set of readings — that is how a dactyl may
be a spondee — so permitting a klingende Kadenz means offering `{P, P + "0"}` where the
row offers `P`. A fixed longer pattern would not do: Gryphius' sonnet rhymes feminine
`Erden`/`Herden` (13 syllables) against masculine `ein`/`seyn` (12) in one poem, and no
single string spans both.

`shakespearean_sonnet`, `rhyme_royal`, `spenserian_stanza`, `blank_verse`,
`curtal_sonnet`, `alexandrine` and `elegiac_couplet` hard-code their metre; they gain a
parameter admitting the feminine variant, defaulting off.

**Under the full metre scan — stress pattern as well as length — the same texts go from
35.7% to 83.3%** (15 of 42 to 35 of 42). That is the honest figure for "does this line
scan", it is below the 95% bar, and the residue is a stress question that D4 addresses
rather than a length one D1 can reach. English is unchanged line for line under the same
change (Sonnet 18 stays 10 of 14, Milton 12 of 16), which is D6 holding by
construction.

**D2. English synaeresis is declined, on the measurement.** The bar: *it must fix at
least 10% of English canonical lines.* The ceiling is **3 of 69, 4.3%**, because
elision reduces a count and 9 of the 15 English outliers are already one syllable
*under*. Implementing it would move three lines and touch all 41 heuristic rows. The
lever English actually wants is dictionary coverage, and `Report.evidence` already
names the guessed word, which is what makes that diagnosable.

**D3. The rhyme model is not widened.** Measured over the canonical texts with their
correct schemes: **11 of 366 rhyme constraints violated, 3.0%, with zero false
positives.** Spenser and Gryphius are perfect. The 11 are Sibbald's slant rhymes (4),
Wordsworth's genuinely disputed scheme (5), `temperate`/`date` (1) and Chaucer's
`ye`/`joie` (1). Accepting slant rhyme would trade a model that currently never fires
spuriously for eleven cases, five of which sit in a text its own research note
recommends replacing. The four affected texts ship `satisfied: false` with the reason
in `source`, which is a true statement about how this package reads them.

**D4. Stress gets no general change; two rows declare a limitation instead.** 59 canonical lines
raise 13 `wrong_stress` violations, but they concentrate: outside `curtal_sonnet` and
`elegiac_couplet`, 44 lines raise **3**. `curtal_sonnet` does not read sprung
rhythm. `elegiac_couplet` already models dactyl and spondee as satisfiability per
ADR 0014, and fails on German accentual hexameter, where word stress and metrical
ictus diverge — Schiller's own *Hexameter* is stressed `0100` and takes the ictus
anyway. Both rows say so in the catalogue rather than the model moving under them.

**D5. A corpus case is transcribed from its named edition and never edited toward the
checker.** Measured, because the temptation is real and looks helpful: hand-modernising
Sonnet 18's orthography moved it from **10 of 14 lines on metre to 8 of 14**, since
expanding the Quarto's `ow'st` to `owest` both adds a syllable and leaves the
dictionary. Tuning the text to the checker destroys the only property that makes an
external corpus worth having. A rejection is the finding.

**D6. No default moves.** Every parameter this record adds defaults to today's reading,
so the 532 existing cases are unchanged by construction and the gate cannot go green
on a widening nobody asked for.

## Consequences

**Seven rows gain surface, and a silent wrong answer with it.** A caller who omits
`metre` gets today's verdict, which is right for English and wrong for a German
alexandriner — and gets it without a warning, because omitting a parameter is not an
error. D6 buys backward compatibility at exactly this price.

**The external corpus rises by less than 23 — correction, measured at 13.** This
paragraph predicted an upper bound before the corpus was built; the implementation
raised it from 38 to 51 (7.1% to 9.4%), which is a smaller rise than 23 and confirms
the bound rather than contradicting it, so the number below is a correction in the
sense of *filled in*, not *overwritten*. Four texts ship `satisfied: false` under
D3 and the four French sonnet and ballade cases cannot ship at all — `sonnet` and
`ballade` want `stress`, which French does not have, so they sit inside the 18-row
ceiling ADR 0034's D3 recorded. A `satisfied: false` case is evidence about the
reading, but it does not demonstrate a row accepting real verse, which is the thing
7.1% was low on: of the 13, only **five** demonstrate exactly that — Crapsey, Bentley,
Verlaine, du Bellay and Kuhlmann pass outright. The other eight, three of them German
(Gryphius twice, Goethe once), ship `satisfied: false` with the measured reading
recorded in `source`, which is the same shape this paragraph predicted, at the scale
this record can now state rather than bound.

**English canonical verse still fails, and this record declines to fix it.** 21.7% of
English canonical lines are not read on metre after D1. Anyone reopening D2 should
re-measure first and over more than 69 lines: 4.3% is a ceiling on *this* sample, and
the sample is six poems.

**The package still rejects Sonnet 18.** D3 makes that a position rather than an
oversight, and it will go on looking like a bug to anyone who meets it without this
record. That is the cost of a rhyme model with no false positives.

**`rondeau` is untouched and still cannot express its own history.** Its fifteen lines
are module constants, so Charles d'Orléans' thirteen-line rondeau — the older form —
raises `wrong_line_count` and `broken_rentrement` and has nowhere to go. That is a
catalogue question about form variants, not a strictness question, and it belongs in
its own record.

**Two of this record's inputs were wrong before they were measured.** The Gryphius
sonnet looked like a rhyme-model defect firing on eight correct rhymes; it was the
pentameter default, and with the right scheme and metre the rhyme is perfect. The
Kuhlmann abecedarian ships `satisfied: false` in its research note on the ground that
the source is stanza-initial, but the note excerpts only each stanza's first line, so
the text it actually supplies *is* line-initial and the checker's acceptance is
correct. Both were caught by running the texts rather than reading about them, which is
the only reason this record's numbers are worth anything.

**A defect the corpus found: lowercase `du` reads as two syllables.** `word_stress`
returns `['10', '?']` for `du` and `['?']` for `Du` and every other German pronoun,
though `syllable_count("du")` is correctly 1 — case-dependent, and the same family of
defect as the `find_word` casing mismatch fixed in `device.segment`. It lives in the
`denckring-de-data` distribution, not in this package, so this record cannot fix it.
It makes one of the 42 German canonical lines — Gryphius, "Es ist alles eitel", l.1 —
*report* as 14 syllables in a `wrong_stress` violation's `found` figure, where
`line_syllables` reads the same line correctly at 13. Parked rather than fixed:
`sonnet/gryphius-eitel-sonett`'s golden case carries a `min_score` floor rather than
an exact score for exactly this reason, so a later fix to the pronunciation data
raises the score instead of breaking the fixture.

**A scoring artefact, parked.** `metre_violations` returns `total=1` from its
wrong-length branch and `total=len(words)` from the branch where a line matches a
candidate's length, so turning `feminine_ending` on changes the score's denominator as
well as its numerator — a six-line Iphigenie excerpt goes from 20/24 to 38/39 for the
same line-for-line reading. Pre-existing: the single-pattern
path has always returned 0/1 for a wrong-length line, and D6 holds exactly, because
with `feminine_ending=False` there is one candidate and the accumulation is
byte-identical to before this record. No `satisfied` verdict is affected, since that
turns on whether violations exist rather than on the ratio; only `score` moves.
Documented in `line_metre`'s own docstring. Fixing it would change what `score` means
for every metre-bearing row, and ADR 0005 makes the continuous score load-bearing, so
it is its own decision record rather than a side effect of this one.

## Alternatives considered

**Widening the model to fit the poets.** Implement English and German elision, accept
feminine endings unconditionally, tolerate slant rhyme. Canonical verse passes, and
every one of the 41 heuristic rows accepts strictly more than it did — which blunts the
eval as a discriminator in exactly the dimension the provenance split exists to
measure. D1 takes the one piece of this that a bar justified and leaves the rest.

**Characterisation only: measure the gap, never move it.** The shape the 2026-09-08
canonical-verse commit already took, extended to all 23 texts. Honest and cheap, and it
leaves German failing 54.8% of its own canonical lines for want of a parameter the
`sonnet` row has had all along. D1 is too well evidenced to defer again.

**Modernising the texts so the dictionary can answer.** Refuted by measurement under
D5, and it would have been the wrong move even had it worked.
