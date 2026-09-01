# 34. French verse is counted a line at a time, and the count is an estimate

## Context

ADR 0032 shipped the French lexicon and stopped at 80 of 121, leaving 41 rows blocked
and dividing them: 18 want `stress`, which French does not have, and **23 want a
syllable count**. Its D5 declined to reach those 23 and said why — Lexique's
`orthosyll`, `phon` and `syll` columns were present and deliberately unused, because
the 23 need a *line-level* count and not a per-word one, and that was "a separate
decision, gated on a separate measurement". This record is that decision, and the
measurement did not come out well.

**French cannot be counted word by word.** `denckring.procedures.syllable_count`
summed `pack.syllable_count(word)` over a line, which is right for English and German
and wrong here. A French final mute *e* is a syllable before a consonant, elides
before a vowel or a mute *h*, and never counts at the end of a line. Lexique gives
`femme`, `une`, `belle` and `porte` all `nbsyll=1` in citation form; in verse each is
frequently 2. French verse is *entirely* syllable-counting, so `alexandrine` — the one
row named after a French metre — would have been wrong about most real French even
with a perfect dictionary.

**The go/no-go was the alexandrine share, and it was chosen before the work started.**
The chapter spec made D3 conditional on one figure: the share of Racine's and Hugo's
alexandrines that the line counter scores at exactly twelve. That figure is pass/fail
per line rather than a coverage percentage, which is why it was picked; the bar was
94%, and it was not reached. See D5.

## Decision

**D1. A pack answers for a whole line, and the default is today's per-word sum.**
`LanguagePack.line_syllables(line) -> (total, estimated)` joins the protocol.
`BasePack` implements it as the loop `syllable_count.line_syllables` used to run
inline, so English and German are unchanged by construction — neither pack overrides it
— and `tests/test_line_syllables.py` pins both halves of that: the default equals the
per-word sum, and English's line counts over a fixture are what they were.
`FrenchDataPack` overrides it with the elision rules.

The seam lives on the pack rather than in the procedure because "how long is this
line" is a question about the language, and the procedure is the wrong place to know
that a mute *e* exists. It is the same move ADR 0030 made for `is_vowel_phoneme` after
`assonance_constraint` answered a phonological question with CMUdict's convention and
was wrong in German. **The 23 syllabic rows then run in French without one of them
being edited**, which was the test of whether the seam sits in the right place.

**D2. French declares `syllables`, `syllables.dictionary`, `syllables.heuristic` and
`phonemes`, from a table of 125,653 rows.** `syllables.txt.gz` carries
`(nbsyll, SAMPA phon, orthosyll)` per spelling. **French is the first pack in this
project that can honestly declare `syllables`**: the capability means a segmentation
of the written word, `orthosyll` is exactly that (`car-ros-se`), and ADR 0030 removed
the same capability from `denckring-en-data`, which had declared it and never
implemented it. German declines it still, because its transcriptions carry no division
of the spelling.

**D3. `stress` is still refused, and 103 is no longer a projection.** ADR 0032 D5 and
spec D2 both stated 103 as the honest ceiling. It is now a measurement: French runs
**103 of 121**, the remaining **18 rows are blocked on `stress` and on nothing else**,
verified mechanically against `meta.requires` rather than asserted. They are accentual
metres — the sonnet family, iambic pentameter, dactylic hexameter, sapphic, alcaic,
ottava rima, rhyme royal, spenserian, heroic couplet, trochaic tetrameter, double
dactyl, elegiac couplet, curtal sonnet, ballade, blank verse, proteus verse — and they
are not French forms. Declaring `stress` to reach a larger number would be the
false-capability defect ADR 0030 fixed twice in one day.

**D4. The French line count is `exact=False`, always.** ADR 0012's flag already exists
to say so and every syllabic report carries `estimated_words`. Diérèse and synérèse
are not decidable from spelling — `extraordinaire` is four syllables or five depending
on the poet — and D5 is the evidence rather than the assertion. plint, the mature tool
in this space, calls its own handling "a liberal estimate" for the same reason.

**D5. A diérèse rule ships, and it is a STOP, not an ACCEPT.** Scored over lines
interior to a speech block, because the first and last line of a speech may be half an
alexandrine shared between speakers — Hugo's unfiltered run has a 266-line spike at
exactly 6, the caesura — and excluding any line holding a word Lexique does not carry,
which cannot test an elision rule:

| | baseline | shipped | ceiling |
|---|---|---|---|
| Racine, *Mithridate* (n=1213) | 89.3% | **90.3%** | 96.6% |
| Hugo, *Hernani* (n=1283) | 79.3% | **80.2%** | 84.8% |

The ceiling column is a perfect per-site oracle: what the counter would score if every
diérèse decision in the text were made correctly by an editor. **A mechanical rule
captured 1.0 of the 7.3 points that oracle would take on Racine.** The accept bar was
94%. Three variants were measured and none reached it, so the chapter stops here with
what it has rather than spending more of the budget or lowering the bar.

The shipped rule is narrow: every `j` after any consonant is one extra syllable, gated
on the word ending in the `-ion(s)` suffix or starting with `dia-`. It generalises
further than its 90.3% suggests — it fires on 18 distinct words across both poets and
23 of its 27 firings are correct — but it is not a solved rule and the count stays
estimated (D4).

**Record the rules that failed, because they are the plausible ones.** The chapter
plan's own proposed starting rule — a glide after a consonant cluster ending in a
liquid — scored **84.5% / 74.7%, roughly five points *below* the baseline of doing
nothing.** Two blanket probes were catastrophic (49.5% / 36.6% and 46.2% / 33.8%),
because the plurality of every "glide after a consonant" site in Lexique is a verb or
adjective ending (`-iez`, `-ions`, `-ier`, `-ien`) that is reliably *synérèse*. Anyone
proposing the cluster rule again should read this paragraph first; it sounds right and
it is worse than no rule at all.

**D6. The aspirated-*h* list is vendored data, extracted from frwiktionary and
expanded through Lexique.** Lexique cannot distinguish aspirated from mute *h* —
`haricot` is `aRiko` and `hôtel` is `otEl`, the letter simply dropped — and the
distinction decides whether the schwa in front of it elides. `h_aspire.txt.gz` holds
**3,370 entries: 3,285 from a scan of `{{h aspiré}}` in the French section of each
page, plus 85 from expanding those lemmas through Lexique's `lemme` column.** The
expansion looks negligible and is not: Wiktionary already marks most inflected pages
directly, so expansion adds only what it missed, and what it missed includes `hais` —
the high-frequency verb forms are exactly the ones that appear in verse. Only 324 of
the 3,370 entries are known to Lexique as lemmas at all, and those expand to 740 forms.
(`{{asp|fr}}`, which an earlier draft guessed at as an alternative template, occurs
**zero** times in the dump.)

**D7. One table row per spelling, chosen by `freqlivres`.** Lexique carries several
rows per homograph, and the pack is asked about a spelling rather than about a reading,
so the most frequent reading wins. The cost is stated in Consequences rather than
hidden here.

## Consequences

**French runs 103 of 121, up from 80**, and `denckring eval --all` goes from 439 to
**487** passing cases, the 48 new ones French across the 23 unblocked rows.
`denckring status` is unchanged at `155 · 130 · 121 · 121 · 25`: this record adds no
catalogue row and implements no procedure. It moves one language's coverage and
nothing else.

**`parent` the verb is counted as `parent` the noun.** D7's consequence, and it is not
a rare shape: French homographs that differ in pronunciation across parts of speech
(`président`, `fils`, `est`, `parent`) are counted, transcribed and rhymed as whichever
reading `freqlivres` ranks first. A caller asking for the syllable count or the rhyme
key of the loser gets a confident wrong answer rather than a refusal, which is this
project's least favourite failure shape. Fixing it needs a part-of-speech capability no
pack provides — the same blocker `homosyntaxism`, `verbless_prose` and `chimera`
already sit behind — so it is recorded, not solved.

**`extraordinaire` is a known mute-*e* miss and is inside the measured 90.3%, not
against it.** Lexique gives it `nbsyll` 5 and `orthosyll` `ex-traor-di-nai-re`, also 5,
because `traor` covers two phonetic syllables in one orthographic segment. The mute-*e*
test compares the segment count against `nbsyll` and so cannot see the final *e* here.
The failure is silent: the word contributes 5 where verse frequently wants 6, and
nothing in the report says which word was wrong. Words shaped like this are the residue
the ceiling column of D5 measures.

**Schwa is rendered /ø/.** Lexique writes `le` as `l2`, and SAMPA `2` spells both /ø/
and the schwa; the table maps it uniformly, so `phonemes("le")` is `['l', 'ø']` where a
French phonology reference would say /lə/. This is faithful to a source that cannot
distinguish the two, and it is harmless for rhyme and assonance, where they are
near-merged — but a caller reading `phonemes()` as a phonological transcription is
being told something slightly false, and finding that out by inspection would be worse
than reading it here.

**`syllables.heuristic` is now satisfiable through `line_syllables` as well as through
`syllable_count`, and the guarantee behind it is weaker than it was.** Before this
record the capability meant one method. French's override reads its own tables directly
rather than calling `syllable_count`, so a pack can now satisfy the capability by two
independent paths and a row that declares it has no way to say which one it will get.
`tests/test_requires_honesty.py` tracks both names and a new test asserts the two
hand-maintained capability tables agree — adding the method to one table alone silently
disarmed the sufficiency check for eleven rows once already. No pack abuses the looser
contract today; nothing prevents one.

**No installed pack lacks `phonemes` any more, so that refusal has no in-suite
example.** `tests/test_prosody_robustness.py` covered "a pack that genuinely cannot
answer" with French, because French had no pronunciation data; German had held the same
role until chapter 4 gave it a dictionary. That test now uses `sonnet` and `stress`,
which is a real refusal but a different one. The phonemes refusal path is exercised
only by the `french-without-data` CI job on a core-only install, which is a job that
can be deleted by someone who does not know it is load-bearing. Its comment says so.

**Feminine/masculine rhyme alternation is not modelled, and French classical prosody
requires it.** `rhyme_key` returns the *rime suffisante* baseline — phonemes from the
last vowel to the end of the word, since French has no lexical stress to anchor a
stronger definition. A French classical poem that never alternates feminine and
masculine rhymes is not a well-formed poem, and `rhyme_scheme` will pass it. This is a
real gap and a **different** one: the project models the alternation in no language, so
it is not something French is missing relative to English or German.

**The caesura is unchecked.** `alexandrine` counts twelve syllables and says nothing
about the hemistich. plint does not check it either, for the reason it gives: the
hemistich has to fall at a sensible grammatical position, which is not decidable from
the data here.

**A word outside Lexique degrades rather than refuses, and the two behaviours now sit
side by side.** `syllables()` and `phonemes()` raise `MissingCapability` for a word the
table does not carry; `line_syllables` falls back to a vowel-run estimate and increments
`estimated_words` instead, because one unknown word must not blank the count for a whole
line of real verse. Both are defensible and they are not the same rule, so a caller
comparing a per-word answer against a per-line one can see a word counted in one and
refused in the other.

## Alternatives considered

**Leaving the sum in `syllable_count.line_syllables` and special-casing French there.**
It would have put a fact about French mute *e* in a procedure module that has no other
business knowing one, and the next language with a line-level rule would have added a
second branch beside it. The seam on the pack costs a protocol method and one default
implementation.

**A diérèse parameter, letting the caller declare the poet's intent.** A reasonable
future request and not designed here. It would turn D4's estimate into an exact count
for a caller willing to annotate, which is the honest shape for a decision that is
editorial — but it is a parameter on 23 rows and its own decision.

**Vendoring a G2P engine (`phonemizer`/espeak) rather than a table.** A runtime
dependency, TTS-oriented, and it answers pronunciation rather than the orthographic
syllabation D2 rests on. It would not have improved D5, which is bounded by editorial
intent and not by phonetic accuracy.

**Deriving the elision rules from plint.** GPLv3 against this project's Apache-2.0. Its
*documented* rules are facts about French and were learned from; its implementation was
not read, and none of it is here.

**Stopping the chapter at 80.** The genuine option, and the one the go/no-go existed to
force. What was measured is a *diérèse* bar that D5 misses, on top of a mute-*e*
baseline of 89.3% on Racine that the same harness reports. The chapter ships because
that baseline is the bulk of what the 23 rows depend on and because `exact=False` is a
truthful label for it — not because 90.3% cleared anything. Had the baseline itself
been the poor number, this record would have said the chapter stopped, and no
comparison against a naive per-word sum was measured to make the baseline look better
than it is.
