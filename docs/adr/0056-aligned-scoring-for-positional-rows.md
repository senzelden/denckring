# 56. Aligned scoring for positional rows

## Context

ADR 0005 made `score` continuous so that a retry loop can tell a near miss from a text
that missed everything. Eight rows check a text against a sequence their rule computes
from a source: `column_reading`, `haikuization` and `every_nth_word` against words,
`slenderizing`, `homoconsonantism` and `homovocalism` against letters, and `n_plus_7`
and `s_plus_7` against the source's words, displaced. Each of them compared the text
with that sequence index by index. One dropped unit early in the text shifted every
later unit by one, so a text that was right but for one missing word scored as if it
had nothing right after it. N+7 was harsher still: any word-count mismatch scored the
whole text 0/1 as `wrong_word_count`, so one dropped article cost every correct
displacement in the text.

denckring-bench found the cost (audit A6). Its spec calls score@1 "reported but harsh",
because the score these rows reported said where the text first slipped, not how much
of it was wrong. A continuous score that collapses at the first slip is not the signal
ADR 0005 asked for.

## Decision

**The positional rows score over an alignment** (ruling R-U8a). One shared helper,
`source_compare.align`, aligns the expected units with the text's units using
`difflib.SequenceMatcher(None, expected, produced, autojunk=False)`. It works over the
units each row already compared: casefolded words, or letters as the row folds them.
With no junk function and no autojunk heuristic, the same pair always aligns the same
way. `source_compare.aligned_report` scores the alignment, and `positional_report`,
`letter_class_report`, `slenderizing` and `every_nth_word` call it.

**`good` is the matched count, and the denominator is the alignment's length**:
matches, substitutions, insertions and deletions. A `replace` of unequal spans counts
its longer side. It pairs units in order as substitutions and leaves the rest as
insertions or deletions. Only identical sequences align with nothing but matches, so
1.0 still means an exact match and nothing else. No verdict moves. A text with one
dropped unit now scores (n − 1)/n, where it used to score its matched prefix over n.

**A substitution keeps the row's rule** (`wrong_word`, `wrong_letter`,
`wrong_column_word`, `wrong_line_end`, `wrong_consonant`, `wrong_vowel`). Insertions
and deletions reuse the shared vocabulary's existing names. An insertion is
`extra_words` or `extra_letters`, which every one of these rows already emitted for a
surplus tail. A deletion is `missing_word` or `missing_letter`, the names
`homosyntaxism`, `transposal`, `anagram` and the pangram rows already use. An inserted
run is one violation at its first unit, with its units joined in `found`, which is the
shape the `extra_*` tail always had. A deleted unit is one violation each, placed where
it would go: at the next unit of the text, or at the text's end when none follows. This
follows `homosyntaxism`, which reports each missing position the writer still owes.

**N+7's word-count mismatch is aligned against the correct N+7**, meaning each listed
word displaced and every other word as it stands. The pairs are then judged exactly as
the equal-count path judges them, under the same `ambiguous_nouns` reading. Each
inserted or missing word is one more unit, as `extra_words` or `missing_word`.
`wrong_word_count` is no longer emitted by these two rows. The equal-count path keeps
its word-for-word pairing, because an alignment there could pair a word with a later
word of the same spelling, and only a dropped or added word is what A6 is about.

`missing_letter` is an `inventory` failure on the rows that count a text's letters, and
a `transcription` failure on `slenderizing`, `homoconsonantism` and `homovocalism`. It
joins `wrong_letter` in `rules.ROW_CATEGORIES`.

## Consequences

This is a breaking change to scores and to violation lists, and the score change is
its purpose. Any score these eight rows produced before may change. A caller who stored
scores from 0.3.x cannot compare them with 0.4.0's on these rows. A caller who read the
violation list now sees insertions and deletions named where it used to see a run of
substitutions, and sees `extra_*` mid-text, not only as a tail. `wrong_letter` on
`slenderizing` and the other substitution rules fire far less often, because most of
what they reported was the cascade. `n_plus_7` and `s_plus_7` add `extra_words` and
`missing_word` to their declared rules and drop `wrong_word_count`. A consumer that
maps rules, such as denckring-bench's failure classes, has to re-map those rows.

`SequenceMatcher` keeps the longest matching block first. It does not minimise edits.
When a substituted unit sits next to a twin, it can come out as an insertion and a
deletion. `homovocalism`'s `the cot sat` against `the cat sat` aligns e-o-a with e-a-a
as keep `e`, insert `o`, keep `a`, delete `a`. That is two units, so the text scores
0.5, where index by index it scored 0.667 with one `wrong_vowel`. The ruling chose
determinism and the standard library over an optimal edit alignment. A text can
therefore score lower than it did before, and its violations can describe a
substitution as a gap pair. `tests/test_letter_class.py` pins the case so that the cost
stays visible.

The alignment is quadratic in the worst case, where index-by-index comparison was
linear. A long letter row (`slenderizing` on a page of prose) pays for that, though
`SequenceMatcher` stays fast on texts that mostly match, which is the case these rows
are written for.

Two other rows compare a sequence index by index and are not changed here. The
relation rows (`synonymic_substitution`, `antonymic_substitution`,
`antonymic_translation`) still score a word-count mismatch 0/1 as `wrong_word_count`,
and `homosyntaxism` still matches part-of-speech tags position by position. Neither was
in A6. Both could move to `align` under the same reasoning.

**Golden corpus, re-measured over all 687 cases: no verdict moves, and four scores do.**

| case | before | after | violations now |
|---|---|---|---|
| `slenderizing` en `r-kept` | 0.250 | 0.750 | one `extra_letters` (`r`) |
| `slenderizing` de `eszett-kept-while-deleting-s` | 0.412 | 0.765 | two `extra_letters` (each `ß`'s `ss`) |
| `slenderizing` fr `oe-ligature-dropped-whole-while-deleting-e` | 0.167 | 0.833 | two `missing_letter` (each `œ`'s `o`) |
| `homovocalism` en `a-changed-vowel` | 0.667 | 0.500 | `extra_letters` and `missing_letter` (the cost above) |

The three `slenderizing` moves are the cascade this ADR removes: each text was one
letter (or one ligature's letters) off, and the old report named every letter after
the first slip as wrong. No golden case on `column_reading`, `haikuization`,
`every_nth_word`, `homoconsonantism`, `n_plus_7` or `s_plus_7` has a dropped or
inserted unit, so none of their scores moves. `tests/test_aligned_scoring.py` drops
one unit early on each of the eight rows and requires it to cost exactly one unit. It
fails against the index-by-index code on every row.
