# 37. The calculator word, and what a seven-segment display can actually write

## Context

`calculator_word` is the first catalogued row whose constraint is a property of a
*machine* rather than of an orthography or a lexicon. A word qualifies if a
seven-segment display can write it: enter the digits, turn the calculator over, read
what it shows. `7353` is `ESEL`.

That framing makes three questions decidable which would otherwise be matters of
taste, and each has a folk answer that is wrong.

The circulating table is usually given as ten digits, `0 1 2 3 4 5 6 7 8 9` mapping
to `O I Z E h S g L B G`, under the name *beghilos*. But rotating a seven-segment
glyph by 180 degrees swaps the segments a↔d, b↔e and c↔f and fixes g, and under that
transform the digits do not behave as the folk table says.

The second question is diacritics. Every other row in this catalogue folds them by
default, and this row's whole subject is what a machine can render.

The third is that the rotation is not injective.

## Decision

### D2. `2` maps to nothing, and the table is fixed

| digit | segments | rotated | reads as |
|---|---|---|---|
| 0 | a b c d e f | a b c d e f | O |
| 1 | b c | e f | I |
| 2 | a b d e g | a b d e g | **itself — no letter** |
| 3 | a b c d g | a d e f g | E |
| 4 | b c f g | c e f g | H |
| 5 | a c d f g | a c d f g | S |
| 6 | a c d e f g | a b c d f g | G |
| 7 | a b c | d e f | L |
| 8 | all | all | B |
| 9 | a b c d f g | a c d e f g | G |

`2` is rotationally symmetric. `2 → Z` is a pun on the *printed* digit, not a property
of the display, and `2 → R` is weaker still — a mapping in which one digit yields two
different letters is not a function, and `7222` would have four readings. Both are
refused, and there is no parameter to reinstate them: a parameter would let the row
publish a geometry it does not have.

### D3. `fold_diacritics` defaults to `false`, inverting the project default

The display is the artefact. A calculator cannot write `Geheiß` — it writes `GEHEISS`
— and it cannot write `blessé`. Under folding both are accepted as calculator words,
which is false about the machine.

### D4. G has two digit spellings; `check` accepts both, `apply` emits `6`

`6` and `9` are each other's rotation mirror and both land on G, and the display has
no case. `IGEL` is `7361` and `7391` alike. The generator emits `6`, because the
practice's own name — *beghilos* — encodes g from 6.

## Consequences

**D2 forgoes roughly half the reachable corpus in every language.** Measured
2026-09-04 against the installed packs, and pinned by `tests/test_calculator_corpus.py`
so the figure cannot drift into prose:

| table | en | de | fr |
|---|---|---|---|
| this one | 304 | 216 | 207 |
| with `2 → Z` and `2 → R` | 643 | 652 | 631 |

The corpus more than doubles on the least defensible entry in the folk table. That is
the cost, and it is paid to keep the row's claim about the machine true. Anyone who
wants the wider set should reopen this decision rather than add a parameter.

**D3 costs de 242 → 216 and fr 356 → 207**, and leaves one row in 156 whose fold
default reads backwards to anyone scanning the catalogue. The parameter remains, so
the lenient "displayable up to accents" reading stays reachable; only the default
states which reading the row means. English is unaffected — it has no accented words
inside the alphabet at all.

**D4 means `apply` is not the inverse of `check`** for any word containing G, which is
108 of 304 English calculator words, 100 of 216 German and 58 of 207 French — about a
third of every corpus. The attested `ILLEGIBLE` is the sharpest case and is a golden
fixture from both sides: the form in circulation is `378193771` and this generator
emits `378163771`. A reader who assumes one canonical spelling will read the other as
a bug. `tests/test_round_trip.py` is unaffected, since it asserts that a generator's
output satisfies its own checker, not that the digits round-trip byte for byte.

**The table is a module constant, not a pack capability.** `prisoners_constraint`
reads its forbidden set from `pack.letter_shapes` because ascenders and descenders
genuinely differ by orthography; seven-segment geometry does not. The cost is that a
reader who has internalised `prisoners_constraint` will expect the pack to own this
and has to be told otherwise, which the row's `notes` does.

**`apply_requires` names `lexicon.nouns`, not `lexicon.graded_words`.** At the time
this was written German declared no graded words — SCOWL ships in
`denckring-en-data` alone (ADR 0028) — so a row demanding them could not generate in
the language of this row's own example, and would have emitted exactly the misleading
`missing_capability` remedy fixed the same day. The generator therefore floors on the
noun list, the capability every pack meets, and uses graded words only to rank where a
pack declares them.

*Amended 2026-09-04, later the same day.* ADR 0038 gave German `lexicon.graded_words`
from the Leipzig Corpora Collection, so the reason above no longer holds. **The
decision does.** `apply_requires` should name what a row genuinely needs rather than
the best thing currently available, and `lexicon.nouns` remains the floor every pack
meets; a row that demanded graded words would refuse on a core-only install for no
gain. Left standing with its original reasoning intact rather than rewritten, because
a decision that survives the collapse of its own premise is worth being able to see.

**The row is a `verfahren`, not the first `instrument`.** The calculator is tempting
as one — its address space is genuine, radix 10, one digit per position — but ADR 0033
D5 refuses a provenance meaning "contemporary, with no source", and a 1970s consumer
device is exactly that. The catalogue still holds 0 instruments.

**Provenance is what was verified and nothing more.** `attribution: reference`, citing
Quinion (2009) and the 1970s dating. A *Word Ways* article, "The Word Calculator",
exists in Butler University's archive and returned HTTP 403; it is not cited. An
unverified citation is worth less than nothing here, which is the same rule that leaves
the Leibniz *De arte combinatoria* headings out of `palindrome` and `anagram`.

**An empty text was vacuously satisfied in the first implementation**, and the fix is
worth recording because the shape recurs. `wrong_word_count` and `wrong_digits` are
faults of the whole entry rather than of one word, and marking them by flagging every
word marks nothing when there are no words — so an empty text scored 1.0 while
carrying two violations. `_report` enforces `satisfied == (score == 1.0)`, so that was
a satisfied report with complaints attached: the one shape the helper exists to rule
out. A whole-text fault is now tracked as its own flag rather than by marking units.
The general lesson is `_report`'s own: a procedure whose verdict is not a ratio of
units must not express it as one.
