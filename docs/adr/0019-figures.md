# 19. A figure is an alphabet read at several levels

## Context

Llull's ternary Ars letters nine principles B to K, skipping J. The same letter names a
dignity, a relation, a question, a subject, a virtue or a vice, depending on which table
it is read against — and that multiple assignment *is* the device, not a convenience of
notation. Turning three concentric wheels produces chambers of letters; what a chamber
says depends on the level.

The existing `Device` does not fit. Its slots are different sets and a reading is a
product across them. A figure draws every position from one alphabet, and a chamber is a
combination rather than a product.

## Decision

`Figure` sits beside `Device`: an alphabet, a set of levels mapping each letter to a
name, and `chambers(arity)` giving the combinations. `llull_figure` accepts a chamber
written either as letters or spelled out at any level, and if no level is named it asks
whether *some* level reads — the satisfiability question this package keeps arriving at.

Kircher's *Ars Magna Sciendi* becomes a preset rather than an implementation, because it
is the same mechanism with a different stock.

## Consequences

Counts are computed, never quoted: 84 ternary chambers and 36 pairs for Figura A fall
out of nine letters, and the number of entries in the printed tabula stays unchecked
until someone reads a facsimile. That follows the rule the expansion research set —
recomputing beats citing, in a field where the headline numbers are often wrong.

Matching spelled-out principles needed the Denckring's segmentation rather than a word
split, because some names are several words long: the ninth question is *Quomodo et cum
quo*, and splitting on whitespace would never find it.

Two things stay in `notes` rather than being smoothed away. The wheels do not freely
generate new truths — the stock is fixed and heterodox combinations are excluded
elsewhere in the Ars, which is Eco's point and cuts against how the device is usually
described. And the reading of the figure as a first computer is reception, not a finding
about the object.

`ars_combinatoria` moved to `checkability: none`. It names a tradition, not a procedure:
what counts as a valid combination is whatever the particular device specifies, and its
instances — this figure, the Denckring, Queneau's sonnets, Kuhlmann's Wechselsatz — are
catalogued and checkable separately.
