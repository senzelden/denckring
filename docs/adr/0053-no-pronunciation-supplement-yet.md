# 53. No vendored pronunciation supplement for band 10, yet

## Context

The audit (D4) found twelve band-10 graded words that CMUdict lacks, and proposed a
small vendored supplement to close the gap. Measured on this branch, after A4's
inflection fallback and ADR 0051's exclusions:

- Six of the twelve are out of the everyday view as no everyday words: `cs`, `cums`,
  `hes`, `leaved`, `numbest`, `payed`.
- `chars` resolves through its stem, `char`.
- Five remain: `deeming`, `inclining`, `inputted`, `inputting`, `sophisticating`.
  The spelling heuristic already counts each one's syllables correctly (2, 3, 3,
  3, 5), so their syllable counts are right and only marked as estimates. What they
  lack is stress and a rhyme key.

## Decision

No supplement ships in 0.3.2, for two reasons.

**No licensed source holds these words.** The proposal was a vendored supplement,
and there is nothing to vendor: CMUdict is the English pronouncing dictionary this
project uses, and it omits them. Wiktionary has some of them under CC BY-SA, which
ADR 0013 would quarantine in a new distribution for five words. Writing the
transcriptions by hand would be data with no source behind it, which this project's
data packages have never shipped.

**Any supplement moves verdicts.** `known_words()` is the union of the nouns and
CMUdict's headwords (ADR 0015), so a pronunciation added for `inputted` makes it a
word for `is_word`, `semordnilap` and `charade`. Its syllable count would turn from
estimated to exact, and `estimated_words` would change in reports. Rhyme rows would
decide pairs they now report as `rhyme_undecidable`. 0.3.2 moves no verdict beyond
the bug fixes its changelog names, and a supplement is not a bug fix.

## Consequences

- The five words keep heuristic syllable counts that are right, and no stress or
  rhyme. A row reading them reports what it could not decide rather than guessing.
- The better route is a rule rather than a list: the inflection fallback A4 began
  (`awakes` from `awake`) extended to `-ing` with a dropped `e` (`inclining`) and a
  doubled consonant (`inputting`), deriving pronunciations from CMUdict's own
  entries. That is a reading change, and belongs in 0.4.0 with a re-measured golden
  corpus.
