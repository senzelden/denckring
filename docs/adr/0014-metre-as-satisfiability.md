# 14. Metre is a satisfiability question, not a comparison

## Context

CMUdict records lexical stress, not metrical stress. On "Shall I compare thee to a
summer's day" it marks *to* and *shall* as stressed, because those are the citation
forms. A checker comparing dictionary stress against an iambic pattern would reject
Shakespeare's most famous line.

The fact that resolves it: polysyllabic words have fixed internal stress — *compare*
is 01 wherever it appears — while monosyllables take whatever stress the line gives
them.

## Decision

A line scans when *some* assignment fits: polysyllabic patterns are fixed,
monosyllables are free, secondary stress is free, and every pronunciation CMUdict
lists is tried. Because free syllables are independent, this is a linear scan per
pronunciation combination rather than a search over stress.

Pronunciation variants matter and are searched. Shakespeare needs the three-syllable
*tem-per-ate*, which CMUdict lists second because the compressed modern form comes
first.

## Consequences

Metre is checked **exactly** rather than approximately — no tolerance parameter, no
apology. What is checked is strict stress, and that is a narrower claim than it may
appear: real English verse routinely uses substitutions, and this checker accepts none
of them. Sonnet 18's second line fails, correctly, because *temperate* ends on an
unstressed syllable where strict iambic pentameter wants a stress.

The catalogue definitions say so. A future `substitutions` parameter could admit the
inverted first foot and the weak ending, but encoding all of scansion's licences is a
research problem, and claiming to have done it would be the overclaiming this project
has avoided throughout.

Two further limits worth stating: CMUdict is modern, so *temperate* no longer rhymes
with *date* as it did for Shakespeare; and archaic contractions such as *o'er* are
absent entirely, where the checker raises rather than guessing.
